"""Tests for scriptkit.console — message routing, prompts, formatting."""

import builtins

import pytest

import scriptkit.console as console


def test_success_to_stdout(no_color, capsys):
    console.success("done")
    out = capsys.readouterr()
    assert "✅ done" in out.out
    assert out.err == ""


def test_error_to_stderr(no_color, capsys):
    console.error("boom")
    out = capsys.readouterr()
    assert "❌ boom" in out.err
    assert out.out == ""


def test_warning_and_info(no_color, capsys):
    console.warning("careful")
    console.info("note")
    out = capsys.readouterr().out
    assert "⚠️" in out and "careful" in out
    assert "ℹ️" in out and "note" in out


def test_step(no_color, capsys):
    console.step(2, 5, "building")
    assert "[2/5] building" in capsys.readouterr().out


def test_detail(no_color, capsys):
    console.detail("sub line")
    assert "sub line" in capsys.readouterr().out


def test_kv(no_color, capsys):
    console.kv("Host", "router")
    assert "Host:" in capsys.readouterr().out


def test_elapsed(no_color, capsys):
    console.elapsed("build", 4.2)
    out = capsys.readouterr().out
    assert "build" in out and "4.2s" in out


def test_header(no_color, capsys):
    console.header("Section")
    assert "Section" in capsys.readouterr().out


def test_color_codes_present_when_enabled(capsys):
    import scriptkit.style as style

    style.set_color(True)
    console.success("x")
    out = capsys.readouterr().out
    assert style.GREEN in out
    style.set_color(None)


def test_ask_returns_input(no_color, monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *a: "  typed  ")
    assert console.ask("name?") == "typed"


def test_ask_default_on_empty(no_color, monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *a: "")
    assert console.ask("name?", default="fallback") == "fallback"


def test_ask_default_on_eof(no_color, monkeypatch):
    def raise_eof(*a):
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)
    assert console.ask("name?", default="d") == "d"


@pytest.mark.parametrize(
    "answer,default,expected",
    [
        ("y", False, True),
        ("yes", False, True),
        ("n", True, False),
        ("", True, True),
        ("", False, False),
        ("garbage", False, False),
    ],
)
def test_confirm(no_color, monkeypatch, answer, default, expected):
    monkeypatch.setattr(builtins, "input", lambda *a: answer)
    assert console.confirm("ok?", default=default) is expected


def test_confirm_eof_returns_default(no_color, monkeypatch):
    def raise_eof(*a):
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)
    assert console.confirm("ok?", default=True) is True
