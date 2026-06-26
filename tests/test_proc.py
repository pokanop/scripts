"""Tests for scriptkit.proc — subprocess wrapper with graceful failures."""

import subprocess
import sys

import pytest

import scriptkit.proc as proc
from scriptkit.cli import CliError


def test_run_success():
    res = proc.run([sys.executable, "-c", "print('hi')"])
    assert res.ok and bool(res) is True
    assert res.code == 0
    assert res.out == "hi"


def test_run_nonzero_no_raise():
    res = proc.run([sys.executable, "-c", "import sys; sys.stderr.write('bad'); sys.exit(3)"])
    assert res.code == 3
    assert res.ok is False
    assert bool(res) is False
    assert res.err == "bad"


def test_run_missing_binary():
    res = proc.run(["definitely-not-a-real-binary-xyz"])
    assert res.code == -127
    assert "command not found" in res.err


def test_run_timeout(monkeypatch):
    def fake(*a, **k):
        raise subprocess.TimeoutExpired(cmd="x", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake)
    res = proc.run(["sleep", "10"], timeout=1)
    assert res.code == -1
    assert "timed out" in res.err


def test_run_check_raises():
    with pytest.raises(CliError) as exc:
        proc.run([sys.executable, "-c", "import sys; sys.exit(1)"], check=True)
    assert "command failed" in str(exc.value)


def test_run_input_passed():
    res = proc.run([sys.executable, "-c", "import sys; print(sys.stdin.read().strip())"], input="echoed")
    assert res.out == "echoed"


def test_which():
    assert proc.which(sys.executable.split("/")[-1]) or proc.which("python3") or proc.which("python")
    assert proc.which("definitely-not-a-real-binary-xyz") is False


def test_require_missing_raises():
    with pytest.raises(CliError) as exc:
        proc.require("definitely-not-a-real-binary-xyz", hint="install it")
    assert "install it" in str(exc.value)


def test_require_present_ok(monkeypatch):
    monkeypatch.setattr(proc, "which", lambda b: True)
    proc.require("anything")  # should not raise
