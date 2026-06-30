"""Unit tests for the aikit gateway native per-tool config layer (Stage 3).

Pure renderers (valid JSON/TOML/YAML, models present, env-ref not inlined secret),
the install plan (never-clobber policy), the portable `gateway.env`/`gateway.json`
files, and an `on`→`off` round-trip on a temp HOME proving every file aikit created
is removed while a pre-existing user config is left untouched. Detection + filesystem
are mocked; no real network.
"""

from __future__ import annotations

import json
import tomllib
import types

import pytest
from ruamel.yaml import YAML

_yaml = YAML(typ="safe")

BASE = "https://gw.example.com"
MODELS = ["anthropic/claude-3", "openai/gpt-4o"]
DETAIL = {"openai/gpt-4o": {"provider": "openai", "max_tokens": 200000}}
SECRET = "sk-secret-key-1234567890"

JSON_RENDERERS = ("render_opencode", "render_crush", "render_pi", "render_continue")
# Renderers that embed an OPENAI_API_KEY *reference* (never the literal key).
ENV_REF_RENDERERS = ("render_opencode", "render_codex", "render_crush", "render_pi",
                     "render_hermes", "render_aider", "render_goose", "render_continue")
ALL_RENDERERS = JSON_RENDERERS + ("render_codex", "render_goose", "render_hermes",
                                  "render_aider", "render_llm")


@pytest.fixture
def aikit(tool_loader):
    return tool_loader("aikit")


def _yaml_load(text):
    return _yaml.load(text)


# --- renderers: each in its native schema -----------------------------------
def test_render_opencode_json_env_ref_and_models(aikit):
    cfg = json.loads(aikit.render_opencode(BASE, MODELS, DETAIL))
    prov = cfg["provider"]["litellm"]
    assert prov["options"]["baseURL"] == "https://gw.example.com/v1"
    assert prov["options"]["apiKey"] == "{env:OPENAI_API_KEY}"   # env ref, not the key
    assert set(prov["models"]) == set(MODELS)


def test_render_codex_toml_provider_and_env_key(aikit):
    data = tomllib.loads(aikit.render_codex(BASE, MODELS, DETAIL))
    assert data["model_provider"] == "litellm"
    prov = data["model_providers"]["litellm"]
    assert prov["base_url"] == "https://gw.example.com/v1"
    assert prov["env_key"] == "OPENAI_API_KEY"
    assert data["model"] == "anthropic/claude-3"                 # first discovered model


def test_render_crush_json_models_carry_context_window(aikit):
    cfg = json.loads(aikit.render_crush(BASE, MODELS, DETAIL))
    prov = cfg["providers"]["litellm"]
    assert prov["type"] == "openai-compat"
    assert prov["api_key"] == "$OPENAI_API_KEY"
    by_id = {m["id"]: m for m in prov["models"]}
    assert [m["id"] for m in prov["models"]] == MODELS
    assert by_id["openai/gpt-4o"]["context_window"] == 200000    # from detail
    assert by_id["anthropic/claude-3"]["context_window"] == 128000  # fallback


def test_render_goose_yaml_host_and_model(aikit):
    data = _yaml_load(aikit.render_goose(BASE, MODELS, DETAIL))
    assert data["GOOSE_PROVIDER"] == "openai"
    assert data["OPENAI_HOST"] == BASE
    assert data["GOOSE_MODEL"] == "anthropic/claude-3"


def test_render_pi_json_shell_key_ref(aikit):
    prov = json.loads(aikit.render_pi(BASE, MODELS, DETAIL))["providers"]["litellm"]
    assert prov["baseUrl"] == "https://gw.example.com/v1"
    assert "$OPENAI_API_KEY" in prov["apiKey"]                   # resolved via shell
    assert [m["id"] for m in prov["models"]] == MODELS


def test_render_hermes_yaml_env_ref(aikit):
    model = _yaml_load(aikit.render_hermes(BASE, MODELS, DETAIL))["model"]
    assert model["base_url"] == "https://gw.example.com/v1"
    assert model["api_key"] == "${OPENAI_API_KEY}"
    assert model["default"] == "anthropic/claude-3"


def test_render_aider_yaml(aikit):
    data = _yaml_load(aikit.render_aider(BASE, MODELS, DETAIL))
    assert data["openai-api-base"] == "https://gw.example.com/v1"
    assert data["openai-api-key"] == "$OPENAI_API_KEY"
    assert data["model"] == "openai/anthropic/claude-3"


def test_render_llm_yaml_list_of_models(aikit):
    data = _yaml_load(aikit.render_llm(BASE, MODELS, DETAIL))
    assert [d["model_id"] for d in data] == MODELS
    assert all(d["api_base"] == "https://gw.example.com/v1" for d in data)


def test_render_continue_json_models(aikit):
    cfg = json.loads(aikit.render_continue(BASE, MODELS, DETAIL))
    assert [m["title"] for m in cfg["models"]] == MODELS
    assert all(m["apiBase"] == "https://gw.example.com/v1" for m in cfg["models"])


