"""Tests for scriptkit.cli — parse_args defaults, dispatch, run_cli."""

import argparse

import pytest

import scriptkit as sk


def _parser():
    p = sk.make_parser("t", "1.0.0", "tag", icon="🧰")
    sub = p.add_subparsers(dest="command")
    scan = sub.add_parser("scan")
    scan.add_argument("--deep", action="store_true")
    sub.add_parser("doctor")
    return p


# --- parse_args -------------------------------------------------------------
def test_parse_args_injects_default_when_bare():
    args = sk.parse_args(_parser(), default="scan", argv=[])
    assert args.command == "scan"
    assert args.deep is False  # scan's defaults populated


def test_parse_args_injects_default_before_flags():
    args = sk.parse_args(_parser(), default="scan", argv=["--deep"])
    assert args.command == "scan" and args.deep is True


def test_parse_args_keeps_explicit_command():
    args = sk.parse_args(_parser(), default="scan", argv=["doctor"])
    assert args.command == "doctor"


def test_parse_args_no_default_leaves_command_none():
    args = sk.parse_args(_parser(), argv=[])
    assert args.command is None


def test_parse_args_does_not_inject_for_help():
    with pytest.raises(SystemExit):
        sk.parse_args(_parser(), default="scan", argv=["--help"])


# --- dispatch ---------------------------------------------------------------
def test_dispatch_runs_handler_and_returns_code():
    args = argparse.Namespace(command="scan")
    rc = sk.dispatch(args, {"scan": lambda a: 7})
    assert rc == 7


def test_dispatch_none_return_is_zero():
    args = argparse.Namespace(command="scan")
    assert sk.dispatch(args, {"scan": lambda a: None}) == 0


def test_dispatch_prints_banner_to_stderr(capsys):
    args = argparse.Namespace(command="scan")
    sk.dispatch(args, {"scan": lambda a: 0}, banner="BANNER-LINE")
    captured = capsys.readouterr()
    assert "BANNER-LINE" in captured.err
    assert "BANNER-LINE" not in captured.out  # never pollutes stdout


def test_dispatch_bare_no_default_prints_help_exit_zero(capsys):
    parser = _parser()
    args = argparse.Namespace(command=None)
    rc = sk.dispatch(args, {}, parser)
    assert rc == 0
    assert "usage:" in capsys.readouterr().out


def test_dispatch_default_resolves_command():
    args = argparse.Namespace(command=None)
    rc = sk.dispatch(args, {"scan": lambda a: 5}, default="scan")
    assert rc == 5


def test_dispatch_unknown_command_exit_one(capsys):
    parser = _parser()
    args = argparse.Namespace(command="bogus")
    rc = sk.dispatch(args, {"scan": lambda a: 0}, parser)
    assert rc == sk.EXIT_ERROR


# --- run_cli ----------------------------------------------------------------
def test_run_cli_returns_exit_code():
    assert sk.run_cli(lambda: 3) == 3
    assert sk.run_cli(lambda: None) == 0


def test_run_cli_catches_clierror_subclass(capsys):
    class ToolError(sk.CliError):
        pass

    def boom():
        raise ToolError("clean message")

    rc = sk.run_cli(boom)
    assert rc == sk.EXIT_ERROR
    assert "clean message" in capsys.readouterr().err


def test_run_cli_interrupt_runs_cleanup_and_exits_130(capsys):
    calls = []

    def boom():
        raise KeyboardInterrupt

    rc = sk.run_cli(boom, on_interrupt=lambda: calls.append(1))
    assert rc == sk.EXIT_INTERRUPT
    assert calls == [1]
    assert "Interrupted" in capsys.readouterr().err


def test_run_cli_interrupt_cleanup_errors_are_swallowed():
    def boom():
        raise KeyboardInterrupt

    def bad_cleanup():
        raise RuntimeError("cleanup failed")

    # Must not propagate the cleanup error.
    assert sk.run_cli(boom, on_interrupt=bad_cleanup) == sk.EXIT_INTERRUPT
