"""A shared ``doctor`` renderer — one diagnostic look for every tool.

Each tool's ``doctor`` command used to be hand-rolled (plain prints, rich
Panels, ad-hoc tables), so no two looked alike. This module gives a single,
beautiful, dependency-light report: an identity banner, an auto-generated
**System** section, tool-supplied **check sections**, a rolled-up **Issues**
list, optional **Tips**, and a one-line verdict with a meaningful exit code.

Typical use::

    import scriptkit as sk

    return sk.doctor(
        "netsy", __version__, TAGLINE, ICON,
        sections={
            "Prerequisites": [
                sk.check_binary("nmap", hint="brew install nmap"),
            ],
            "Network": [
                sk.Check.ok("Local IP", get_local_ip()),
            ],
        },
        tips=["Use scan --thorough --passes 3 to reduce variance"],
    )

``doctor`` returns an exit code (``1`` if any *required* check failed, else
``0``) so handlers can ``return sk.doctor(...)`` and have the process exit
status reflect the environment's health.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass

from . import style
from .console import INDENT, header
from .style import BOLD, CYAN, DIM, GREEN, RED, YELLOW

# Check states. "fail" is a missing *required* thing (drives exit 1); "warn"
# is a missing optional thing (visible, but non-fatal).
OK = "ok"
WARN = "warn"
FAIL = "fail"

_GLYPH = {OK: ("✓", GREEN), WARN: ("⚠", YELLOW), FAIL: ("✗", RED)}


@dataclass
class Check:
    """One diagnostic line: a label, a state, an optional detail and hint.

    ``state`` is one of :data:`OK`, :data:`WARN`, :data:`FAIL`. ``detail`` is
    shown inline (a version string, a path); ``hint`` is surfaced in the rolled
    up **Issues** section when the check is not OK.
    """

    label: str
    state: str = OK
    detail: str = ""
    hint: str = ""

    @classmethod
    def ok(cls, label: str, detail: str = "") -> "Check":
        return cls(label, OK, detail)

    @classmethod
    def warn(cls, label: str, detail: str = "", hint: str = "") -> "Check":
        return cls(label, WARN, detail, hint)

    @classmethod
    def fail(cls, label: str, detail: str = "", hint: str = "") -> "Check":
        return cls(label, FAIL, detail, hint)

    def render(self) -> str:
        glyph, color = _GLYPH.get(self.state, _GLYPH[OK])
        line = f"{INDENT}{style.styled(glyph, color, BOLD)} {self.label}"
        if self.detail:
            line += f" {style.styled('—', DIM)} {self.detail}"
        return line


def check_binary(
    binary: str,
    *,
    hint: str = "",
    required: bool = True,
    version: bool = True,
) -> Check:
    """Check a system binary is on ``PATH``; best-effort capture its version.

    Found -> :data:`OK` with the first line of ``<binary> --version`` as detail.
    Missing -> :data:`FAIL` if ``required`` else :data:`WARN`, carrying ``hint``.
    """
    from .proc import run, which

    path = which(binary)
    if not path:
        state = FAIL if required else WARN
        return Check(binary, state, "not found", hint or f"install {binary}")
    detail = ""
    if version:
        from .text import truncate

        res = run([binary, "--version"], timeout=5)
        out = (res.out or res.err or "").strip()
        if out:
            detail = truncate(out.splitlines()[0], 60)
    return Check(binary, OK, detail)


def check_python(module: str, *, hint: str = "", required: bool = True) -> Check:
    """Check an importable Python module. Missing -> FAIL (required) or WARN."""
    import importlib.util

    try:
        found = importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        found = False
    if found:
        return Check(f"python: {module}", OK, "available")
    state = FAIL if required else WARN
    return Check(f"python: {module}", state, "missing", hint or f"pip install {module}")


def _system_section(name: str, version: str) -> list[Check]:
    return [
        Check.ok("Platform", f"{platform.system()} {platform.release()}"),
        Check.ok("Python", sys.version.split()[0]),
        Check.ok(name, f"v{version}"),
    ]


def doctor(
    name: str,
    version: str,
    tagline: str = "",
    icon: str = "",
    *,
    sections,
    tips=None,
    system: bool = True,
    show_banner: bool = False,
) -> int:
    """Render a consistent diagnostic report; return ``0`` or ``1``.

    ``sections`` maps a section title to a list of :class:`Check`. When
    ``system`` is true, a leading **System** section (platform/python/version)
    is generated automatically. ``tips`` is an optional list of dim guidance
    lines. The return value is ``1`` iff any check is :data:`FAIL`.

    The identity banner is normally emitted by :func:`scriptkit.dispatch` (once,
    to stderr, for every command), so this renderer omits it. Pass
    ``show_banner=True`` to lead the report with the banner when calling
    :func:`doctor` outside the standard dispatch flow.
    """
    if show_banner:
        from .app import banner

        print(banner(name, version, tagline, icon))

    ordered = {}
    if system:
        ordered["System"] = _system_section(name, version)
    if isinstance(sections, dict):
        ordered.update(sections)
    else:  # list of (title, checks)
        ordered.update(dict(sections))

    issues: list[Check] = []
    for title, checks in ordered.items():
        header(title)
        for check in checks:
            print(check.render())
            if check.state in (WARN, FAIL):
                issues.append(check)

    if issues:
        header("Issues")
        for check in issues:
            glyph, color = _GLYPH[check.state]
            msg = check.hint or f"{check.label}: {check.detail}".strip(": ")
            print(f"{INDENT}{style.styled(glyph, color)} {msg}")

    if tips:
        header("Tips")
        for tip in tips:
            print(f"{INDENT}{style.styled('•', CYAN)} {style.styled(tip, DIM)}")

    print()
    fails = sum(1 for c in issues if c.state == FAIL)
    warns = sum(1 for c in issues if c.state == WARN)
    if not issues:
        print(f"{INDENT}{style.styled('✅ All checks passed', BOLD, GREEN)}")
    else:
        parts = []
        if fails:
            parts.append(f"{fails} error{'s' if fails != 1 else ''}")
        if warns:
            parts.append(f"{warns} warning{'s' if warns != 1 else ''}")
        glyph, color = (("❌", RED) if fails else ("⚠️", YELLOW))
        summary = ", ".join(parts)
        print(f"{INDENT}{style.styled(f'{glyph} {summary}', BOLD, color)}")

    return 1 if fails else 0
