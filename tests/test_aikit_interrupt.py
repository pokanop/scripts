"""Interrupt / subprocess-lifecycle tests for aikit's ``run`` (POK-85).

``aikit update`` couldn't be aborted cleanly with Ctrl-C: the update command is
run through ``run()``, and the previous implementation only killed the immediate
shell, orphaning the real installer tree it spawned. ``run()`` now isolates
captured children in their own session/process group and tears down the *whole*
group on interrupt or timeout, so nothing survives the abort — the same in tmux
or a plain terminal.

These are POSIX tests (process groups / signals); skipped elsewhere. Liveness is
checked via a heartbeat file the grandchild keeps touching rather than
``os.kill(pid, 0)``, which can't tell a killed-but-unreaped zombie from a live
process once the parent shell is gone.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX process groups")


@pytest.fixture
def aikit(tool_loader):
    return tool_loader("aikit")


def _tree_cmd(started: str, heartbeat: str) -> str:
    """Shell command that backgrounds a signal-ignoring grandchild.

    The grandchild ignores SIGINT/SIGTERM, records its pid in ``started``, then
    touches ``heartbeat`` every 50ms for ~100s (a bounded comprehension keeps it
    a single ``python -c`` statement). A frozen heartbeat therefore means the
    grandchild was actually terminated — only ``SIGKILL`` to the whole group can
    do that. ``& wait`` keeps the captured parent shell alive so the run reaches
    its interrupt/timeout instead of returning on its own.
    """
    body = (
        "import os,signal,time;"
        "signal.signal(signal.SIGINT,signal.SIG_IGN);"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
        f"open({started!r},'w').write(str(os.getpid()));"
        f"[(open({heartbeat!r},'w').write(str(time.time())),time.sleep(0.05)) "
        "for _ in range(2000)]"
    )
    return f"{sys.executable} -c {body!r} & wait"


def _wait_for(path: str, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path):
            return
        time.sleep(0.02)
    raise AssertionError(f"{path} was never created")


def _assert_heartbeat_stops(path: str, settle: float = 0.5, timeout: float = 5.0) -> None:
    """Pass once ``path``'s mtime holds still for ``settle`` (writer is dead)."""
    _wait_for(path)
    deadline = time.time() + timeout
    last = None
    stable_since = None
    while time.time() < deadline:
        try:
            mtime = os.stat(path).st_mtime_ns
        except FileNotFoundError:
            mtime = None
        now = time.time()
        if mtime == last:
            stable_since = stable_since or now
            if now - stable_since >= settle:
                return
        else:
            last = mtime
            stable_since = None
        time.sleep(0.03)
    raise AssertionError(f"heartbeat {path} kept advancing; process not terminated")


def test_run_captures_output(aikit):
    assert aikit.run("echo hi") == (0, "hi", "")
    assert aikit.run("echo out; echo err 1>&2; exit 3") == (3, "out", "err")


def test_run_captured_child_is_session_isolated(aikit):
    """Captured runs get their own process group, so a group signal on teardown
    can only reach the child tree, never aikit itself."""
    code, out, _ = aikit.run(f"{sys.executable} -c 'import os; print(os.getpgrp())'")
    assert code == 0
    assert int(out) != os.getpgrp()


def test_run_timeout_terminates_whole_tree(aikit, tmp_path):
    started = tmp_path / "started"
    heartbeat = tmp_path / "hb"
    t0 = time.perf_counter()
    code, _, err = aikit.run(_tree_cmd(str(started), str(heartbeat)), timeout=0.5)
    elapsed = time.perf_counter() - t0

    assert code == -1
    assert "timed out" in err
    assert elapsed < 4.0
    _assert_heartbeat_stops(str(heartbeat))


def test_terminate_process_tree_kills_group_on_interrupt(aikit, tmp_path):
    started = tmp_path / "started"
    heartbeat = tmp_path / "hb"
    proc = subprocess.Popen(
        _tree_cmd(str(started), str(heartbeat)),
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        _wait_for(str(started))
        # Exactly what run() does on Ctrl-C: signal the whole group and reap.
        aikit._terminate_process_tree(proc, proc.pid, signal.SIGINT)
        assert proc.poll() is not None  # the shell itself was reaped
        _assert_heartbeat_stops(str(heartbeat))
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
