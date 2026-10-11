"""V1 routing and bare-Python dry-run remain usable through migration."""
import json
import locale
import os
from types import SimpleNamespace

import pytest
import subprocess
import sys
import venv
from pathlib import Path

from test_manager_migration import installation, snapshot
from pokanop_manager import lifecycle as life


@pytest.mark.parametrize("historical", [False, True])
def test_v1_migration_and_rollback_preserve_old_environment(installation, tool_loader, historical):
    root, bin_dir = installation
    (root / "pluck").write_text('print("legacy")\n')
    venv.EnvBuilder(with_pip=False).create(root / "venv")
    sentinel = root / "venv/sentinel"
    sentinel.write_text("keep")
    old = {"version": 1, "tools": ["pluck", "netsy"], "install_dir": str(root), "bin_dir": str(bin_dir)}
    (root / life.MARKER).write_text(json.dumps(old))
    host = tool_loader("scripts")
    wrapper = lambda name: host.wrapper_content(name, root, bin_dir)
    path = life.destination(bin_dir, "pluck")
    host.install_wrappers(root, bin_dir, ["pluck"])
    encoding = "utf-8" if sys.flags.utf8_mode else locale.getencoding()
    assert path.read_bytes() == wrapper("pluck").encode(encoding)
    if historical:
        # Reproduce the old writer, including Windows' encoding and translation.
        path.write_text(wrapper("pluck"), encoding=locale.getencoding(), newline=os.linesep)
    other = life.destination(bin_dir, "netsy")
    other.write_bytes(b"unrelated")
    life.install(root, bin_dir, ["pluck"], legacy_wrapper=wrapper, prepare_tool=snapshot)
    assert subprocess.check_output([str(path)], text=True).strip() == "working"
    assert life.marker(root)["tools"] == ["netsy", "pluck"]
    life.rollback(root, bin_dir)
    assert subprocess.check_output([str(path)], text=True).strip() == "legacy"
    assert life.marker(root) == old
    assert sentinel.read_text() == "keep"
    assert other.read_bytes() == b"unrelated"


@pytest.mark.parametrize("historical", [False, True])
@pytest.mark.parametrize("edited", [False, True])
def test_legacy_uninstall_ownership(installation, tool_loader, historical, edited):
    root, bin_dir = installation
    host = tool_loader("scripts")
    wrapper = lambda name: host.wrapper_content(name, root, bin_dir)
    (root / life.MARKER).write_text(json.dumps({"version": 1, "tools": ["pluck"]}))
    host.install_wrappers(root, bin_dir, ["pluck"])
    path = life.destination(bin_dir, "pluck")
    if historical:
        path.write_text(wrapper("pluck"), encoding=locale.getencoding(), newline=os.linesep)
    if edited:
        path.write_bytes(path.read_bytes() + b"rem edited\r\n")
        before = path.read_bytes()
        with pytest.raises(ValueError, match="refusing foreign wrapper"):
            life.uninstall(root, bin_dir, ["pluck"], legacy_wrapper=wrapper)
        assert path.read_bytes() == before
        assert life.marker(root)["tools"] == ["pluck"]
    else:
        life.uninstall(root, bin_dir, ["pluck"], legacy_wrapper=wrapper)
        assert not path.exists()
        assert life.marker(root)["tools"] == []


@pytest.mark.parametrize("platform", ["nt", "posix"])
@pytest.mark.parametrize("encoding,username", [("utf-8", "José"), ("cp1252", "José"),
                                               ("cp932", "田中")])
def test_historical_windows_bytes_are_exact_and_platform_scoped(tmp_path, monkeypatch, platform,
                                                               encoding, username):
    content = f'@echo off\r\n"C:\\Users\\{username}\\python" "pluck" %*\r\n'
    path = tmp_path / "pluck.cmd"
    path.write_text(content, encoding=encoding, newline="\r\n")
    historical = path.read_bytes()
    assert historical == content.replace("\r\n", "\r\r\n").encode(encoding)
    monkeypatch.setattr(life, "os", SimpleNamespace(name=platform))
    monkeypatch.setattr(life.locale, "getencoding", lambda: encoding)
    allowed = life.legacy_wrapper_bytes(content)
    assert content.encode() in allowed
    assert (historical in allowed) == (platform == "nt")
    assert (content.encode(encoding) in allowed) == (platform == "nt" or encoding == "utf-8")
    assert historical + b"rem edited\r\n" not in allowed
    assert content.replace("\r\n", "\n").encode(encoding) not in allowed


def test_utf8_wrapper_outside_locale_encoding(monkeypatch):
    monkeypatch.setattr(life, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(life.locale, "getencoding", lambda: "cp1252")
    content = '@echo off\r\n"C:\\Users\\田中\\python" "pluck" %*\r\n'
    assert life.legacy_wrapper_bytes(content) == [content.encode(),
                                                content.replace("\n", "\r\n").encode()]


def test_bare_dry_run_creates_nothing(installation):
    root, bin_dir = installation
    before = sorted(str(p) for p in root.rglob("*"))
    script = Path(__file__).resolve().parents[1] / "scripts"
    result = subprocess.run([sys.executable, "-S", str(script), "migrate", "pluck", "--dry-run",
                             "--dir", str(root), "--bin-dir", str(bin_dir)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "requested_dependencies" in result.stdout
    assert before == sorted(str(p) for p in root.rglob("*"))
