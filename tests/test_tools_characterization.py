"""Characterization tests for the CLI tools.

These pin observable behavior (pure helpers + parser/--help) so the scriptkit
refactor is provably non-breaking: every assertion here passes before and
after the tools are rewired onto the shared library.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ALL_TOOLS = ["scripts", "pluck", "netsy", "keyferry", "aikit", "medcat", "voxtract"]


# --- smoke: every tool imports and exposes a version ----------------------
@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_tool_imports_and_has_version(tool, tool_loader):
    mod = tool_loader(tool)
    assert isinstance(mod.__version__, str) and mod.__version__


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_tool_help_runs(tool):
    """`<tool> --help` exits 0 and prints the program name."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / tool), "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert tool in proc.stdout


# Canonical brand emoji per tool — the unified identity line every tool shows.
TOOL_ICONS = {
    "scripts": "🛠", "aikit": "🤖", "keyferry": "🛳", "medcat": "📚",
    "netsy": "📡", "pluck": "🪶", "voxtract": "🌊",
}


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_tool_help_has_unified_identity(tool, tool_loader):
    """Every tool's --help shows `{icon} {name} v{version} — {tagline}`."""
    mod = tool_loader(tool)
    version = mod.__version__
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / tool), "--help"],
        capture_output=True, text=True, timeout=60, env={**os.environ, "NO_COLOR": "1"},
    )
    out = proc.stdout
    assert TOOL_ICONS[tool] in out, f"{tool} missing brand emoji"
    assert f"{tool} v{version} —" in out, f"{tool} missing unified identity line"


@pytest.mark.parametrize("tool", ALL_TOOLS)
def test_tool_version_flag(tool):
    """Every tool supports `-v`/`--version` printing `<tool> <version>`, exit 0."""
    for flag in ("-v", "--version"):
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / tool), flag],
            capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0, f"{tool} {flag}: {proc.stderr}"
        assert tool in proc.stdout


# --- build_parser smoke ----------------------------------------------------
@pytest.mark.parametrize("tool", ["scripts", "pluck", "netsy", "keyferry", "aikit", "medcat"])
def test_build_parser_exists(tool, tool_loader):
    mod = tool_loader(tool)
    parser = mod.build_parser()
    assert parser is not None


# --- pluck -----------------------------------------------------------------
def test_pluck_parse_path(tool_loader):
    m = tool_loader("pluck")
    assert m.parse_path("foo.bar") == ["foo", "bar"]
    assert m.parse_path("foo.bar[0].baz") == ["foo", "bar", 0, "baz"]
    assert m.parse_path("a[2]") == ["a", 2]


def test_pluck_parse_path_errors(tool_loader):
    m = tool_loader("pluck")
    with pytest.raises(m.PluckError):
        m.parse_path("")
    with pytest.raises(m.PluckError):
        m.parse_path("a..b")
    with pytest.raises(m.PluckError):
        m.parse_path("a[x]")
    with pytest.raises(m.PluckError):
        m.parse_path("a[0")


def test_pluck_deep_merge(tool_loader):
    m = tool_loader("pluck")
    assert m.deep_merge({"a": {"b": 1}}, {"a": {"c": 2}}) == {"a": {"b": 1, "c": 2}}


def test_pluck_path_to_env_key(tool_loader):
    m = tool_loader("pluck")
    assert m.path_to_env_key("foo.bar") == "FOO_BAR"
    assert m.path_to_env_key("a.b[2]") == "A_B_2"


# --- pluck: end-to-end file operations ------------------------------------
# The pure helpers above never touch the dispatch → handler_for → load/save
# path — which is the entire tool. These round-trips pin that path end to end:
# a regression in the format-handler wiring or the TOML writer breaks get/set
# for real files (and no assertion above would notice). JSON and .env need no
# third-party deps so they always run; YAML/TOML skip if their writer is absent.
_PLUCK_SAMPLES = {
    "json": ('{"model": "gpt-4o", "web": {"port": 8080}}', "web.port", 8080),
    "env": ("MODEL=gpt-4o\n", "MODEL", "gpt-4o"),
    "yaml": ("model: gpt-4o\nweb:\n  port: 8080\n", "web.port", 8080),
    "toml": ('model = "gpt-4o"\n[web]\nport = 8080\n', "web.port", 8080),
}


def _run_pluck(*args):
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "pluck"), *args],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "NO_COLOR": "1"},
    )


def _require_writer(fmt):
    """Skip when the optional writer for ``fmt`` isn't installed."""
    if fmt == "yaml":
        pytest.importorskip("ruamel.yaml")
    if fmt == "toml":
        pytest.importorskip("tomli_w")


@pytest.mark.parametrize("fmt", ["json", "env", "yaml", "toml"])
def test_pluck_get_reads_value(tmp_path, fmt):
    """`pluck get` resolves a path in every format, via both output modes."""
    body, key, expected = _PLUCK_SAMPLES[fmt]
    cfg = tmp_path / f"config.{fmt}"
    cfg.write_text(body)
    # machine-readable mode: exact value on stdout
    proc = _run_pluck("get", "--json", str(cfg), key)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == expected
    # default (rich panel) display mode must also succeed and show the value
    proc = _run_pluck("get", str(cfg), key)
    assert proc.returncode == 0, proc.stderr
    assert str(expected) in proc.stdout


def test_pluck_get_toml_display_needs_no_writer(tmp_path):
    """Default (panel) `get` on TOML must not require the tomli-w *writer*.

    Reading TOML uses stdlib ``tomllib``; only rendering the value back as TOML
    needed ``tomli_w``. Simulate the writer's absence by shadowing it with a
    module that fails to import, and assert a plain `get` (no ``--json``) still
    succeeds — the exact tomli-w-absent venv this issue targets. (``--json``
    renders via ``json.dumps`` and never needed the writer.)
    """
    shim = tmp_path / "no_writer"
    shim.mkdir()
    (shim / "tomli_w.py").write_text('raise ImportError("simulated: tomli-w absent")\n')
    cfg = tmp_path / "config.toml"
    cfg.write_text('model = "gpt-4o"\n[web]\nport = 8080\n')
    env = {
        **os.environ,
        "NO_COLOR": "1",
        "PYTHONPATH": str(shim) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "pluck"), "get", str(cfg), "web.port"],
        capture_output=True, text=True, timeout=60, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "8080" in proc.stdout


@pytest.mark.parametrize("fmt", ["json", "env", "yaml", "toml"])
def test_pluck_set_roundtrips(tmp_path, fmt):
    """`pluck set` writes a value that `pluck get` reads back, every format."""
    _require_writer(fmt)
    body, key, _ = _PLUCK_SAMPLES[fmt]
    cfg = tmp_path / f"config.{fmt}"
    cfg.write_text(body)
    assert _run_pluck("set", str(cfg), key, "xyzzy-42").returncode == 0
    proc = _run_pluck("get", "--json", str(cfg), key)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == "xyzzy-42"


# --- netsy -----------------------------------------------------------------
def test_netsy_parse_subnet_valid(tool_loader):
    m = tool_loader("netsy")
    assert m.parse_subnet("192.168.1.0/24") == "192.168.1.0/24"
    assert m.parse_subnet("10.0.0.5/24") == "10.0.0.0/24"  # strict=False normalizes


def test_netsy_parse_nmap_output(tool_loader):
    m = tool_loader("netsy")
    sample = (
        "Nmap scan report for router.local (192.168.1.1)\n"
        "Host is up (0.0030s latency).\n"
        "MAC Address: AA-BB-CC-DD-EE-FF (Acme Corp)\n"
        "Nmap scan report for 192.168.1.50\n"
        "Host is up.\n"
    )
    hosts = m.parse_nmap_output(sample)
    assert len(hosts) == 2
    assert hosts[0]["ip"] == "192.168.1.1"
    assert hosts[0]["hostname"] == "router.local"
    assert hosts[0]["mac"] == "AA:BB:CC:DD:EE:FF"
    assert hosts[0]["vendor"] == "Acme Corp"
    assert hosts[1]["ip"] == "192.168.1.50"


