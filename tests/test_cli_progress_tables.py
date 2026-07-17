"""Tests for scriptkit.cli, scriptkit.progress, scriptkit.tables."""

import argparse

import pytest

import scriptkit.cli as cli
import scriptkit.progress as progress
import scriptkit.tables as tables
from scriptkit.cli import CliError


# --- cli -------------------------------------------------------------------
def test_run_cli_success():
    assert cli.run(lambda: None) == cli.EXIT_OK
    assert cli.run(lambda: 7) == 7


def test_run_cli_clierror(capsys):
    def boom():
        raise CliError("nope")

    assert cli.run(boom) == cli.EXIT_ERROR
    assert "nope" in capsys.readouterr().err


def test_run_cli_keyboardinterrupt(capsys):
    def boom():
        raise KeyboardInterrupt

    assert cli.run(boom) == cli.EXIT_INTERRUPT
    assert "Interrupted" in capsys.readouterr().err


def test_run_cli_unexpected_propagates():
    def boom():
        raise ValueError("bug")

    with pytest.raises(ValueError):
        cli.run(boom)


def test_dispatch_routes():
    seen = {}

    def handler(a):
        seen["hit"] = True

    ns = argparse.Namespace(command="go")
    rc = cli.dispatch(ns, {"go": handler})
    assert rc == cli.EXIT_OK and seen["hit"]


def test_dispatch_unknown_prints_help():
    ns = argparse.Namespace(command="nope")

    class FakeParser:
        printed = False

        def print_help(self):
            FakeParser.printed = True

    parser = FakeParser()
    rc = cli.dispatch(ns, {"go": lambda a: None}, parser)
    assert rc == cli.EXIT_ERROR and parser.printed


def test_dispatch_returns_handler_code():
    ns = argparse.Namespace(command="go")
    assert cli.dispatch(ns, {"go": lambda a: 5}) == 5


# --- progress --------------------------------------------------------------
def test_bar_endpoints():
    import scriptkit.style as style

    style.set_color(False)
    assert style.strip_ansi(progress.bar(0)).startswith("[")
    assert "0%" in progress.bar(0)
    assert "100%" in progress.bar(100)
    # clamps out-of-range input
    assert "100%" in progress.bar(150)
    assert "0%" in progress.bar(-5)


def test_track_yields_all_items(no_color):
    assert list(progress.track([1, 2, 3], "x")) == [1, 2, 3]


def test_track_handles_generator(no_color):
    gen = (i for i in range(3))
    assert list(progress.track(gen, "x")) == [0, 1, 2]


def test_track_bytes_yields_all_chunks(no_color):
    chunks = [b"abc", b"", b"defg"]
    assert list(progress.track_bytes(chunks, total=7)) == chunks


def test_track_bytes_renders_transfer_details(monkeypatch):
    import io

    from rich.console import Console
    import scriptkit.style as style

    output = io.StringIO()
    monkeypatch.setattr(
        progress,
        "console",
        Console(file=output, force_terminal=True, width=100),
    )
    style.set_color(True)

    assert list(progress.track_bytes([b"abc", b"def"], "Fetching", total=6)) == [
        b"abc",
        b"def",
    ]
    rendered = style.strip_ansi(output.getvalue())
    assert "Fetching" in rendered
    assert "100%" in rendered
    assert "6/6 bytes" in rendered


def test_parallel_map_results(no_color):
    out = progress.parallel_map(lambda x: x * 2, [1, 2, 3, 4], max_workers=2)
    assert sorted(out) == [2, 4, 6, 8]


def test_parallel_map_empty(no_color):
    assert progress.parallel_map(lambda x: x, []) == []


def test_parallel_map_preserves_completion_order(no_color):
    import time

    order = progress.parallel_map(
        lambda d: (time.sleep(d / 100.0) or d), [5, 1, 3, 2], max_workers=4
    )
    assert order[0] == 1 and order[-1] == 5


def test_parallel_map_worker_exception_propagates(no_color):
    with pytest.raises(ZeroDivisionError):
        progress.parallel_map(lambda x: 1 / 0 if x == 2 else x, [1, 2, 3], max_workers=3)


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX signals")
def test_parallel_map_interrupt_is_prompt(no_color):
    """Ctrl-C surfaces promptly instead of blocking on in-flight workers.

    Regression for POK-85: the old ThreadPoolExecutor implementation blocked at
    shutdown until every started task finished (e.g. a 20s network timeout), so
    the interrupt looked like a hang. Daemon workers + an interruptible
    collection loop mean the interpreter can bail immediately.
    """
    import os
    import signal
    import threading
    import time

    slow_finished = []
    fired = threading.Event()

    def fn(x):
        if x == 0:
            fired.set()
            os.kill(os.getpid(), signal.SIGINT)  # signal handled on main thread
            return x
        time.sleep(5)  # an in-flight worker we must NOT wait for
        slow_finished.append(x)
        return x

    start = time.perf_counter()
    with pytest.raises(KeyboardInterrupt):
        progress.parallel_map(fn, [0, 1, 2, 3], "interrupt", max_workers=4)
    elapsed = time.perf_counter() - start

    assert fired.is_set()
    assert elapsed < 3.0, f"interrupt took {elapsed:.2f}s; slow workers were awaited"
    assert slow_finished == [], "in-flight workers should be abandoned, not awaited"


def test_status_contextmanager(no_color, capsys):
    with progress.status("working") as st:
        st.update("still working")
    out = capsys.readouterr().out
    assert "working" in out


# --- tables ----------------------------------------------------------------
def test_table_renders_rows(capsys):
    tables.table(["Name", "Value"], [["a", "1"], ["b", "2"]], title="T")
    out = capsys.readouterr().out
    assert "Name" in out and "a" in out and "b" in out


def test_table_dict_columns(capsys):
    cols = [{"name": "#", "justify": "right"}, {"name": "Host"}]
    tables.table(cols, [[1, "router"]])
    out = capsys.readouterr().out
    assert "Host" in out and "router" in out
