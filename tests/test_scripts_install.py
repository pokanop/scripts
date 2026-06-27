"""Regression tests for `scripts install` auto-pull behavior."""

import argparse


def _install_args(tmp_path, **overrides):
    args = dict(
        dir=str(tmp_path), bin_dir=str(tmp_path / "bin"),
        tools=[], upgrade=False, no_path=True, no_pull=False,
    )
    args.update(overrides)
    return argparse.Namespace(**args)


def _patch_heavy(m, monkeypatch, calls):
    """Stub out everything cmd_install does except the git_pull decision."""
    monkeypatch.setattr(m, "git_pull", lambda p: calls.append(p))
    monkeypatch.setattr(m, "ensure_venv", lambda p: None)
    monkeypatch.setattr(m, "pip_install_base", lambda p, upgrade=False: None)
    monkeypatch.setattr(m, "pip_install_requirements", lambda p, t, upgrade=False: None)
    monkeypatch.setattr(m, "install_wrappers", lambda *a, **k: None)
    monkeypatch.setattr(m, "write_marker", lambda *a, **k: None)
    monkeypatch.setattr(m, "read_marker", lambda p=None: None)


def test_install_has_no_pull_flag(tool_loader):
    m = tool_loader("scripts")
    ns = m.build_parser().parse_args(["install", "--no-pull"])
    assert ns.no_pull is True
    ns2 = m.build_parser().parse_args(["install"])
    assert ns2.no_pull is False


def test_install_pulls_for_git_clone(tool_loader, tmp_path, monkeypatch):
    m = tool_loader("scripts")
    (tmp_path / "requirements").mkdir()
    calls = []
    _patch_heavy(m, monkeypatch, calls)
    monkeypatch.setattr(m, "is_git_clone", lambda p: True)
    m.cmd_install(_install_args(tmp_path))
    assert calls, "git_pull should run when the install dir is a git clone"


def test_install_no_pull_skips(tool_loader, tmp_path, monkeypatch):
    m = tool_loader("scripts")
    (tmp_path / "requirements").mkdir()
    calls = []
    _patch_heavy(m, monkeypatch, calls)
    monkeypatch.setattr(m, "is_git_clone", lambda p: True)
    m.cmd_install(_install_args(tmp_path, no_pull=True))
    assert not calls, "--no-pull should skip git_pull"


def test_install_non_git_does_not_pull(tool_loader, tmp_path, monkeypatch):
    m = tool_loader("scripts")
    (tmp_path / "requirements").mkdir()
    calls = []
    _patch_heavy(m, monkeypatch, calls)
    monkeypatch.setattr(m, "is_git_clone", lambda p: False)
    m.cmd_install(_install_args(tmp_path))
    assert not calls, "a non-git install dir has nothing to pull"