def test_netsy_print_table_no_extra_column(tool_loader):
    """A plain scan must render exactly four columns — no blank trailing column.

    Regression for POK-55: print_table used to always pass five row values
    (including an empty `seen`), so rich auto-created a headerless fifth
    column after Vendor whenever stability tracking was off.
    """
    m = tool_loader("netsy")
    hosts = [
        {
            "hostname": "router.local",
            "ip": "192.168.1.1",
            "mac": "AA:BB:CC:DD:EE:FF",
            "vendor": "Acme Corp",
        }
    ]

    with m.console.capture() as capture:
        m.print_table(hosts, "192.168.1.0/24", show_stability=False)
    output = capture.get()

    header_line = next(line for line in output.splitlines() if "Hostname" in line)
    # Four columns ⇒ five vertical separators in the header row.
    assert header_line.count("┃") == 5
    assert "Vendor" in header_line


def test_netsy_print_table_shows_seen_column_when_stable(tool_loader):
    """Multi-pass scans keep the fifth 'Seen' column (show_stability=True)."""
    m = tool_loader("netsy")
    hosts = [
        {
            "hostname": "router.local",
            "ip": "192.168.1.1",
            "mac": "AA:BB:CC:DD:EE:FF",
            "vendor": "Acme Corp",
            "passes_seen": "3",
            "pass_total": "3",
        }
    ]

    with m.console.capture() as capture:
        m.print_table(hosts, "192.168.1.0/24", show_stability=True)
    output = capture.get()

    header_line = next(line for line in output.splitlines() if "Hostname" in line)
    assert header_line.count("┃") == 6  # five columns
    assert "Seen" in header_line


# --- keyferry --------------------------------------------------------------
def test_keyferry_config_nested(tool_loader):
    m = tool_loader("keyferry")
    cfg = {}
    m._config_set_nested(cfg, "a.b.c", 5)
    assert m._config_get_nested(cfg, "a.b.c") == 5
    assert m._config_get_nested(cfg, "a.x") is None


def test_keyferry_deep_merge(tool_loader):
    m = tool_loader("keyferry")
    assert m._deep_merge({"a": {"b": 1}}, {"a": {"c": 2}}) == {"a": {"b": 1, "c": 2}}


def test_keyferry_bw_install_hint(tool_loader, monkeypatch):
    m = tool_loader("keyferry")
    monkeypatch.setattr(m.platform, "system", lambda: "Darwin")
    assert "brew install bitwarden-cli" in m.bw_install_hint()
    assert m.BW_CLI_RELEASES in m.bw_install_hint()
    monkeypatch.setattr(m.platform, "system", lambda: "Windows")
    assert "choco install bitwarden-cli" in m.bw_install_hint()
    monkeypatch.setattr(m.platform, "system", lambda: "Linux")
    assert "snap install bw" in m.bw_install_hint()


# --- aikit -----------------------------------------------------------------
def test_aikit_config_nested(tool_loader):
    m = tool_loader("aikit")
    cfg = {}
    m._config_set_nested(cfg, "settings.web_port", 9000)
    assert m._config_get_nested(cfg, "settings.web_port") == 9000


