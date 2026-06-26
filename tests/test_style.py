"""Tests for scriptkit.style — color resolution, styling, icons."""

import scriptkit.style as style


def test_use_color_override():
    style.set_color(True)
    assert style.use_color() is True
    style.set_color(False)
    assert style.use_color() is False
    style.set_color(None)


def test_no_color_env_wins(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert style.use_color() is False


def test_force_color_env(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert style.use_color() is True


def test_no_color_beats_force(monkeypatch):
    # NO_COLOR is checked first per the no-color.org contract.
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert style.use_color() is False


def test_use_color_non_tty(monkeypatch):
    class FakeStream:
        def isatty(self):
            return False

    assert style.use_color(FakeStream()) is False

    class TtyStream:
        def isatty(self):
            return True

    assert style.use_color(TtyStream()) is True


def test_styled_with_color():
    style.set_color(True)
    out = style.styled("hi", style.BOLD, style.GREEN)
    assert out == f"{style.BOLD}{style.GREEN}hi{style.RESET}"


def test_styled_without_color_strips():
    style.set_color(False)
    assert style.styled("hi", style.BOLD, style.GREEN) == "hi"
    # Pre-existing codes in the text are removed too.
    assert style.styled(f"{style.RED}x{style.RESET}", style.BOLD) == "x"


def test_styled_no_codes_passthrough():
    style.set_color(True)
    assert style.styled("plain") == "plain"


def test_strip_ansi():
    assert style.strip_ansi(f"{style.RED}a{style.RESET}b") == "ab"


def test_icon_known_and_unknown():
    assert style.icon("success") == "✅"
    assert style.icon("nope") == ""
    assert style.icon("nope", "?") == "?"
    # Every advertised icon resolves to a non-empty glyph.
    assert all(v for v in style.ICONS.values())
