"""Review regressions: full managed uninstall and transactional registration."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pokanop_manager import lifecycle as life
from pokanop_manager.catalog import load
from test_manager_migration import installation, snapshot, setup_root


@pytest.mark.parametrize("keep_dir,keep_path,clone", [(False, False, False), (True, True, False), (False, False, True)])
def test_full_v2_uninstall(installation, tool_loader, monkeypatch, keep_dir, keep_path, clone):
    root, bin_dir = installation
    setup_root(root)
    life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=snapshot)
    host = tool_loader("scripts")
    host_path = life.destination(bin_dir, "scripts")
    host_path.write_text("host")
    user_config = root.parent / "user-config"
    user_config.write_text("keep")
    for name in ("venv", ".scripts-harness"):
        (root / name).mkdir()
        (root / name / "data").write_text("old")
    calls = []
    monkeypatch.setattr(host, "default_install_dir", lambda: root)
    monkeypatch.setattr(host, "is_git_clone", lambda _: clone)
    monkeypatch.setattr(host, "remove_path_from_shell", lambda _: calls.append("path"))
    args = argparse.Namespace(dir=str(root), bin_dir=str(bin_dir), tools=[], yes=True,
                              keep_dir=keep_dir, keep_path=keep_path)
    host.cmd_uninstall(args)
    assert not life.destination(bin_dir, "pluck").exists()
    assert not host_path.exists()
    assert not (root / life.MARKER).exists()
    assert not (root / ".scripts-state").exists()
    assert not (root / ".scripts-harness").exists()
    assert not (root / "venv").exists()
    assert root.exists() == (keep_dir or clone)
    assert calls == ([] if keep_path else ["path"])
    assert user_config.read_text() == "keep"


def test_locked_uninstall_data_prints_cleanup(installation, tool_loader, monkeypatch, capsys):
    root, bin_dir = installation
    setup_root(root)
    life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=snapshot)
    host = tool_loader("scripts")
    def locked(*args, **kwargs):
        raise PermissionError("busy")
    monkeypatch.setattr(host.shutil, "rmtree", locked)
    host.cmd_uninstall(argparse.Namespace(dir=str(root), bin_dir=str(bin_dir), tools=[],
                                         yes=True, keep_dir=True, keep_path=True))
    output = capsys.readouterr().out
    assert "Retained (close running tools, then delete)" in output
    assert "Remove-Item -LiteralPath" in output or "rm -rf --" in output
    assert not (root / life.MARKER).exists()


def test_reserved_registration_does_not_publish(installation, tool_loader):
    from scriptkit.contracts import resource_text
    root, _ = installation
    host = tool_loader("scripts")
    project = root / "project"
    project.mkdir()
    spec = json.loads(resource_text("ToolSpec.example.json"))
    spec["name"] = "scripts"
    (project / "tool.json").write_text(json.dumps(spec))
    overlay = root / ".scripts-catalog.json"
    overlay.write_text('{}')
    before = overlay.read_bytes()
    with pytest.raises(ValueError, match="invalid catalog tool name"):
        host.cmd_register(argparse.Namespace(dir=str(root), project=str(project)))
    assert overlay.read_bytes() == before
    assert "pluck" in load(root)


@pytest.mark.parametrize("overlay", [{"scripts": {}}, [], {"bad": None}])
def test_invalid_overlay_is_cli_error_not_traceback(tmp_path, overlay):
    (tmp_path / ".scripts-catalog.json").write_text(json.dumps(overlay))
    script = Path(__file__).resolve().parents[1] / "scripts"
    result = subprocess.run([sys.executable, str(script), "doctor", "--dir", str(tmp_path)],
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert "scripts:" in result.stderr
    assert "Traceback" not in result.stderr


def test_uninstall_invalidates_stale_rollback(installation):
    root, bin_dir = installation
    setup_root(root)
    for _ in range(2):
        life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=snapshot)
    life.uninstall(root, bin_dir, ["pluck"])
    with pytest.raises(ValueError, match="no previous migration snapshot"):
        life.rollback(root, bin_dir)
    assert life.marker(root)["tools"] == []
