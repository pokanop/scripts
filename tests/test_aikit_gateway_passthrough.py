"""Unit tests for aikit gateway passthrough-endpoint discovery + native-protocol tool
linking (POK-68).

Routability through a native passthrough route (claude → /anthropic) is a RUNTIME,
gateway-dependent property, not a static table. These tests pin: composite discovery
(built-in route table ∩ (provider-tag inference ∪ probe), plus user-declared custom
routes); a mounted-but-401 route is reported unusable; the vendor-locked tools are
reclassified from a flat "unsupported" to route-aware verdicts and flip to `passthrough`
via a declared custom mapping; env wiring points each tool's base-URL var at the route;
and the credential modes (virtual-key vs forwarded-token). All mocked — no network.
"""

from __future__ import annotations

import types

import pytest

BASE = "https://gw.example.com"
SECRET = "sk-secret-key-1234567890"
# Models chosen so provider-tag inference marks anthropic + openai + cohere in-use.
MODELS = ["anthropic/claude-3-5", "openai/gpt-4o", "cohere/command-r"]
DETAIL = {"openai/gpt-4o": {"provider": "openai", "max_tokens": 128000}}


@pytest.fixture
def aikit(tool_loader):
    m = tool_loader("aikit")
    m._reset_passthrough_cache()
    return m


@pytest.fixture
def gw(aikit, tmp_path, monkeypatch):
    """Isolated gateway: temp HOME + gateway dir, mocked model discovery, controllable
    tool detection (via the returned ``detected`` set) and passthrough probing (via the
    returned ``probe`` dict: full-url → HTTP status)."""
    home = tmp_path
    rc = home / ".zshrc"
    rc.write_text("# rc\n")
    detected: set = set()
    probe: dict = {}
    gwdir = home / ".aikit" / "gateway"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(aikit, "GATEWAY_DIR", gwdir)
    monkeypatch.setattr(aikit, "GATEWAY_CONFIG_FILE", gwdir / "config.json")
    monkeypatch.setattr(aikit, "GATEWAY_STATE_FILE", gwdir / "state.json")
    monkeypatch.setattr(aikit, "detect_shell", lambda explicit=None: ("zsh", rc))
    monkeypatch.setattr(aikit, "discover_models", lambda u, k, **kw: (MODELS, DETAIL))
    monkeypatch.setattr(aikit, "detect_gateway_tool", lambda key: key in detected)
    # Default prober: 200 unless the test set a specific status for that URL.
    monkeypatch.setattr(aikit, "_probe_status",
                        lambda url, key, **kw: probe.get(url, 200))
    return types.SimpleNamespace(aikit=aikit, home=home, rc=rc, gwdir=gwdir,
                                 detected=detected, probe=probe)


def _write_gateway_config(gw, **extra):
    """Seed config.json with credentials + any passthroughs/credential_mode."""
    gw.gwdir.mkdir(parents=True, exist_ok=True)
    data = {"base_url": BASE, "key": SECRET}
    data.update(extra)
    (gw.gwdir / "config.json").write_text(__import__("json").dumps(data))


# --- built-in route table ---------------------------------------------------
def test_builtin_routes_are_verified_litellm_set(aikit):
    routes = aikit.GATEWAY_PASSTHROUGH_ROUTES
    # The native routes LiteLLM mounts in code (verified against source).
    for r in ("/anthropic", "/gemini", "/vertex_ai", "/bedrock", "/cohere",
              "/mistral", "/openai", "/vllm", "/azure", "/cursor"):
        assert r in routes, f"{r} missing from the built-in route table"
    # Each route names a provider; probeable ones carry a safe models-list GET.
    assert routes["/anthropic"]["provider"] == "anthropic"
    assert routes["/anthropic"]["probe"] == "/v1/models"
    assert routes["/cursor"]["provider"] == "cursor"        # Cursor Cloud Agents
    assert routes["/bedrock"]["probe"] is None              # no safe cheap GET


# --- composite discovery ----------------------------------------------------
def test_discover_inference_only_marks_in_use_providers(aikit):
    # No probing: a provider serving models makes its native route usable.
    disc = aikit.discover_passthrough_routes(BASE, SECRET, MODELS, DETAIL)
    usable = aikit.usable_passthrough_routes(disc)
    assert "/anthropic" in usable          # anthropic/claude-3-5 in use
    assert "/openai" in usable             # openai/gpt-4o in use
    assert "/cohere" in usable             # cohere/command-r in use
    assert "/mistral" not in usable        # no mistral model → not inferred
    assert disc["/anthropic"]["via"] == "inference"


