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


def test_parallel_map_results(no_color):
    out = progress.parallel_map(lambda x: x * 2, [1, 2, 3, 4], max_workers=2)
    assert sorted(out) == [2, 4, 6, 8]


def test_parallel_map_empty(no_color):
    assert progress.parallel_map(lambda x: x, []) == []


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
