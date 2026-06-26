"""Tests for scriptkit.app — banner, examples block, parser factory."""

import scriptkit.app as app


def test_banner_plain(no_color):
    assert app.banner("mytool", "1.2.3", "does things", "🚀") == "🚀 mytool v1.2.3 — does things"


def test_banner_no_icon_no_tagline(no_color):
    assert app.banner("t", "0.1.0") == "t v0.1.0"


def test_banner_colorized():
    import scriptkit.style as style

    style.set_color(True)
    out = app.banner("t", "1.0.0", "tag")
    assert style.CYAN in out and style.DIM in out
    style.set_color(None)


def test_examples_block_aligns(no_color):
    out = app.examples_block([("t go", "do the thing"), ("t list", "show items")])
    assert out.splitlines()[0] == "Examples:"
    # commands column-aligned to the longest command
    assert "  t go    do the thing" in out
    assert "  t list  show items" in out


def test_examples_block_bare_strings(no_color):
    out = app.examples_block(["t go", "t stop"])
    assert "  t go" in out and "  t stop" in out


def test_make_parser_help_has_identity(no_color, capsys):
    import pytest

    parser = app.make_parser("mytool", "9.9.9", "a tagline", icon="🚀",
                             examples=[("mytool go", "run it")])
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])
    out = capsys.readouterr().out
    assert "mytool v9.9.9 — a tagline" in out
    assert "Examples:" in out and "mytool go" in out


def test_make_parser_version_flag(no_color, capsys):
    import pytest

    parser = app.make_parser("mytool", "9.9.9")
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])
    assert exc.value.code == 0
    assert "mytool 9.9.9" in capsys.readouterr().out


def test_make_parser_can_disable_version():
    parser = app.make_parser("mytool", "1.0.0", add_version=False)
    # -v should not be registered; parsing it errors out.
    import pytest

    with pytest.raises(SystemExit):
        parser.parse_args(["-v"])