def test_no_renderer_inlines_a_secret(aikit):
    # Renderers don't even receive the key — they *cannot* inline it. Assert the
    # output never contains a key-looking literal, regardless of detail contents.
    for name in ALL_RENDERERS:
        out = getattr(aikit, name)(BASE, MODELS, DETAIL)
        assert "sk-" not in out


def test_env_ref_renderers_reference_the_env_var(aikit):
    for name in ENV_REF_RENDERERS:
        out = getattr(aikit, name)(BASE, MODELS, DETAIL)
        assert "OPENAI_API_KEY" in out


def test_render_empty_models_is_still_valid(aikit):
    # No models discovered → renderers still emit valid documents.
    json.loads(aikit.render_opencode(BASE, [], {}))
    tomllib.loads(aikit.render_codex(BASE, [], {}))
    assert _yaml_load(aikit.render_llm(BASE, [], {})) is None  # just the comment header


# --- portable files ---------------------------------------------------------
def test_render_gateway_env_exports_pairs_including_key(aikit):
    out = aikit.render_gateway_env([("OPENAI_API_KEY", SECRET),
                                    ("OPENAI_BASE_URL", "https://gw/v1")])
    assert f'export OPENAI_API_KEY="{SECRET}"' in out            # the key lives here
    assert 'export OPENAI_BASE_URL="https://gw/v1"' in out


def test_render_gateway_summary_is_valid_json(aikit):
    data = json.loads(aikit.render_gateway_summary(BASE, MODELS, DETAIL,
                                                   "2026-06-30T00:00:00Z"))
    assert data["gateway_url"] == BASE
    assert data["openai_compatible_base"] == "https://gw.example.com/v1"
    assert data["generated"] == "2026-06-30T00:00:00Z"
    assert len(data["providers"]) == len(aikit.GATEWAY_PROVIDERS)
    assert {m["id"] for m in data["models"]} == set(MODELS)


# --- install plan (never-clobber) -------------------------------------------
def test_gateway_tool_plan_actions(aikit, tmp_path):
    (tmp_path / ".aider.conf.yml").write_text("# my aider\n")   # pre-existing → keep
    detector = lambda key: key in {"opencode", "aider"}          # codex absent
    plan = {p["id"]: p for p in
            aikit.gateway_tool_plan(BASE, MODELS, DETAIL, home=tmp_path, detector=detector)}
    assert plan["opencode"]["action"] == "install"              # detected, no config
    assert plan["aider"]["action"] == "keep-existing"           # detected, config exists
    assert plan["codex"]["action"] == "not-detected"            # not installed
    assert plan["llm"]["action"] == "staged-only"               # target path varies
    assert plan["continue"]["action"] == "staged-only"
    assert len(plan) == 9


# --- helpers: dir creation/pruning ------------------------------------------
def test_dirs_to_create_innermost_first_stops_at_existing(aikit, tmp_path):
    leaf = tmp_path / "a" / "b" / "c"
    dirs = aikit._dirs_to_create(leaf)
    assert dirs[0] == leaf and dirs[-1] == tmp_path / "a"        # innermost → outermost
    (tmp_path / "a").mkdir()
    assert (tmp_path / "a") not in aikit._dirs_to_create(leaf)   # existing ancestor excluded


def test_undo_config_file_prunes_created_dirs(aikit, tmp_path):
    target = tmp_path / "x" / "y" / "cfg.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}")
    aikit._undo_config_file({"path": str(target), "created_by_aikit": True,
                             "created_dirs": [str(target.parent),
                                              str(target.parent.parent)]})
    assert not target.exists()
    assert not (tmp_path / "x").exists()                          # both empty dirs pruned


# --- on → off round-trip on a temp HOME -------------------------------------
@pytest.fixture
def gw(aikit, tmp_path, monkeypatch):
    """Isolated gateway: temp HOME + gateway dir, mocked discovery, controllable
    tool detection via the returned ``detected`` set."""
    home = tmp_path
    rc = home / ".zshrc"
    rc.write_text("# rc\n")
    detected: set = set()
    gwdir = home / ".aikit" / "gateway"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(aikit, "GATEWAY_DIR", gwdir)
    monkeypatch.setattr(aikit, "GATEWAY_CONFIG_FILE", gwdir / "config.json")
    monkeypatch.setattr(aikit, "GATEWAY_STATE_FILE", gwdir / "state.json")
    monkeypatch.setattr(aikit, "detect_shell", lambda explicit=None: ("zsh", rc))
    monkeypatch.setattr(aikit, "discover_models", lambda u, k, **kw: (MODELS, DETAIL))
    monkeypatch.setattr(aikit, "detect_gateway_tool", lambda key: key in detected)
    return types.SimpleNamespace(aikit=aikit, home=home, rc=rc, gwdir=gwdir,
                                 detected=detected)


