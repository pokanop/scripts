"""Tests for scriptkit.doctor — the shared diagnostic report."""

import sys

import scriptkit as sk

# ``sk.doctor`` is the function; the submodule (with its OK/WARN/FAIL constants)
# is reached via sys.modules since the package attribute is shadowed by design.
doctor = sys.modules["scriptkit.doctor"]


def test_check_factories_set_state():
    assert sk.Check.ok("a").state == doctor.OK
    assert sk.Check.warn("a").state == doctor.WARN
    assert sk.Check.fail("a").state == doctor.FAIL


def test_check_render_includes_glyph_and_detail(no_color):
    line = sk.Check.ok("Python", "3.13").render()
    assert "✓" in line and "Python" in line and "3.13" in line


def test_check_binary_found(no_color):
    # python3 is essentially always present in the test environment.
    chk = sk.check_binary("python3")
    assert chk.state == doctor.OK
    assert "Python" in chk.detail or chk.detail  # version captured


def test_check_binary_missing_required_is_fail(no_color):
    chk = sk.check_binary("definitely-not-a-real-binary-xyz", hint="install it")
    assert chk.state == doctor.FAIL
    assert chk.hint == "install it"


def test_check_binary_missing_optional_is_warn(no_color):
    chk = sk.check_binary("definitely-not-a-real-binary-xyz", required=False)
    assert chk.state == doctor.WARN


def test_check_python_found_and_missing(no_color):
    assert sk.check_python("sys").state == doctor.OK
    miss = sk.check_python("no_such_module_xyz", hint="pip install x")
    assert miss.state == doctor.FAIL and miss.hint == "pip install x"
    assert sk.check_python("no_such_module_xyz", required=False).state == doctor.WARN


def test_doctor_all_ok_returns_zero(no_color, capsys):
    rc = sk.doctor("mytool", "1.0.0", "tag", "🧰",
                   sections={"Checks": [sk.Check.ok("thing", "fine")]})
    out = capsys.readouterr().out
    assert rc == 0
    assert "System" in out and "Checks" in out
    assert "All checks passed" in out


def test_doctor_fail_returns_one_and_lists_issue(no_color, capsys):
    rc = sk.doctor("mytool", "1.0.0",
                   sections={"Checks": [sk.Check.fail("dep", "missing", "install dep")]})
    out = capsys.readouterr().out
    assert rc == 1
    assert "Issues" in out and "install dep" in out
    assert "1 error" in out


def test_doctor_mixed_fail_and_warn_summary(no_color, capsys):
    rc = sk.doctor(
        "mytool",
        "1.0.0",
        sections={
            "Checks": [
                sk.Check.fail("dep", "missing", "install dep"),
                sk.Check.warn("opt", "missing", "optional"),
            ]
        },
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "1 error, 1 warning" in out


def test_doctor_warn_only_returns_zero(no_color, capsys):
    rc = sk.doctor("mytool", "1.0.0",
                   sections={"Checks": [sk.Check.warn("opt", "missing", "optional")]})
    capsys.readouterr()
    assert rc == 0  # warnings don't fail the doctor


def test_doctor_renders_tips(no_color, capsys):
    sk.doctor("mytool", "1.0.0", sections={"Checks": [sk.Check.ok("x")]},
              tips=["do the thing"])
    out = capsys.readouterr().out
    assert "Tips" in out and "do the thing" in out


def test_doctor_system_section_can_be_disabled(no_color, capsys):
    sk.doctor("mytool", "1.0.0", sections={"Checks": [sk.Check.ok("x")]}, system=False)
    out = capsys.readouterr().out
    assert "System" not in out


def test_doctor_banner_opt_in(no_color, capsys):
    sk.doctor("mytool", "9.9.9", "tag", "🧰",
              sections={"Checks": [sk.Check.ok("x")]}, show_banner=True)
    out = capsys.readouterr().out
    assert "mytool v9.9.9 — tag" in out