def test_probe_401_route_is_unusable_even_if_mounted(aikit):
    # POK-62: /anthropic 401'd while /v1 served the same model. A mounted-but-401 route
    # must be reported UNUSABLE — presence ≠ works.
    def prober(url, key, **kw):
        return 401 if "/anthropic/" in url else 200
    disc = aikit.discover_passthrough_routes(
        BASE, SECRET, MODELS, DETAIL, probe=True, prober=prober)
    assert disc["/anthropic"]["usable"] is False
    assert disc["/anthropic"]["status"] == "unauthorized"
    assert "/anthropic" not in aikit.usable_passthrough_routes(disc)


def test_probe_ok_route_is_usable(aikit):
    disc = aikit.discover_passthrough_routes(
        BASE, SECRET, [], {}, probe=True, prober=lambda u, k, **kw: 200)
    # /mistral isn't inferred (no model), but a 200 probe proves it usable.
    assert disc["/mistral"]["usable"] is True
    assert disc["/mistral"]["via"] == "probe"


def test_probe_unknown_falls_back_to_inference(aikit):
    # A network error (status 0) is inconclusive → fall back to provider-tag inference.
    disc = aikit.discover_passthrough_routes(
        BASE, SECRET, MODELS, DETAIL, probe=True, prober=lambda u, k, **kw: 0)
    assert disc["/anthropic"]["usable"] is True       # inferred (model in use)
    assert disc["/anthropic"]["via"] == "inference"
    assert disc["/mistral"]["usable"] is False        # neither inferred nor probed-ok


def test_custom_declared_route_is_honored(aikit):
    custom = {"amp": {"route": "/sourcegraph", "auth_var": "AMP_API_KEY"}}
    disc = aikit.discover_passthrough_routes(BASE, SECRET, [], {}, custom=custom)
    assert disc["/sourcegraph"]["usable"] is True
    assert disc["/sourcegraph"]["source"] == "custom"
    assert "/sourcegraph" in aikit.usable_passthrough_routes(disc)


def test_probe_status_swallows_network_errors(aikit, monkeypatch):
    # The real prober must never raise — a dead host is 'unknown' (0), not a crash, so
    # discovery degrades gracefully and can't take down `on`.
    import requests

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("host down")
    monkeypatch.setattr(requests, "get", boom)
    assert aikit._probe_status(f"{BASE}/anthropic/v1/models", SECRET) == 0


def test_discovery_caches_live_probes(aikit, gw):
    calls = {"n": 0}

    def counting(url, key, **kw):
        calls["n"] += 1
        return 200
    gw.aikit._probe_status = counting  # module-level default prober (prober=None → live)
    aikit._reset_passthrough_cache()
    aikit.discover_passthrough_routes(BASE, SECRET, MODELS, DETAIL, probe=True)
    first = calls["n"]
    assert first > 0
    aikit.discover_passthrough_routes(BASE, SECRET, MODELS, DETAIL, probe=True)
    assert calls["n"] == first                              # served from cache
    aikit._reset_passthrough_cache()
    aikit.discover_passthrough_routes(BASE, SECRET, MODELS, DETAIL, probe=True)
    assert calls["n"] > first                               # recomputed after reset


# --- reclassification / resolution ------------------------------------------
def test_passthrough_state_is_registered_and_routed(aikit):
    assert aikit.COVERAGE_PASSTHROUGH == "passthrough"
    assert aikit.COVERAGE_PASSTHROUGH in aikit.COVERAGE_STATE_ORDER
    assert aikit.COVERAGE_PASSTHROUGH in aikit.COVERAGE_ROUTED_STATES


def test_static_coverage_is_the_declared_baseline(aikit):
    # With no discovery + no custom maps, the model is the static declared view (POK-67
    # baseline: renderers cover kilo/cline/qwen, openhands is env). The 5 vendor tools are
    # still unsupported — routability is a runtime property, unchanged without discovery.
    cov = aikit.gateway_coverage()
    counts: dict = {}
    for c in cov.values():
        counts[c["state"]] = counts.get(c["state"], 0) + 1
    assert counts == {"renderer": 12, "env": 5, "pending": 3, "unsupported": 6}
    assert cov["cursor"]["state"] == "unsupported"


def test_vendor_entries_carry_route_aware_candidacy(aikit):
    # The reclassification: each vendor tool declares its native protocol + route (or
    # None) + auth var, and the reason is now route-aware, not a flat "first-party".
    pt = {k: v.get("passthrough") for k, v in aikit.GATEWAY_COVERAGE.items()}
    assert pt["cursor"]["route"] == "/cursor"               # Cursor Cloud Agents exists
    assert pt["antigravity"]["route"] == "/gemini"          # Google AI Studio exists
    assert pt["copilot"]["route"] is None                   # no LiteLLM github route
    assert pt["kiro"]["route"] is None and pt["amp"]["route"] is None
    assert "/cursor" in aikit.GATEWAY_COVERAGE["cursor"]["reason"]


