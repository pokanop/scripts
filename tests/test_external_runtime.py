"""Consumer compatibility and bootstrap migration regressions."""
import subprocess
import sys
import tomllib
from importlib.metadata import distribution, version
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def test_external_ownership_and_pin():
    import scripteer

    assert not (ROOT / "scripteer" / "__init__.py").exists()
    assert not Path(scripteer.__file__).resolve().is_relative_to(ROOT / "scripteer")
    assert version("scripteer") == "2.0.0"
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    requirements = [Requirement(r) for r in metadata["project"]["dependencies"]]
    runtime = [r for r in requirements if r.name == "scripteer"]
    assert len(runtime) == 1 and runtime[0].url is None
    assert str(runtime[0]) == "scripteer==2.0.0"
    for path in ("runtime-constraints.txt", "base.txt"):
        assert str(runtime[0]) in (ROOT / "requirements" / path).read_text()
    assert metadata["tool"]["setuptools"]["packages"] == ["pokanop_manager"]
    files = distribution("scripteer").files
    assert any(str(f) == "scripteer/__init__.py" for f in files)


def test_published_manager_does_not_rebootstrap(tool_loader, monkeypatch, tmp_path):
    host = tool_loader("scripts")
    def unexpected(*args, **kwargs):
        pytest.fail("published runtime should not trigger harness repair")
    monkeypatch.setattr(host.subprocess, "run", unexpected)
    args = SimpleNamespace(command="install", dry_run=False, dir=str(tmp_path))
    assert host.ensure_manager(args) is None


@pytest.mark.parametrize("tool", [
    "scripts", "aikit", "keyferry", "medcat", "netsy", "pluck", "templates/tool_template.py",
    pytest.param("voxtract", marks=pytest.mark.skipif(
        sys.platform == "win32", reason="Existing voxtract POSIX-only fcntl import")),
])
def test_outside_cwd_help(tool, tmp_path):
    # Isolated mode ignores PYTHONUTF8; explicitly select the UTF-8 stream used
    # by the tools' existing emoji banners rather than Windows pipe cp1252.
    result = subprocess.run([sys.executable, "-I", "-X", "utf8", str(ROOT / tool), "--help"],
                            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


@pytest.mark.parametrize("owner", ["legacy", "external", "absent"])
def test_legacy_uninstalled_before_forced_runtime_repair(tool_loader, monkeypatch, tmp_path, owner):
    host = tool_loader("scripts")
    req = tmp_path / "requirements"
    req.mkdir()
    (req / "base.txt").write_text("scripteer==2.0.0\n")
    calls = []
    monkeypatch.setattr(host, "ensure_venv", lambda _: None)
    system = host.platform.system()
    monkeypatch.setattr(host.platform, "system", lambda: system)
    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(stdout=owner + "\n")
    monkeypatch.setattr(host.subprocess, "run", run)
    host.pip_install_base(tmp_path)
    assert "-I" in calls[0]
    assert any("uninstall" in cmd for cmd in calls) == (owner == "legacy")
    assert calls[-2][-2:] == ["-r", str(req / "base.txt")]
    assert "--force-reinstall" not in calls[-2]
    assert "--upgrade" not in calls[-2]
    assert calls[-1][-5:] == ["install", "--force-reinstall", "--no-deps", "-r", str(req / "runtime-constraints.txt")]


@pytest.mark.parametrize("failure", [subprocess.CalledProcessError(1, "pip"), KeyboardInterrupt()])
def test_install_failure_does_not_rewrite_wrappers_or_marker(tool_loader, monkeypatch, tmp_path, failure):
    import argparse
    host = tool_loader("scripts")
    (tmp_path / "requirements").mkdir()
    marker = tmp_path / host.MARKER_NAME
    marker.write_text('{"tools": []}')
    wrapper = tmp_path / "bin" / "scripts"
    wrapper.parent.mkdir()
    wrapper.write_text("original wrapper")
    monkeypatch.setattr(host, "ensure_venv", lambda _: None)
    def fail(*a, **kw):
        raise failure
    monkeypatch.setattr(host, "pip_install_base", fail)
    args = argparse.Namespace(dir=str(tmp_path), bin_dir=str(wrapper.parent),
                              tools=[], upgrade=False, no_path=True, no_pull=True)
    with pytest.raises(type(failure)):
        host.cmd_install(args)
    assert marker.read_text() == '{"tools": []}'
    assert wrapper.read_text() == "original wrapper"


def test_namespace_cache_uses_bare_python_fallback(tmp_path):
    import shutil
    shutil.copyfile(ROOT / "scripts", tmp_path / "scripts")
    shutil.copytree(ROOT / "pokanop_manager", tmp_path / "pokanop_manager")
    (tmp_path / "scriptkit" / "__pycache__").mkdir(parents=True)
    result = subprocess.run([sys.executable, "-S", "-X", "utf8", str(tmp_path / "scripts"), "--help"],
                            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


@pytest.mark.parametrize("extra", [None, "__init__.py", "notes.txt", "__pycache__/notes.txt"])
def test_prune_only_orphaned_bytecode(tool_loader, tmp_path, extra):
    host = tool_loader("scripts")
    runtime = tmp_path / "scriptkit"
    cache = runtime / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "app.cpython-311.pyc").write_bytes(b"old bytecode")
    if extra:
        (runtime / extra).write_text("preserve")
    host.prune_legacy_runtime_cache(tmp_path)
    assert runtime.exists() == bool(extra)
    if extra:
        assert (runtime / extra).read_text() == "preserve"