def test_on_writes_files_installs_detected_only_then_off_is_pristine(aikit, gw):
    home = gw.home
    gw.detected.update({"opencode", "aider"})
    aider_cfg = home / ".aider.conf.yml"
    aider_cfg.write_text("# MY aider config — keep me\n")        # pre-existing user config
    aider_before = aider_cfg.read_text()

    aikit.do_gateway_on(BASE, SECRET, yes=True)

    env_file = gw.gwdir / "gateway.env"
    summary_file = gw.gwdir / "gateway.json"
    tools_dir = gw.gwdir / "tools"
    opencode_cfg = home / ".config" / "opencode" / "opencode.json"

    # portable files: gateway.env holds the key at 0600; gateway.json has no key
    assert env_file.exists() and summary_file.exists()
    assert (env_file.stat().st_mode & 0o777) == 0o600
    assert SECRET in env_file.read_text()
    assert SECRET not in summary_file.read_text()
    assert json.loads(summary_file.read_text())["openai_compatible_base"] == f"{BASE}/v1"

    # all nine configs staged, none leaking the secret
    assert sum(1 for _ in tools_dir.iterdir()) == 9
    for f in tools_dir.iterdir():
        assert SECRET not in f.read_text()

    # detected + absent → installed; detected + pre-existing → kept untouched
    assert opencode_cfg.exists()
    assert aider_cfg.read_text() == aider_before
    assert not (home / ".codex" / "config.toml").exists()        # codex not detected

    manifest = aikit.read_manifest()
    roles = [e["role"] for e in manifest["config_files"]]
    assert roles.count("portable") == 2
    assert roles.count("staged") == 9
    assert roles.count("installed") == 1                         # opencode only

    # off → every aikit-created file removed; created dir pruned; user config kept
    aikit.do_gateway_off()
    assert not env_file.exists()
    assert not summary_file.exists()
    assert not opencode_cfg.exists()
    assert not (home / ".config" / "opencode").exists()          # empty dir pruned
    assert not any(tools_dir.iterdir())                          # staged copies gone
    assert aider_cfg.read_text() == aider_before                 # still pristine
    assert aikit.read_manifest() == {}

    # second off → clean no-op
    aikit.do_gateway_off()
    assert aider_cfg.read_text() == aider_before


def test_on_then_on_is_stable(aikit, gw):
    gw.detected.add("opencode")
    aikit.do_gateway_on(BASE, "sk-key-1234567890", yes=True)
    files1 = [e["path"] for e in aikit.read_manifest()["config_files"]]
    aikit.do_gateway_on(BASE, "sk-key-1234567890", yes=True)
    m2 = aikit.read_manifest()
    assert m2["active"] is True
    assert files1 == [e["path"] for e in m2["config_files"]]     # same file set
    assert (gw.home / ".config" / "opencode" / "opencode.json").exists()


def test_on_then_on_then_off_leaves_no_orphaned_install(aikit, gw):
    # Regression: run 1 installs opencode; run 2 sees aikit's own config and must
    # re-own it (not treat it as a user file), so a single `off` still removes it.
    gw.detected.add("opencode")
    opencode_cfg = gw.home / ".config" / "opencode" / "opencode.json"

    aikit.do_gateway_on(BASE, "sk-key-1234567890", yes=True)
    assert opencode_cfg.exists()
    aikit.do_gateway_on(BASE, "sk-key-1234567890", yes=True)    # re-apply
    assert opencode_cfg.exists()
    assert aikit.read_manifest()["config_files"]                # still tracked as ours

    aikit.do_gateway_off()
    assert not opencode_cfg.exists()                            # no orphan left behind
    assert not (gw.home / ".config" / "opencode").exists()      # created dir pruned too


def test_on_dry_run_writes_no_config_files(aikit, gw, capsys):
    gw.detected.add("opencode")
    aikit.do_gateway_on(BASE, SECRET, dry_run=True)
    assert not (gw.gwdir / "gateway.env").exists()
    assert not (gw.home / ".config" / "opencode" / "opencode.json").exists()
    assert aikit.read_manifest() == {}
    out = capsys.readouterr().out
    assert "Native per-tool config" in out
    assert SECRET not in out                                     # key never printed


def test_status_lists_wrapped_tools(aikit, gw, capsys):
    gw.detected.update({"opencode", "aider"})
    (gw.home / ".aider.conf.yml").write_text("# pre-existing\n")
    aikit.do_gateway_on(BASE, "sk-key-1234567890", yes=True)
    capsys.readouterr()                                          # drop `on` output

    aikit.do_gateway_status()
    assert "Wrapped tools" in capsys.readouterr().out

    rows = {r[0]: r for r in aikit.gateway_tool_status(aikit.read_manifest(),
                                                       home=gw.home)}
    assert rows["opencode"][1] == "yes"
    assert "installed by aikit" in rows["opencode"][2]
    assert "user config (kept)" in rows["aider"][2]
    assert "staged only" in rows["llm"][2]                       # target path varies
