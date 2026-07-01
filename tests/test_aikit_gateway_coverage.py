"""Unit tests for the aikit gateway coverage capability model (POK-66).

The model is the single source of truth for how (and whether) each agent reaches
the gateway. These tests pin: every agent in AGENTS is classified into exactly one
state (renderer/env/pending/unsupported) with no silent omission; renderer state
derives from GATEWAY_TOOL_SPECS; and `coverage`/`status`/`on` account for env-routed
and unsupported agents, not just the 9 wrapped tools. Detection is mocked; no network.
"""

from __future__ import annotations

import types

import pytest

BASE = "https://gw.example.com"
SECRET = "sk-secret-key-1234567890"
MODELS = ["anthropic/claude-3", "openai/gpt-4o"]
DETAIL = {"openai/gpt-4o": {"provider": "openai", "max_tokens": 200000}}


@pytest.fixture
def aikit(tool_loader):
    return tool_loader("aikit")


@pytest.fixture
def gw(aikit, tmp_path, monkeypatch):
    """Isolated gateway: temp HOME + gateway dir, mocked discovery, controllable
    tool detection via the returned ``detected`` set (mirrors the tools-test fixture)."""
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
    return types.SimpleNamespace(aikit=aikit, home=home, rc=rc, gwdir=gwdir, detected=detected)


# --- model: completeness + no silent omission -------------------------------
def test_coverage_classifies_every_agent(aikit):
    cov = aikit.gateway_coverage()
    # Every agent in the registry is classified — the anti-silent-omission guarantee.
    assert set(cov) == set(aikit.AGENTS)
    assert len(cov) == 26


def test_coverage_bucket_counts_match_audit(aikit):
    cov = aikit.gateway_coverage()
    counts: dict = {}
    for c in cov.values():
        counts[c["state"]] = counts.get(c["state"], 0) + 1
    assert counts == {"renderer": 12, "env": 6, "pending": 3, "unsupported": 5}
    assert "unclassified" not in counts   # nothing left uncategorised


def test_renderer_state_derives_from_tool_specs(aikit):
    cov = aikit.gateway_coverage()
    renderer = {k for k, v in cov.items() if v["state"] == "renderer"}
    spec_keys = {agent_key for _, agent_key, _, _, _ in aikit.GATEWAY_TOOL_SPECS}
    assert renderer == spec_keys


def test_every_coverage_entry_has_a_reason_or_route(aikit):
    # renderer/env carry a `via`; pending/unsupported carry a `reason`. Never blank —
    # `coverage` must always have something to show in the How/why column.
    for key, c in aikit.gateway_coverage().items():
        assert c.get("via") or c.get("reason"), f"{key} has no via/reason"


def test_known_agents_land_in_expected_buckets(aikit):
    cov = aikit.gateway_coverage()
    assert cov["opencode"]["state"] == "renderer"
    assert cov["claude"]["state"] == "env"
    assert cov["qwen"]["state"] == "renderer"      # POK-67: now a native renderer
    assert cov["openhands"]["state"] == "env"      # POK-67: wired via LLM_* env vars
    assert cov["copilot"]["state"] == "unsupported"
    # env routes name the actual var; unsupported names the blocking backend.
    assert "ANTHROPIC_BASE_URL" in cov["claude"]["via"]
    assert cov["copilot"]["reason"]


def test_unclassified_agent_is_surfaced_not_dropped(aikit, monkeypatch):
    # A newly-registered agent with no coverage entry must appear as `unclassified`
    # (visible, with guidance) rather than silently vanish from the report.
    patched = dict(aikit.AGENTS)
    patched["brandnew"] = {"name": "Brand New", "bin": "brandnew"}
    monkeypatch.setattr(aikit, "AGENTS", patched)
    cov = aikit.gateway_coverage()
    assert cov["brandnew"]["state"] == "unclassified"
    assert cov["brandnew"]["reason"]                       # tells the maintainer what to do