def test_aikit_config_from_env(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setenv("AIKIT_SETTINGS__WEB_PORT", "1234")
    out = m._config_from_env()
    # aikit coerces scalar env strings to their natural types.
    assert out.get("settings", {}).get("web_port") == 1234


def test_aikit_config_set_nested_coercion(tool_loader):
    m = tool_loader("aikit")
    cfg = {}
    m._config_set_nested(cfg, "a.flag", "true")
    m._config_set_nested(cfg, "a.off", "no")
    m._config_set_nested(cfg, "a.n", "null")
    m._config_set_nested(cfg, "a.num", "42")
    m._config_set_nested(cfg, "a.f", "3.5")
    m._config_set_nested(cfg, "a.s", "hello")
    assert cfg["a"] == {"flag": True, "off": False, "n": None, "num": 42, "f": 3.5, "s": "hello"}


def test_aikit_cursor_registry_uses_agent_cli(tool_loader):
    m = tool_loader("aikit")
    cursor = m.AGENTS["cursor"]
    assert cursor["bin"] == "cursor-agent"
    assert "agent" in cursor["bin_aliases"]


def test_aikit_bin_path_belongs_to_cursor(tool_loader):
    m = tool_loader("aikit")
    cursor_bin = "/Users/x/.local/share/cursor-agent/versions/1/cursor-agent"
    grok_bin = "/Users/x/.grok/bin/agent"
    assert m.bin_path_belongs_to_agent("cursor", cursor_bin)
    assert not m.bin_path_belongs_to_agent("cursor", grok_bin)


def test_aikit_bin_path_belongs_to_grok(tool_loader):
    m = tool_loader("aikit")
    grok_bin = "/Users/x/.grok/bin/grok"
    cursor_bin = "/Users/x/.local/bin/cursor-agent"
    assert m.bin_path_belongs_to_agent("grok", grok_bin)
    assert not m.bin_path_belongs_to_agent("grok", cursor_bin)


def test_aikit_agent_bin_collision_warnings(tool_loader, monkeypatch):
    m = tool_loader("aikit")

    def fake_which(name):
        paths = {
            "cursor-agent": "/Users/x/.local/bin/cursor-agent",
            "grok": "/Users/x/.grok/bin/grok",
            "agent": "/Users/x/.grok/bin/agent",
        }
        return paths.get(name)

    monkeypatch.setattr(m.shutil, "which", fake_which)
    warnings = m.agent_bin_collision_warnings()
    assert len(warnings) == 1
    assert "Grok Build" in warnings[0]
    assert "cursor-agent" in warnings[0]


def test_aikit_extract_version(tool_loader):
    m = tool_loader("aikit")
    assert m.extract_version("grok 0.2.67 (03e13f) [stable]") == "0.2.67"
    assert m.extract_version("codex-cli 0.141.0") == "0.141.0"
    assert m.extract_version("2026.06.16-20-30-07-a07d3ac") == "2026.06.16-20-30-07-a07d3ac"


def test_aikit_version_is_older(tool_loader):
    m = tool_loader("aikit")
    assert m.version_is_older("7.2.34", "7.3.54") is True
    assert m.version_is_older("7.3.54", "7.3.54") is False
    assert m.version_is_older("0.141.0", "0.142.3") is True


def test_aikit_resolve_update_cmd_cursor(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "cursor-agent")
    assert m.resolve_update_cmd("cursor") == "cursor-agent update"


def test_aikit_resolve_update_cmd_kimi_reinstall(tool_loader):
    m = tool_loader("aikit")
    cmd = m.resolve_update_cmd("kimi")
    assert cmd and "kimi-code/install.sh" in cmd


def test_aikit_kimi_bin_and_uninstall(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    assert m.AGENTS["kimi"]["bin"] == "kimi"
    kimi_bin = tmp_path / ".kimi-code" / "bin" / "kimi"
    kimi_bin.parent.mkdir(parents=True)
    kimi_bin.write_text("#!/bin/sh\necho 0.20.2\n")
    kimi_bin.chmod(0o755)
    kimi_agent = {**m.AGENTS["kimi"], "install_paths": [str(kimi_bin)]}
    monkeypatch.setitem(m.AGENTS, "kimi", kimi_agent)
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    assert m.detect_agent_bin("kimi")
    uninstall = m.resolve_uninstall_cmd(kimi_agent)
    assert uninstall and ".kimi-code/bin/kimi" in uninstall
    assert ".local/bin/kimi" in uninstall


def test_aikit_curl_installed_agent_uninstall_cmds(tool_loader):
    m = tool_loader("aikit")
    cases = {
        "claude": {
            "paths": [".local/bin/claude", ".claude", ".claude.json"],
            "needs_rf": True,
        },
        "antigravity": {
            "paths": [".local/bin/agy", ".gemini/antigravity-cli"],
            "needs_rf": True,
        },
        "cursor": {
            "paths": [
                ".local/bin/cursor-agent",
                ".local/bin/agent",
                ".local/share/cursor-agent",
                ".cursor/cli-config.json",
            ],
            "needs_rf": True,
            "no_rf_paths": [".cursor"],
        },
        "hermes": {
            "paths": [".local/bin/hermes", ".hermes"],
            "needs_rf": True,
        },
        "codex": {
            "paths": [".local/bin/codex", ".codex"],
            "needs_rf": True,
        },
        "copilot": {
            "paths": [".local/bin/copilot", ".copilot"],
            "needs_rf": True,
        },
        "grok": {
            "paths": [".local/bin/grok", ".local/bin/agent", ".grok"],
            "needs_rf": True,
        },
        "kiro": {
            "paths": [
                ".local/bin/kiro-cli",
                ".local/bin/kiro",
                ".local/bin/kiro-cli-chat",
                ".local/bin/q",
                ".kiro",
            ],
            "needs_rf": True,
        },
        "openclaw": {
            "paths": [".local/bin/openclaw", ".openclaw"],
            "needs_rf": True,
        },
        "devin": {
            "paths": [".local/bin/devin", ".local/share/devin"],
            "needs_rf": True,
        },
        "droid": {
            "paths": [".local/bin/droid", ".factory"],
            "needs_rf": True,
        },
    }
    for key, spec in cases.items():
        cmd = m.resolve_uninstall_cmd(m.AGENTS[key])
        assert cmd and "rm -f" in cmd, key
        for path in spec["paths"]:
            assert path in cmd, f"{key}: missing {path}"
        if spec.get("needs_rf"):
            assert "rm -rf" in cmd, f"{key}: missing vendor dir cleanup"
        for path in spec.get("no_rf_paths", []):
            assert f"rm -rf $HOME/{path}" not in cmd, f"{key}: must not rm -rf {path}"


def test_aikit_resolve_update_cmd_kilo(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "kilo")
    cmd = m.resolve_update_cmd("kilo")
    assert cmd and "npm install -g @kilocode/cli@latest" in cmd
    assert "--prefix" in cmd and ".local" in cmd


def test_aikit_resolve_update_cmd_opencode(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "opencode")
    assert m.resolve_update_cmd("opencode") == "opencode upgrade"


def test_aikit_resolve_update_cmd_pi(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "pi")
    assert m.resolve_update_cmd("pi") == "pi update --self"


def test_aikit_resolve_update_cmd_qwen(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "qwen")
    assert m.resolve_update_cmd("qwen") == "qwen upgrade"


def test_aikit_resolve_update_cmd_blackbox(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "blackbox")
    assert m.resolve_update_cmd("blackbox") == "blackbox update"


def test_aikit_kiro_registry_uses_kiro_cli(tool_loader):
    m = tool_loader("aikit")
    kiro = m.AGENTS["kiro"]
    assert kiro["bin"] == "kiro-cli"
    assert "kiro" in kiro.get("bin_aliases", [])
    assert kiro["version_cmd"] == "kiro-cli --version"


def test_aikit_validate_agent_keys_unknown(tool_loader):
    m = tool_loader("aikit")
    with pytest.raises(m.AikitError, match="cline"):
        m.validate_agent_keys(["goose", "clien"])


def test_aikit_validate_agent_keys_ok(tool_loader):
    m = tool_loader("aikit")
    assert m.validate_agent_keys(["goose", "cline"]) == ["goose", "cline"]
    assert m.validate_agent_keys([]) == []


def test_aikit_new_agent_registry_entries(tool_loader):
    m = tool_loader("aikit")
    assert len(m.AGENTS) == 31
    goose = m.AGENTS["goose"]
    assert goose["bin"] == "goose"
    assert goose["update_cmd"] == "goose update"
    assert "aaif-goose/goose" in goose["install"]["Linux"]
    assert "CONFIGURE=false" in goose["install"]["Linux"]
    assert "CONFIGURE=false" in goose["install"]["Darwin"]
    cline = m.AGENTS["cline"]
    assert cline["bin"] == "cline"
    assert cline["update_cmd"] == "cline update"
    assert cline["version_check"]["package"] == "cline"
    assert "--prefix" in cline["install"]["Linux"]
    assert ".local" in cline["install"]["Linux"]
    openhands = m.AGENTS["openhands"]
    assert openhands["bin"] == "openhands"
    assert openhands.get("update_via_install") is True
    assert "install.openhands.dev" in openhands["install"]["Linux"]
    crush = m.AGENTS["crush"]
    assert crush["bin"] == "crush"
    assert crush["version_check"]["package"] == "@charmland/crush"
    assert "--prefix" in crush["install"]["Darwin"]


def test_aikit_amp_registry_entry(tool_loader):
    m = tool_loader("aikit")
    amp = m.AGENTS["amp"]
    assert amp["bin"] == "amp"
    assert amp["vendor"] == "Sourcegraph"
    assert amp["update_cmd"] == "amp update"
    assert amp["auth_cmd"] == "amp login"
    assert amp["auth_type"] == "oauth_browser"
    assert "AMP_API_KEY" in amp["auth_env_vars"]
    assert amp["version_check"]["package"] == "@ampcode/cli"
    assert "ampcode.com/install.sh" in amp["install"]["Linux"]
    assert "ampcode.com/install.sh" in amp["install"]["Darwin"]
    assert "install.ps1" in amp["install"]["Windows"]


def test_aikit_devin_registry_entry(tool_loader):
    m = tool_loader("aikit")
    devin = m.AGENTS["devin"]
    assert devin["bin"] == "devin"
    assert devin["vendor"] == "Cognition AI"
    assert devin["auth_cmd"] == "devin auth login"
    assert devin["auth_type"] == "oauth_browser"
    assert "WINDSURF_API_KEY" in devin["auth_env_vars"]
    assert devin.get("update_via_install") is True
    assert devin["version_check"]["type"] == "json_url"
    assert "static.devin.ai" in devin["version_check"]["url"]
    assert "cli.devin.ai/install.sh" in devin["install"]["Linux"]
    assert "setup.ps1" in devin["install"]["Windows"]
    assert "Devin subscription" in devin["auth_note"]


def test_aikit_auggie_registry_entry(tool_loader):
    m = tool_loader("aikit")
    auggie = m.AGENTS["auggie"]
    assert auggie["bin"] == "auggie"
    assert auggie["vendor"] == "Augment Code"
    assert auggie["auth_cmd"] == "auggie login"
    assert auggie["auth_type"] == "oauth_browser"
    assert "AUGMENT_SESSION_AUTH" in auggie["auth_env_vars"]
    assert auggie["version_check"]["package"] == "@augmentcode/auggie"


def test_aikit_droid_registry_entry(tool_loader):
    m = tool_loader("aikit")
    droid = m.AGENTS["droid"]
    assert droid["bin"] == "droid"
    assert droid["vendor"] == "Factory AI"
    assert droid["update_cmd"] == "droid update"
    assert droid.get("update_via_install") is None
    assert droid["auth_type"] == "oauth_browser"
    # Factory AI supports headless/BYOK auth via $FACTORY_API_KEY (fk-…); it must be
    # registered so discover_auth's generic env-var check picks it up (POK-76).
    assert "FACTORY_API_KEY" in droid["auth_env_vars"]
    assert droid["install"]["Windows"] is None
    assert "app.factory.ai/cli" in droid["install"]["Linux"]
    assert droid["version_check"]["cmd"] == "droid update --check"
    cov = m.gateway_coverage()
    assert cov["droid"]["state"] == "unsupported"
    assert "proprietary" in cov["droid"]["reason"]


def test_aikit_resolve_update_cmd_amp(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "amp")
    assert m.resolve_update_cmd("amp") == "amp update"


def test_aikit_gateway_cli_registry_entries(tool_loader):
    m = tool_loader("aikit")
    gemini = m.AGENTS["gemini"]
    assert gemini["bin"] == "gemini"
    assert "@google/gemini-cli@latest" in gemini["update_cmd"]
    assert gemini["version_check"]["package"] == "@google/gemini-cli"
    assert "GEMINI_API_KEY" in gemini["auth_env_vars"]
    assert "--prefix" in gemini["install"]["Linux"]
    llm = m.AGENTS["llm"]
    assert llm["bin"] == "llm"
    assert llm["version_check"]["package"] == "llm"
    assert "pip install llm" in llm["install"]["Linux"]
    assert "pip uninstall -y llm" in llm["uninstall_cmd"]
    continue_cli = m.AGENTS["continue"]
    assert continue_cli["bin"] == "cn"
    assert continue_cli["auth_cmd"] == "cn login"
    assert continue_cli["version_check"]["package"] == "@continuedev/cli"
    assert "continuedev/continue" in continue_cli["install"]["Linux"]
    sgpt = m.AGENTS["sgpt"]
    assert sgpt["bin"] == "sgpt"
    assert sgpt["version_check"]["package"] == "shell-gpt"
    assert "OPENAI_API_KEY" in sgpt["auth_env_vars"]
    oi = m.AGENTS["openinterpreter"]
    assert oi["bin"] == "interpreter"
    assert oi["version_check"]["package"] == "open-interpreter"
    assert "OPENAI_API_KEY" in oi["auth_env_vars"]
    assert "pip install open-interpreter" in oi["install"]["Linux"]


def test_aikit_resolve_update_cmd_gemini(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "gemini")
    cmd = m.resolve_update_cmd("gemini")
    assert cmd and "@google/gemini-cli@latest" in cmd


def test_aikit_resolve_update_cmd_continue(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "cn")
    cmd = m.resolve_update_cmd("continue")
    assert cmd and "@continuedev/cli@latest" in cmd


def test_aikit_resolve_agent_bin_npm_global_fallback(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    npm_bin = tmp_path / "npm-bin"
    npm_bin.mkdir()
    cline_link = npm_bin / "cline"
    cline_link.write_text("#!/bin/sh\necho cline\n")
    cline_link.chmod(0o755)
    monkeypatch.setenv("PATH", f"{npm_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setattr(m, "_npm_global_bin_dirs", lambda: [npm_bin])
    monkeypatch.setattr(m.shutil, "which", lambda _name: None)
    resolved = m.resolve_agent_bin("cline")
    assert resolved == str(cline_link)


def test_aikit_npm_global_bin_dirs_skips_off_path_prefixes(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    off_path_bin = tmp_path / "off-path" / "bin"
    on_path_bin = tmp_path / "on-path" / "bin"
    off_path_bin.mkdir(parents=True)
    on_path_bin.mkdir(parents=True)
    monkeypatch.setattr(
        m,
        "_npm_global_prefixes",
        lambda: [tmp_path / "off-path", tmp_path / "on-path"],
    )
    monkeypatch.setenv("PATH", str(on_path_bin))
    dirs = m._npm_global_bin_dirs()
    assert on_path_bin in dirs
    assert off_path_bin not in dirs


def test_aikit_resolve_agent_bin_none_when_not_on_path(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m.shutil, "which", lambda _name: None)
    monkeypatch.setattr(m, "_npm_global_bin_dirs", lambda: [])
    assert m.resolve_agent_bin("cline") is None


def test_aikit_npm_global_prefixes_includes_nvm_from_path(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    nvm_bin = tmp_path / ".nvm" / "versions" / "node" / "v99.0.0" / "bin"
    nvm_bin.mkdir(parents=True)
    monkeypatch.setenv("PATH", f"{nvm_bin}{os.pathsep}")
    prefixes = m._npm_global_prefixes()
    assert (tmp_path / ".nvm" / "versions" / "node" / "v99.0.0") in prefixes


@pytest.mark.skipif(shutil.which("npm") is None, reason="npm not installed")
def test_aikit_npm_global_prefixes_writes_no_home_files(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    m._npm_global_prefixes()
    assert not list(home.rglob("*"))


def test_aikit_npm_uninstall_cmd_targets_all_prefixes(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    local_pkg = tmp_path / "local" / "lib" / "node_modules" / "cline"
    hermes_pkg = tmp_path / "hermes" / "lib" / "node_modules" / "cline"
    local_pkg.mkdir(parents=True)
    hermes_pkg.mkdir(parents=True)
    monkeypatch.setattr(m, "_npm_global_prefixes", lambda: [tmp_path / "local", tmp_path / "hermes"])
    cmd = m.npm_uninstall_cmd("cline")
    assert cmd.count("npm uninstall -g cline") == 2
    assert str(tmp_path / "local") in cmd
    assert str(tmp_path / "hermes") in cmd


def test_aikit_bin_path_belongs_to_cline_resolves_symlink(tool_loader, tmp_path):
    m = tool_loader("aikit")
    pkg_bin = tmp_path / "lib" / "node_modules" / "cline" / "bin" / "cline"
    pkg_bin.parent.mkdir(parents=True)
    pkg_bin.write_text("#!/bin/sh\n")
    pkg_bin.chmod(0o755)
    wrapper = tmp_path / "bin" / "cline"
    wrapper.parent.mkdir()
    wrapper.symlink_to(pkg_bin)
    assert m.bin_path_belongs_to_agent("cline", str(wrapper))


def test_aikit_bin_path_belongs_to_goose_local_bin(tool_loader, tmp_path):
    m = tool_loader("aikit")
    goose_bin = tmp_path / ".local" / "bin" / "goose"
    goose_bin.parent.mkdir(parents=True)
    goose_bin.write_text("#!/bin/sh\necho goose\n")
    goose_bin.chmod(0o755)
    assert m.bin_path_belongs_to_agent("goose", str(goose_bin))


def test_aikit_bin_path_belongs_to_openhands_local_bin(tool_loader, tmp_path):
    m = tool_loader("aikit")
    oh_bin = tmp_path / ".local" / "bin" / "openhands"
    oh_bin.parent.mkdir(parents=True)
    oh_bin.write_text("#!/bin/sh\necho openhands\n")
    oh_bin.chmod(0o755)
    assert m.bin_path_belongs_to_agent("openhands", str(oh_bin))


def test_aikit_bin_path_belongs_to_symlink_wrapper_name(tool_loader, tmp_path):
    m = tool_loader("aikit")
    target = tmp_path / "versions" / "2.1.195"
    target.parent.mkdir(parents=True)
    target.write_text("#!/bin/sh\necho claude\n")
    target.chmod(0o755)
    wrapper = tmp_path / "bin" / "claude"
    wrapper.parent.mkdir()
    wrapper.symlink_to(target)
    assert m.bin_path_belongs_to_agent("claude", str(wrapper))


def test_aikit_agent_collision_still_requires_markers(tool_loader, tmp_path):
    m = tool_loader("aikit")
    agent_bin = tmp_path / "bin" / "agent"
    agent_bin.parent.mkdir(parents=True)
    agent_bin.write_text("#!/bin/sh\necho agent\n")
    agent_bin.chmod(0o755)
    assert not m.bin_path_belongs_to_agent("grok", str(agent_bin))
    assert not m.bin_path_belongs_to_agent("cursor", str(agent_bin))


def test_aikit_uninstall_cmds_for_new_agents(tool_loader):
    m = tool_loader("aikit")
    goose = m.resolve_uninstall_cmd(m.AGENTS["goose"])
    assert goose and "rm -f" in goose and ".local/bin/goose" in goose
    assert "brew uninstall" not in goose


def test_aikit_pip_agent_uninstall_cmds(tool_loader):
    m = tool_loader("aikit")
    cases = [
        ("aider", "aider-chat", "aider"),
        ("llm", "llm", "llm"),
        ("sgpt", "shell-gpt", "sgpt"),
        ("openinterpreter", "open-interpreter", "interpreter"),
    ]
    for key, pip_pkg, bin_name in cases:
        cmd = m.resolve_uninstall_cmd(m.AGENTS[key])
        assert cmd and f"pip uninstall -y {pip_pkg}" in cmd
        assert f"pipx uninstall {pip_pkg}" in cmd
        assert f"uv tool uninstall {pip_pkg}" in cmd
        assert "command -v uv >/dev/null 2>&1" in cmd
        assert "command -v pipx >/dev/null 2>&1" in cmd
        assert f".local/bin/{bin_name}" in cmd


def test_aikit_goose_uninstall_uses_brew_only_for_homebrew_install(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    brew_bin = tmp_path / "opt" / "homebrew" / "bin" / "goose"
    brew_bin.parent.mkdir(parents=True)
    brew_bin.write_text("#!/bin/sh\necho goose\n")
    brew_bin.chmod(0o755)
    monkeypatch.setattr(m.shutil, "which", lambda name: str(brew_bin) if name == "goose" else None)
    cmd = m.goose_uninstall_cmd()
    assert "brew uninstall block-goose-cli" in cmd
    assert "rm -f" in cmd
    openhands = m.resolve_uninstall_cmd(m.AGENTS["openhands"])
    assert openhands and "uv tool uninstall openhands" in openhands
    assert "rm -f" in openhands and ".local/bin/openhands" in openhands
    cline = m.resolve_uninstall_cmd(m.AGENTS["cline"])
    assert cline and "npm uninstall -g cline" in cline
    crush = m.resolve_uninstall_cmd(m.AGENTS["crush"])
    assert crush and "npm uninstall -g @charmland/crush" in crush
    kimi = m.resolve_uninstall_cmd(m.AGENTS["kimi"])
    assert kimi and ".kimi-code/bin/kimi" in kimi


def test_aikit_npm_agent_uninstall_derived_from_version_check(tool_loader):
    # POK-87: npm agents omit explicit uninstall_cmd; npm uninstall is derived.
    m = tool_loader("aikit")
    npm_agents = [
        ("kilo", "@kilocode/cli"),
        ("opencode", "opencode-ai"),
        ("qwen", "@qwen-code/qwen-code"),
        ("qodo", "@qodo/command"),
        ("pi", "@earendil-works/pi-coding-agent"),
        ("blackbox", "@blackboxai/cli"),
        ("cline", "cline"),
        ("crush", "@charmland/crush"),
        ("amp", "@ampcode/cli"),
        ("gemini", "@google/gemini-cli"),
        ("continue", "@continuedev/cli"),
        ("auggie", "@augmentcode/auggie"),
    ]
    for key, package in npm_agents:
        agent = m.AGENTS[key]
        assert "uninstall_cmd" not in agent, key
        cmd = m.resolve_uninstall_cmd(agent)
        assert cmd and f"npm uninstall -g {package}" in cmd, key


def test_aikit_explicit_uninstall_cmd_none_blocks_npm_derivation(tool_loader):
    # POK-87: explicit uninstall_cmd: None means manual-only, even for npm agents.
    m = tool_loader("aikit")
    agent = {
        **m.AGENTS["opencode"],
        "uninstall_cmd": None,
    }
    assert m.resolve_uninstall_cmd(agent) is None


def test_aikit_resolve_update_cmd_openhands_reinstall(tool_loader):
    m = tool_loader("aikit")
    cmd = m.resolve_update_cmd("openhands")
    assert cmd and "install.openhands.dev" in cmd


def test_aikit_resolve_update_cmd_cline(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "resolve_agent_bin", lambda _key: "cline")
    assert m.resolve_update_cmd("cline") == "cline update"


def test_aikit_format_update_status(tool_loader):
    m = tool_loader("aikit")
    assert m.format_update_status("kilo", {"available": True, "latest": "7.3.54"}) == "↑ 7.3.54"
    assert m.format_update_status("kilo", {"available": False, "latest": "7.3.54"}) == "up to date"


def test_aikit_check_update_status_npm(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: True)
    monkeypatch.setattr(m, "detect_agent_version", lambda _key: "7.2.34")
    monkeypatch.setattr(m, "fetch_latest_version", lambda _key: "7.3.54")
    m.UPDATE_CHECK_CACHE.clear()
    status = m.check_update_status("kilo", config={"settings": {"auto_update_check": True}})
    assert status["available"] is True
    assert status["latest"] == "7.3.54"


def test_aikit_check_update_status_reuses_current_raw(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    calls = {"version": 0}

    def _detect(_key):
        calls["version"] += 1
        return "7.2.34"

    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: True)
    monkeypatch.setattr(m, "detect_agent_version", _detect)
    monkeypatch.setattr(m, "fetch_latest_version", lambda _key: "7.3.54")
    m.UPDATE_CHECK_CACHE.clear()
    status = m.check_update_status(
        "kilo",
        current_raw="kilo 7.2.34",
        config={"settings": {"auto_update_check": True}},
    )
    assert calls["version"] == 0
    assert status["available"] is True


def test_aikit_parse_version_stdout_multiline(tool_loader):
    m = tool_loader("aikit")
    stdout = "+------+\n| banner |\n+------+\n\nOpenHands CLI 1.14.0"
    assert m._parse_version_stdout(stdout) == "OpenHands CLI 1.14.0"


def test_aikit_classify_update_outcome_upgraded(tool_loader):
    m = tool_loader("aikit")
    outcome = m.classify_update_outcome(
        "kilo",
        old_version_raw="kilo 7.2.34",
        new_version_raw="kilo 7.3.54",
        exit_code=0,
    )
    assert outcome["status"] == "upgraded"
    assert outcome["old"] == "7.2.34"
    assert outcome["new"] == "7.3.54"


def test_aikit_classify_update_outcome_up_to_date(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(
        m,
        "check_update_status",
        lambda _key, **kwargs: {"available": False, "current": "7.3.54", "latest": "7.3.54"},
    )
    outcome = m.classify_update_outcome(
        "kilo",
        old_version_raw="kilo 7.3.54",
        new_version_raw="kilo 7.3.54",
        exit_code=0,
    )
    assert outcome["status"] == "up_to_date"


def test_aikit_classify_update_outcome_unchanged_outdated(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(
        m,
        "check_update_status",
        lambda _key, **kwargs: {"available": True, "current": "7.2.34", "latest": "7.3.54"},
    )
    outcome = m.classify_update_outcome(
        "kilo",
        old_version_raw="kilo 7.2.34",
        new_version_raw="kilo 7.2.34",
        exit_code=0,
    )
    assert outcome["status"] == "unchanged_outdated"
    assert outcome["latest"] == "7.3.54"


def test_aikit_should_skip_update_when_current(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(
        m,
        "check_update_status",
        lambda _key, **kwargs: {"available": False, "current": "1.0.0", "latest": "1.0.0"},
    )
    skip, check = m.should_skip_update("claude")
    assert skip is True
    assert check["available"] is False


def test_aikit_should_skip_update_force(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(
        m,
        "check_update_status",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("should not check")),
    )
    skip, check = m.should_skip_update("claude", force=True)
    assert skip is False
    assert check is None


def test_aikit_auth_registry_login_commands(tool_loader):
    m = tool_loader("aikit")
    assert m.AGENTS["cursor"]["auth_cmd"] == "agent login"
    assert "CURSOR_API_KEY" in m.AGENTS["cursor"]["auth_env_vars"]
    assert m.AGENTS["codex"]["auth_cmd"] == "codex login"
    assert m.AGENTS["grok"]["auth_cmd"] == "grok login"
    assert m.AGENTS["copilot"]["auth_cmd"] == "copilot login"
    assert m.AGENTS["copilot"]["auth_type"] == "oauth_browser"
    assert "COPILOT_GITHUB_TOKEN" in m.AGENTS["copilot"]["auth_env_vars"]
    assert "opencode auth login" in m.AGENTS["opencode"]["auth_note"]
    assert "BAILIAN_CODING_PLAN_API_KEY" in m.AGENTS["qwen"]["auth_env_vars"]
    assert "MOONSHOT_API_KEY" not in m.AGENTS["kimi"]["auth_env_vars"]
    assert m.AGENTS["kiro"]["auth_cmd"] == "kiro-cli login"
    assert m.AGENTS["devin"]["auth_cmd"] == "devin auth login"


def test_aikit_discover_auth_env_var(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    monkeypatch.setenv("CURSOR_API_KEY", "sk-test-key")
    result = m.discover_auth("cursor")
    assert result["auth_configured"] is True
    assert result["method"] == "env_var"
    assert result["source"] == "$CURSOR_API_KEY"


def test_aikit_discover_auth_opencode_cred_file(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    auth_dir = home / ".local" / "share" / "opencode"
    auth_dir.mkdir(parents=True)
    auth_file = auth_dir / "auth.json"
    auth_file.write_text('{"openai": {"type": "api", "key": "sk-test"}}')
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = m.discover_auth("opencode")
    assert result["auth_configured"] is True
    assert result["method"] == "cred_file"
    assert result["source"] == str(auth_file)


def test_aikit_discover_auth_antigravity_token(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    tok_dir = home / ".gemini" / "antigravity-cli"
    tok_dir.mkdir(parents=True)
    tok_file = tok_dir / "antigravity-oauth-token"
    tok_file.write_text("oauth-token-data")
    monkeypatch.setattr(m, "_REAL_HOME", home)
    result = m.discover_auth("antigravity")
    assert result["auth_configured"] is True
    assert result["method"] == "cred_file"
    assert result["source"] == str(tok_file)


def test_aikit_discover_auth_droid_env_var(tool_loader, monkeypatch):
    # POK-76: Factory AI's headless/BYOK auth ($FACTORY_API_KEY) must count as authed.
    m = tool_loader("aikit")
    monkeypatch.setenv("FACTORY_API_KEY", "fk-test-key")
    result = m.discover_auth("droid")
    assert result["auth_configured"] is True
    assert result["method"] == "env_var"
    assert result["source"] == "$FACTORY_API_KEY"


def test_aikit_discover_auth_droid_cred_file(tool_loader, monkeypatch, tmp_path):
    # POK-76: `droid login` fallback credential file under ~/.factory/ means authed.
    m = tool_loader("aikit")
    home = tmp_path / "home"
    factory_dir = home / ".factory"
    factory_dir.mkdir(parents=True)
    cred_file = factory_dir / "auth.json"
    cred_file.write_text('{"token": "abc"}')
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("FACTORY_API_KEY", raising=False)
    result = m.discover_auth("droid")
    assert result["auth_configured"] is True
    assert result["method"] == "cred_file"
    assert result["source"] == str(cred_file)


def test_aikit_discover_auth_droid_settings_file(tool_loader, monkeypatch, tmp_path):
    # POK-76: keyring-backed OAuth leaves no cred file, but `droid login` writes
    # ~/.factory/settings.json — that is enough to consider droid authenticated.
    m = tool_loader("aikit")
    home = tmp_path / "home"
    factory_dir = home / ".factory"
    factory_dir.mkdir(parents=True)
    settings = factory_dir / "settings.json"
    settings.write_text('{"model": "claude"}')
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("FACTORY_API_KEY", raising=False)
    result = m.discover_auth("droid")
    assert result["auth_configured"] is True
    assert result["method"] == "config_file"
    assert result["source"] == str(settings)


def test_aikit_discover_auth_droid_unauthenticated(tool_loader, monkeypatch, tmp_path):
    # POK-76 guard: an unauthenticated droid (only logs, no creds/settings, no env,
    # no prior aikit-recorded auth) must still report needs-auth — no false positive.
    m = tool_loader("aikit")
    home = tmp_path / "home"
    (home / ".factory" / "logs").mkdir(parents=True)
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("FACTORY_API_KEY", raising=False)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}})
    result = m.discover_auth("droid")
    assert result["auth_configured"] is False


def test_aikit_discover_auth_auggie_env_var(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setenv("AUGMENT_SESSION_AUTH", '{"accessToken":"tok"}')
    result = m.discover_auth("auggie")
    assert result["auth_configured"] is True
    assert result["method"] == "env_var"
    assert result["source"] == "$AUGMENT_SESSION_AUTH"


def test_aikit_discover_auth_auggie_session_file(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    session = home / ".augment" / "session.json"
    session.parent.mkdir(parents=True)
    session.write_text('{"accessToken":"tok","tenantURL":"https://api.example"}')
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("AUGMENT_SESSION_AUTH", raising=False)
    result = m.discover_auth("auggie")
    assert result["auth_configured"] is True
    assert result["method"] == "cred_file"
    assert result["source"] == str(session)


def test_aikit_discover_auth_auggie_unauthenticated(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    (home / ".augment" / "cache").mkdir(parents=True)
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("AUGMENT_SESSION_AUTH", raising=False)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}})
    result = m.discover_auth("auggie")
    assert result["auth_configured"] is False


def test_aikit_discover_auth_devin_env_var(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setenv("WINDSURF_API_KEY", "cog_test_key")
    result = m.discover_auth("devin")
    assert result["auth_configured"] is True
    assert result["method"] == "env_var"
    assert result["source"] == "$WINDSURF_API_KEY"


def test_aikit_discover_auth_devin_cred_file(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    cred_file = home / ".local" / "share" / "devin" / "credentials.json"
    cred_file.parent.mkdir(parents=True)
    cred_file.write_text('{"token":"abc"}')
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("WINDSURF_API_KEY", raising=False)
    result = m.discover_auth("devin")
    assert result["auth_configured"] is True
    assert result["method"] == "cred_file"
    assert result["source"] == str(cred_file)


def test_aikit_discover_auth_devin_unauthenticated(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    (home / ".local" / "share" / "devin" / "cli" / "logs").mkdir(parents=True)
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("WINDSURF_API_KEY", raising=False)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}})
    result = m.discover_auth("devin")
    assert result["auth_configured"] is False


def test_aikit_discover_auth_qodo_env_var(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setenv("QODO_API_KEY", "qodo-test-key")
    result = m.discover_auth("qodo")
    assert result["auth_configured"] is True
    assert result["method"] == "env_var"
    assert result["source"] == "$QODO_API_KEY"


def test_aikit_discover_auth_qodo_auth_key_file(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    auth_key = home / ".qodo" / "auth.key"
    auth_key.parent.mkdir(parents=True)
    auth_key.write_text("qodo-test-key")
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("QODO_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = m.discover_auth("qodo")
    assert result["auth_configured"] is True
    assert result["method"] == "cred_file"
    assert result["source"] == str(auth_key)


def test_aikit_discover_auth_qodo_unauthenticated(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    (home / ".qodo").mkdir(parents=True)
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("QODO_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}})
    result = m.discover_auth("qodo")
    assert result["auth_configured"] is False


def test_aikit_discover_auth_openinterpreter_env_var(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    result = m.discover_auth("openinterpreter")
    assert result["auth_configured"] is True
    assert result["method"] == "env_var"
    assert result["source"] == "$OPENAI_API_KEY"


def test_aikit_discover_auth_openinterpreter_profile_file(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    profile = home / ".config" / "open-interpreter" / "profiles" / "default.yaml"
    profile.parent.mkdir(parents=True)
    profile.write_text("llm:\n  model: gpt-4o\n  api_key: sk-test-key\n")
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = m.discover_auth("openinterpreter")
    assert result["auth_configured"] is True
    assert result["method"] == "config_file"
    assert result["source"] == str(profile)


def test_aikit_discover_auth_openinterpreter_unauthenticated(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    profile = home / ".config" / "open-interpreter" / "profiles" / "default.yaml"
    profile.parent.mkdir(parents=True)
    profile.write_text("llm:\n  model: gpt-4o\n  temperature: 0\n")
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}})
    result = m.discover_auth("openinterpreter")
    assert result["auth_configured"] is False


def test_aikit_discover_auth_plandex_env_var(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    result = m.discover_auth("plandex")
    assert result["auth_configured"] is True
    assert result["method"] == "env_var"
    assert result["source"] == "$OPENROUTER_API_KEY"


def test_aikit_discover_auth_plandex_auth_file(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    auth_file = home / ".plandex-home-v2" / "auth.json"
    auth_file.parent.mkdir(parents=True)
    auth_file.write_text('{"token":"abc","email":"user@example.com"}')
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = m.discover_auth("plandex")
    assert result["auth_configured"] is True
    assert result["method"] == "cred_file"
    assert result["source"] == str(auth_file)


def test_aikit_discover_auth_plandex_unauthenticated(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    (home / ".plandex-v2" / "plans").mkdir(parents=True)
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}})
    result = m.discover_auth("plandex")
    assert result["auth_configured"] is False


def test_aikit_discover_auth_kilo_ignores_opencode_config(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    oc_dir = home / ".config" / "opencode"
    oc_dir.mkdir(parents=True)
    (oc_dir / "opencode.json").write_text('{"provider": "anthropic", "model": "claude-sonnet"}')
    monkeypatch.setattr(m, "_REAL_HOME", home)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {"kilo": {"auth_configured": True}}})
    result = m.discover_auth("kilo")
    assert result["auth_configured"] is False


def test_aikit_discover_auth_kilo_auth_json(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    auth_dir = home / ".local" / "share" / "kilo"
    auth_dir.mkdir(parents=True)
    auth_file = auth_dir / "auth.json"
    auth_file.write_text('{"anthropic": {"type": "api", "key": "sk-test"}}')
    monkeypatch.setattr(m, "_REAL_HOME", home)
    result = m.discover_auth("kilo")
    assert result["auth_configured"] is True
    assert result["method"] == "cred_file"
    assert result["source"] == str(auth_file)


def test_aikit_read_key_enter_accepts_carriage_return(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(m.readchar, "readkey", lambda: "\r")
    assert m._read_key() == "enter"


def test_aikit_auth_picker_single_select_on_enter(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    installed = {"claude", "codex", "cursor"}

    def fake_detect(key):
        return key in installed

    keys = iter(["enter"])

    monkeypatch.setattr(m, "detect_agent_bin", fake_detect)
    monkeypatch.setattr(m, "_read_key", lambda: next(keys))
    monkeypatch.setattr(m.sys.stdin, "isatty", lambda: True)

    result = m.interactive_agent_picker(
        "Select agent to authenticate",
        single=True,
        only_installed=True,
    )
    assert result == ["claude"]


def test_aikit_auth_picker_only_installed(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    monkeypatch.setattr(m, "detect_agent_bin", lambda key: key == "codex")
    monkeypatch.setattr(m, "_read_key", lambda: "enter")
    monkeypatch.setattr(m.sys.stdin, "isatty", lambda: True)

    result = m.interactive_agent_picker(
        "Select agent to authenticate",
        single=True,
        only_installed=True,
    )
    assert result == ["codex"]


def test_aikit_uninstall_prompts_before_vendor_data_removal(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    prompts = []
    runs = []

    monkeypatch.setattr(m, "_prompt_yes_no", lambda msg, default: prompts.append(msg) or False)
    monkeypatch.setattr(m, "validate_agent_keys", lambda keys: None)
    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: True)
    monkeypatch.setattr(m, "run", lambda *args, **kwargs: runs.append(args) or (0, "", ""))
    monkeypatch.setattr(m, "discover_and_persist", lambda: None)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}, "settings": {}})
    monkeypatch.setattr(m, "save_config", lambda _cfg: None)

    m._do_uninstall_impl(["claude"], yes=False)

    assert prompts
    assert "vendor config/data" in prompts[0]
    assert not runs


def test_aikit_uninstall_skips_vendor_prompt_with_yes(tool_loader, monkeypatch):
    m = tool_loader("aikit")
    prompts = []
    runs = []

    monkeypatch.setattr(m, "_prompt_yes_no", lambda msg, default: prompts.append(msg) or False)
    monkeypatch.setattr(m, "validate_agent_keys", lambda keys: None)
    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: True)
    monkeypatch.setattr(m, "run", lambda *args, **kwargs: runs.append(args) or (0, "", ""))
    monkeypatch.setattr(m, "discover_and_persist", lambda: None)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}, "settings": {}})
    monkeypatch.setattr(m, "save_config", lambda _cfg: None)

    m._do_uninstall_impl(["claude"], yes=True)

    assert not prompts
    assert runs


def test_aikit_uninstall_prunes_config_entry(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    cfg_dir = tmp_path / ".aikit"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.json"
    cfg_file.write_text(
        json.dumps(
            {
                "version": 1,
                "agents": {
                    "kilo": {
                        "installed": True,
                        "auth_configured": True,
                        "install_date": "2026-01-01",
                    }
                },
                "settings": {},
            }
        )
    )
    monkeypatch.setattr(m, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(m, "CONFIG_FILE", cfg_file)
    monkeypatch.setattr(m, "validate_agent_keys", lambda keys: None)
    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: False)
    monkeypatch.setattr(m, "resolve_uninstall_cmd", lambda _agent: "true")
    monkeypatch.setattr(m, "run", lambda *_a, **_k: (0, "", ""))
    monkeypatch.setattr(m, "discover_and_persist", lambda: None)

    m._do_uninstall_impl(["kilo"], yes=True)

    saved = json.loads(cfg_file.read_text())
    assert "kilo" not in saved.get("agents", {})


def test_aikit_auth_signals_failure_when_agent_not_installed(tool_loader, monkeypatch):
    # POK-90: auth for a known-but-not-installed agent must raise AikitError so
    # `aikit auth` exits non-zero (previously it printed an error and returned 0).
    m = tool_loader("aikit")

    monkeypatch.setattr(m, "validate_agent_keys", lambda keys: keys)
    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: False)

    with pytest.raises(m.AikitError, match="not installed"):
        m._do_auth_impl("aider")


def test_aikit_uninstall_signals_failure_when_no_uninstall_command(tool_loader, monkeypatch):
    # POK-82: an installed agent with no automated uninstall command must make
    # `aikit uninstall` exit non-zero (previously it exited 0 and misled callers).
    m = tool_loader("aikit")

    monkeypatch.setattr(m, "validate_agent_keys", lambda keys: None)
    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: True)
    monkeypatch.setattr(m, "resolve_uninstall_cmd", lambda _agent: None)
    monkeypatch.setattr(m, "discover_and_persist", lambda: None)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}, "settings": {}})
    monkeypatch.setattr(m, "save_config", lambda _cfg: None)

    rc = m._do_uninstall_impl(["claude"], yes=True)

    assert rc == 1


def test_aikit_uninstall_signals_success_when_uninstall_command_runs(tool_loader, monkeypatch):
    # Installed agent WITH an automated uninstall command keeps exit 0.
    m = tool_loader("aikit")

    monkeypatch.setattr(m, "validate_agent_keys", lambda keys: None)
    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: True)
    monkeypatch.setattr(m, "resolve_uninstall_cmd", lambda _agent: "true")
    monkeypatch.setattr(m, "run", lambda *_a, **_k: (0, "", ""))
    monkeypatch.setattr(m, "discover_and_persist", lambda: None)
    monkeypatch.setattr(m, "load_config", lambda: {"agents": {}, "settings": {}})
    monkeypatch.setattr(m, "save_config", lambda _cfg: None)

    rc = m._do_uninstall_impl(["claude"], yes=True)

    assert rc == 0


def test_aikit_discover_prunes_uninstalled_agents(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    cfg_dir = tmp_path / ".aikit"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.json"
    cfg_file.write_text(
        json.dumps(
            {
                "version": 1,
                "agents": {
                    "kilo": {
                        "installed": True,
                        "auth_configured": True,
                        "install_date": "2026-01-01",
                    }
                },
                "settings": {},
            }
        )
    )
    monkeypatch.setattr(m, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(m, "CONFIG_FILE", cfg_file)
    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: False)
    monkeypatch.setattr(m, "discover_auth", lambda _key: {"auth_configured": True, "method": "cred_file", "source": "/tmp/auth.json"})
    monkeypatch.setattr(m, "check_update_status", lambda *_a, **_k: {})
    monkeypatch.setattr(m, "detect_agent_version", lambda _key: None)

    m.discover_and_persist()

    saved = json.loads(cfg_file.read_text())
    assert "kilo" not in saved.get("agents", {})


def test_aikit_discover_does_not_add_never_installed_agents(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    cfg_dir = tmp_path / ".aikit"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.json"
    cfg_file.write_text(json.dumps({"version": 1, "agents": {}, "settings": {}}))
    monkeypatch.setattr(m, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(m, "CONFIG_FILE", cfg_file)
    monkeypatch.setattr(m, "detect_agent_bin", lambda _key: False)
    monkeypatch.setattr(m, "discover_auth", lambda _key: {"auth_configured": False, "method": "", "source": ""})
    monkeypatch.setattr(m, "check_update_status", lambda *_a, **_k: {})
    monkeypatch.setattr(m, "detect_agent_version", lambda _key: None)

    m.discover_and_persist()

    saved = json.loads(cfg_file.read_text())
    assert saved.get("agents") == {}


# --- aikit gateway ---------------------------------------------------------
def test_aikit_gateway_registry_table_driven(tool_loader):
    m = tool_loader("aikit")
    ids = [p[0] for p in m.GATEWAY_PROVIDERS]
    assert len(ids) == 65 and len(ids) == len(set(ids))
    routes = {p[0]: p[5] for p in m.GATEWAY_PROVIDERS}
    assert routes["anthropic"] == "/anthropic"   # native pass-through
    assert routes["openai"] == "/v1"             # OpenAI-compatible endpoint


def test_aikit_gateway_env_pairs_universal_and_safe(tool_loader):
    m = tool_loader("aikit")
    d = dict(m.build_env_pairs("https://gw.example.com/", "sk-x"))
    assert d["OPENAI_BASE_URL"] == "https://gw.example.com/v1"
    assert d["ANTHROPIC_BASE_URL"] == "https://gw.example.com/anthropic"
    # general-purpose credentials are never set (safety invariant)
    assert "AWS_ACCESS_KEY_ID" not in d and "GITHUB_TOKEN" not in d


def test_aikit_gateway_help_runs():
    """`aikit gateway --help` exits 0 and lists the subcommands."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "aikit"), "gateway", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    for sub in ("on", "off", "status", "models"):
        assert sub in proc.stdout


# --- medcat ----------------------------------------------------------------
def test_medcat_format_structure(tool_loader):
    m = tool_loader("medcat")
    out = m.format_structure("{Author}/{Title}", {"Author": "Ann", "Title": "Book"})
    assert out == "Ann/Book"


def test_medcat_format_structure_numeric_spec(tool_loader):
    m = tool_loader("medcat")
    out = m.format_structure("Vol{Volume:02d}", {"Volume": 3})
    assert out == "Vol03"


def test_medcat_config_nested(tool_loader):
    m = tool_loader("medcat")
    cfg = {}
    m._config_set_nested(cfg, "services.kavita.url", "http://x")
    assert m._config_get_nested(cfg, "services.kavita.url") == "http://x"


class _FakeArchiveResp:
    """Minimal stand-in for the Internet Archive advancedsearch.php response."""

    status_code = 200

    @staticmethod
    def json():
        return {"response": {"docs": [
            {"identifier": "abc", "title": "A Book", "creator": "Ann", "date": "1999"},
        ]}}


class _SearchArgs:
    """Namespace mimicking argparse for cmd_search (archive-only, no ingest)."""

    query = "q"
    type = "books"
    source = "archive"
    limit = 5
    list_only = False
    no_ingest = True
    audio = False
    dest = None


def test_medcat_archive_search_source_is_dispatchable(tool_loader, monkeypatch):
    """Archive results must carry a source key SEARCH_SOURCES can dispatch.

    Regression: results were tagged ``"archive.org"`` while the dispatch table
    keys on ``"archive"``, so every selection silently no-op'd.
    """
    m = tool_loader("medcat")
    monkeypatch.setattr(m.requests, "get", lambda *a, **k: _FakeArchiveResp())
    results = m._archive_search("query", "books", 5)
    assert results, "archive search returned no results"
    assert results[0].source == "archive"
    assert results[0].source in m.SEARCH_SOURCES


def test_medcat_search_selection_dispatches_download(tool_loader, monkeypatch):
    """Picking a result actually triggers its source's download handler."""
    m = tool_loader("medcat")
    monkeypatch.setattr(m.requests, "get", lambda *a, **k: _FakeArchiveResp())
    monkeypatch.setattr(m, "load_config", lambda: {"services": {}, "destinations": {}})
    monkeypatch.setattr(m.sys.stdin, "isatty", lambda: True)

    downloaded = []
    monkeypatch.setattr(
        m, "_archive_download",
        lambda r, dest_dir=None: (downloaded.append(r), True)[1],
    )

    answers = iter(["1"])  # pick #1; _prompt_yes_no=False ends the loop after

    def fake_input(*a, **k):
        try:
            return next(answers)
        except StopIteration:  # safety net — shouldn't be reached
            raise EOFError

    monkeypatch.setattr(m.console, "input", fake_input)
    monkeypatch.setattr(m, "_prompt_yes_no", lambda *a, **k: False)

    m.cmd_search(_SearchArgs())
    assert len(downloaded) == 1, "selection did not dispatch an archive download"


def test_medcat_search_menu_eof_quits_cleanly(tool_loader, monkeypatch):
    """Ctrl-D / closed stdin at the menu exits cleanly, no EOFError traceback."""
    m = tool_loader("medcat")
    monkeypatch.setattr(m, "load_config", lambda: {"services": {}, "destinations": {}})
    monkeypatch.setattr(
        m, "_archive_search",
        lambda q, mt=None, lim=20: [m.SearchResult(title="X", source="archive", media_type="books")],
    )
    monkeypatch.setattr(m.sys.stdin, "isatty", lambda: True)

    def eof(*a, **k):
        raise EOFError

    monkeypatch.setattr(m.console, "input", eof)
    assert m.cmd_search(_SearchArgs()) is None


def test_medcat_search_menu_ctrl_c_propagates(tool_loader, monkeypatch):
    """KeyboardInterrupt is left for sk.run_cli (the one termination point),
    not swallowed in the tool — per AGENTS.md."""
    m = tool_loader("medcat")
    monkeypatch.setattr(m, "load_config", lambda: {"services": {}, "destinations": {}})
    monkeypatch.setattr(
        m, "_archive_search",
        lambda q, mt=None, lim=20: [m.SearchResult(title="X", source="archive", media_type="books")],
    )
    monkeypatch.setattr(m.sys.stdin, "isatty", lambda: True)

    def boom(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(m.console, "input", boom)
    with pytest.raises(KeyboardInterrupt):
        m.cmd_search(_SearchArgs())


# --- voxtract --------------------------------------------------------------
def test_voxtract_parse_time(tool_loader):
    m = tool_loader("voxtract")
    assert m.parse_time("90") == 90.0
    assert m.parse_time("1:30") == 90.0
    assert m.parse_time("1:01:01") == 3661.0


def test_voxtract_format_time(tool_loader):
    m = tool_loader("voxtract")
    assert m.format_time(90) == "1:30.00"
    assert m.format_time(3661) == "1:01:01.00"


def test_voxtract_cache_id_stable(tool_loader):
    m = tool_loader("voxtract")
    a = m.cache_id("youtube://abc")
    assert a == m.cache_id("youtube://abc")
    assert len(a) == 16
    assert a != m.cache_id("youtube://xyz")


def test_voxtract_human_size(tool_loader):
    m = tool_loader("voxtract")
    assert m.human_size(1536) == "1.5 KB"


# --- scripts ---------------------------------------------------------------
def test_scripts_validate_tools(tool_loader):
    m = tool_loader("scripts")
    assert m.validate_tools(["medcat", "pluck"]) == ["medcat", "pluck"]
    with pytest.raises(SystemExit):
        m.validate_tools(["nope"])


def test_scripts_path_export_line(tool_loader):
    m = tool_loader("scripts")
    line = m.path_export_line(Path("/some/bin"))
    assert "/some/bin" in line
