"""Characterization tests for the CLI tools.

These pin observable behavior (pure helpers + parser/--help) so the scriptkit
refactor is provably non-breaking: every assertion here passes before and
after the tools are rewired onto the shared library.
"""

import os
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
    assert len(m.AGENTS) == 20
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
    status = m.check_update_status("kilo", force=True, config={"settings": {"auto_update_check": True}})
    assert status["available"] is True
    assert status["latest"] == "7.3.54"


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