# --- rows builder -----------------------------------------------------------
def test_coverage_rows_span_all_agents_in_state_order(aikit):
    rows = aikit.gateway_coverage_rows(detector=lambda k: False)
    assert len(rows) == 26
    assert {r["id"] for r in rows} == set(aikit.AGENTS)
    # Grouped: the first 12 rows are the renderer set (sorted within the group).
    assert all(r["state"] == "renderer" for r in rows[:12])
    assert [r["id"] for r in rows[:12]] == sorted(
        {agent_key for _, agent_key, _, _, _ in aikit.GATEWAY_TOOL_SPECS})


def test_coverage_rows_detected_reflects_detector(aikit):
    rows = aikit.gateway_coverage_rows(detector=lambda k: k in {"claude", "kilo"})
    detected = {r["id"] for r in rows if r["detected"]}
    assert detected == {"claude", "kilo"}


def test_detected_unrouted_and_env_helpers(aikit):
    rows = aikit.gateway_coverage_rows(
        detector=lambda k: k in {"opencode", "claude", "kimi", "copilot"})
    assert aikit._coverage_detected_env(rows) == ["claude"]
    unrouted = dict(aikit._coverage_detected_unrouted(rows))
    assert unrouted == {"kimi": "pending", "copilot": "unsupported"}
    # a routed renderer tool is NOT reported as unrouted
    assert "opencode" not in unrouted


# --- `coverage` command output ----------------------------------------------
def test_coverage_command_accounts_for_every_state(aikit, monkeypatch, capsys):
    monkeypatch.setattr(aikit, "detect_gateway_tool",
                        lambda k: k in {"opencode", "claude", "kimi", "copilot"})
    aikit.do_gateway_coverage()
    out = capsys.readouterr().out
    # env-routed, pending, and unsupported agents all appear — none silently omitted.
    for name in ("opencode", "claude", "qwen", "openhands", "copilot", "cursor"):
        assert name in out
    assert "renderer" in out and "env" in out and "pending" in out and "unsupported" in out
    assert "12 renderer" in out                             # the per-state tally
    assert "Detected but not routed" in out                 # honest unrouted warning
    assert "kimi (pending)" in out and "copilot (unsupported)" in out


# --- `on` / `status` account for env + unsupported, not just wrapped tools ---
def test_on_reports_env_routed_and_unrouted(aikit, gw, capsys):
    gw.detected.update({"opencode", "claude", "openhands", "kimi", "copilot"})
    aikit.do_gateway_on(BASE, SECRET, yes=True)
    out = capsys.readouterr().out
    assert "Also routed via env" in out and "claude" in out
    assert "openhands" in out                               # POK-67: env-routed via LLM_*
    assert "Detected but not routed through the gateway" in out
    assert "kimi (pending)" in out
    assert "copilot (unsupported)" in out
    assert SECRET not in out                                # key never printed


def test_on_dry_run_still_accounts_for_coverage(aikit, gw, capsys):
    gw.detected.update({"claude", "kimi"})
    aikit.do_gateway_on(BASE, SECRET, dry_run=True)
    out = capsys.readouterr().out
    assert "Also routed via env" in out and "claude" in out
    assert "kimi (pending)" in out
    assert SECRET not in out


def test_status_accounts_for_env_and_unsupported(aikit, gw, capsys):
    gw.detected.update({"opencode", "claude", "copilot"})
    aikit.do_gateway_on(BASE, SECRET, yes=True)
    capsys.readouterr()                                     # drop `on` output
    aikit.do_gateway_status()
    out = capsys.readouterr().out
    assert "Wrapped tools" in out                           # existing renderer table
    assert "Also routed via env" in out and "claude" in out
    assert "copilot (unsupported)" in out                   # not silently omitted


def test_on_with_only_wrapped_tools_stays_quiet_about_others(aikit, gw, capsys):
    # No env/pending/unsupported tools detected → no accounting noise beyond the plan.
    gw.detected.update({"opencode"})
    aikit.do_gateway_on(BASE, SECRET, yes=True)
    out = capsys.readouterr().out
    assert "Also routed via env" not in out
    assert "Detected but not routed" not in out