def test_usable_route_without_override_stays_unsupported_with_upgraded_reason(aikit):
    # /cursor is usable, but cursor-agent has no base-URL override → the BLOCKER is now
    # the tool side, not the gateway. State stays unsupported; the reason says so.
    cov = aikit.gateway_coverage(passthrough={"/cursor"})
    assert cov["cursor"]["state"] == "unsupported"
    assert "no base-URL override" in cov["cursor"]["reason"]
    assert cov["cursor"]["route"] == "/cursor"


def test_custom_mapping_flips_vendor_tool_to_passthrough(aikit):
    custom = {"amp": {"route": "/sourcegraph", "auth_var": "AMP_API_KEY",
                      "base_url_var": "AMP_URL"}}
    cov = aikit.gateway_coverage(custom=custom)
    assert cov["amp"]["state"] == "passthrough"
    assert cov["amp"]["route"] == "/sourcegraph"
    assert cov["amp"]["auth_mode"] == "virtual_key"
    assert "custom" in cov["amp"]["via"]


def test_custom_mapping_per_route_forwarded_token_mode(aikit):
    # A per-passthrough credential_mode overrides the global default for that tool.
    custom = {"amp": {"route": "/anthropic", "auth_var": "ANTHROPIC_AUTH_TOKEN",
                      "base_url_var": "ANTHROPIC_BASE_URL",
                      "credential_mode": "forwarded_token"}}
    cov = aikit.gateway_coverage(custom=custom)          # global default = virtual_key
    assert cov["amp"]["state"] == "passthrough"
    assert cov["amp"]["auth_mode"] == "forwarded_token"  # per-route override wins


def test_global_credential_mode_propagates_to_resolved_specs(aikit):
    custom = {"amp": {"route": "/sourcegraph", "auth_var": "AMP_API_KEY",
                      "base_url_var": "AMP_URL"}}
    cov = aikit.gateway_coverage(custom=custom, credential_mode="forwarded_token")
    assert cov["amp"]["auth_mode"] == "forwarded_token"


# --- env-layer wiring -------------------------------------------------------
def test_build_env_pairs_default_is_unchanged(aikit):
    # No passthroughs, no forwarded prefixes → identical to the pre-POK-68 behaviour.
    a = dict(aikit.build_env_pairs(BASE, SECRET))
    assert a["ANTHROPIC_AUTH_TOKEN"] == SECRET
    assert a["ANTHROPIC_BASE_URL"] == f"{BASE}/anthropic"


def test_build_env_pairs_wires_passthrough_spec(aikit):
    specs = [{"route": "/sourcegraph", "auth_var": "AMP_API_KEY",
              "base_url_var": "AMP_URL", "auth_mode": "virtual_key"}]
    pairs = dict(aikit.build_env_pairs(BASE, SECRET, passthroughs=specs))
    assert pairs["AMP_URL"] == f"{BASE}/sourcegraph"
    assert pairs["AMP_API_KEY"] == SECRET


def test_build_env_pairs_forwarded_token_leaves_auth_var(aikit):
    specs = [{"route": "/anthropic", "auth_var": "ANTHROPIC_AUTH_TOKEN",
              "base_url_var": "SOME_BASE", "auth_mode": "forwarded_token"}]
    pairs = dict(aikit.build_env_pairs(BASE, SECRET, passthroughs=specs))
    assert pairs["SOME_BASE"] == f"{BASE}/anthropic"        # base URL is redirected
    # ANTHROPIC_AUTH_TOKEN still comes from the universal anthropic block (=key), but the
    # spec must NOT add a fresh forwarded-token override; check it didn't duplicate wrong.
    assert pairs["ANTHROPIC_AUTH_TOKEN"] == SECRET          # from the provider block only


def test_build_env_pairs_forwarded_prefix_skips_provider_key(aikit):
    # Claude Code Max: forwarded-token mode must NOT overwrite ANTHROPIC_AUTH_TOKEN with
    # the virtual key — the caller's own OAuth token is forwarded upstream instead.
    pairs = dict(aikit.build_env_pairs(
        BASE, SECRET, forwarded_token_prefixes=frozenset({"anthropic"})))
    assert "ANTHROPIC_AUTH_TOKEN" not in pairs
    assert "ANTHROPIC_API_KEY" not in pairs
    assert pairs["ANTHROPIC_BASE_URL"] == f"{BASE}/anthropic"   # base URL still set


