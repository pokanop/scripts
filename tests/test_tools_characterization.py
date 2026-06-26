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