# --- custom-route config + credential mode ----------------------------------
def test_save_gateway_config_preserves_custom_passthroughs(aikit, gw):
    _write_gateway_config(gw, passthroughs={"amp": {"route": "/x"}},
                          credential_mode="forwarded_token")
    aikit.save_gateway_config("https://new.example.com", "sk-new")
    cfg = aikit.load_gateway_config()
    assert cfg["base_url"] == "https://new.example.com"
    assert cfg["passthroughs"] == {"amp": {"route": "/x"}}      # not clobbered
    assert cfg["credential_mode"] == "forwarded_token"


def test_load_custom_passthroughs_and_credential_mode(aikit, gw):
    assert aikit.load_custom_passthroughs() == {}               # unconfigured → empty
    assert aikit.gateway_credential_mode() == "virtual_key"     # default
    _write_gateway_config(gw, passthroughs={"amp": {"route": "/x"}},
                          credential_mode="forwarded_token")
    assert aikit.load_custom_passthroughs() == {"amp": {"route": "/x"}}
    assert aikit.gateway_credential_mode() == "forwarded_token"


def test_credential_mode_rejects_garbage(aikit, gw):
    _write_gateway_config(gw, credential_mode="nonsense")
    assert aikit.gateway_credential_mode() == "virtual_key"     # falls back to default


# --- `verify` command -------------------------------------------------------
def test_verify_reports_routes_and_flags_401(aikit, gw, capsys):
    _write_gateway_config(gw)
    gw.probe[f"{BASE}/anthropic/v1/models"] = 401              # mounted but mis-credentialed
    gw.probe[f"{BASE}/openai/v1/models"] = 200
    aikit.do_gateway_verify(BASE, SECRET)
    out = capsys.readouterr().out
    assert "Passthrough routes" in out
    assert "/anthropic" in out and "/openai" in out
    assert "Mounted but unauthorized" in out                   # the 401 warning
    assert "/anthropic" in out
    assert SECRET not in out                                    # key never printed


def test_verify_shows_tools_resolved_to_passthrough(aikit, gw, capsys):
    _write_gateway_config(gw, passthroughs={"amp": {"route": "/anthropic",
                          "auth_var": "AMP_API_KEY", "base_url_var": "AMP_URL"}})
    gw.probe[f"{BASE}/anthropic/v1/models"] = 200
    aikit.do_gateway_verify(BASE, SECRET)
    out = capsys.readouterr().out
    assert "resolved to passthrough" in out and "amp" in out


# --- `on` integration -------------------------------------------------------
def test_on_wires_custom_passthrough_into_env_block(aikit, gw, capsys):
    _write_gateway_config(gw, passthroughs={"amp": {"route": "/anthropic",
                          "auth_var": "AMP_API_KEY", "base_url_var": "AMP_URL"}})
    gw.detected.add("amp")
    aikit.do_gateway_on(BASE, SECRET, yes=True)
    out = capsys.readouterr().out
    assert "Passthrough-routed tool" in out
    # The managed env block on disk wires amp's base-URL override at the route.
    env_text = (gw.gwdir / "gateway.env").read_text()
    assert f"AMP_URL={BASE}/anthropic" in env_text or f'AMP_URL="{BASE}/anthropic"' in env_text
    assert "Routed via native passthrough" in out             # honest accounting


def test_on_warns_when_wired_passthrough_probes_401(aikit, gw, capsys):
    _write_gateway_config(gw, passthroughs={"amp": {"route": "/anthropic",
                          "auth_var": "AMP_API_KEY", "base_url_var": "AMP_URL"}})
    gw.probe[f"{BASE}/anthropic/v1/models"] = 401
    aikit.do_gateway_on(BASE, SECRET, yes=True)
    out = capsys.readouterr().out
    assert "mounted but returned HTTP 401" in out
    assert "aikit gateway verify" in out


def test_on_without_custom_passthroughs_does_not_probe(aikit, gw, monkeypatch, capsys):
    # No custom passthroughs wired → `on` must not touch the network at all.
    def fail(*a, **k):
        raise AssertionError("on probed the network with no passthrough tools wired")
    monkeypatch.setattr(aikit, "_probe_status", fail)
    aikit.do_gateway_on(BASE, SECRET, yes=True)
    out = capsys.readouterr().out
    assert "Gateway enabled" in out or "vars route through" in out


def test_coverage_command_shows_custom_passthrough(aikit, gw, capsys):
    _write_gateway_config(gw, passthroughs={"amp": {"route": "/sourcegraph",
                          "auth_var": "AMP_API_KEY", "base_url_var": "AMP_URL"}})
    gw.detected.add("amp")
    aikit.do_gateway_coverage()
    out = capsys.readouterr().out
    assert "passthrough" in out and "amp" in out
    assert "aikit gateway verify" in out                       # points at the live probe
