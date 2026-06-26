"""Color, ANSI styling, and semantic icons.

A dependency-free styling layer shared by every tool. Color is resolved
*dynamically* on each call (so ``NO_COLOR`` / a piped stdout / a forced
override all take effect at runtime, which keeps the behaviour easy to test),
and ``styled()`` degrades to plain — code-stripped — text when color is off.

The canonical reference for the no-color contract:
- ``NO_COLOR`` set (any value)         -> color off   (https://no-color.org)
- ``FORCE_COLOR`` set (any value)      -> color on
- otherwise                            -> on iff the target stream is a TTY
"""

from __future__ import annotations

import os
import re
import sys

# --- ANSI codes ------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
GRAY = "\033[90m"

BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_BLUE = "\033[44m"

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")

# When not None, forces color on (True) or off (False) regardless of env/TTY.
_OVERRIDE: bool | None = None


def set_color(enabled: bool | None) -> None:
    """Force color on/off, or pass ``None`` to restore auto-detection."""
    global _OVERRIDE
    _OVERRIDE = enabled


def use_color(stream=None) -> bool:
    """Return whether color should be emitted to ``stream`` (default: stdout)."""
    if _OVERRIDE is not None:
        return _OVERRIDE
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    stream = stream if stream is not None else sys.stdout
    try:
        return bool(stream.isatty())
    except Exception:
        return False


def strip_ansi(text: str) -> str:
    """Remove all ANSI SGR escape sequences from ``text``."""
    return _ANSI_RE.sub("", text)


def styled(text: str, *codes: str, stream=None) -> str:
    """Wrap ``text`` in ANSI ``codes``; strip codes entirely when color is off."""
    if not use_color(stream):
        return strip_ansi(text)
    if not codes:
        return text
    return "".join(codes) + text + RESET


# --- Semantic icons --------------------------------------------------------
# Curated emoji set merged from every tool. Names are stable; the glyphs may
# change in one place and update everywhere. Multi-cell glyphs that use a
# variation selector carry a trailing space so columns line up in terminals.
ICONS: dict[str, str] = {
    # status
    "success": "✅",
    "error": "❌",
    "warning": "⚠️ ",
    "warn": "⚠️ ",
    "info": "ℹ️ ",
    "check": "✔",
    "cross": "✗",
    "bullet": "•",
    "arrow": "→",
    "question": "❓",
    # time / progress
    "clock": "⏱️ ",
    "hourglass": "⏳",
    "rocket": "🚀",
    "sparkle": "✨",
    "spinner": "⠋",
    # objects / domains
    "folder": "📁",
    "package": "📦",
    "gear": "⚙️ ",
    "lock": "🔒",
    "key": "🔑",
    "link": "🔗",
    "search": "🔍",
    "cache": "💾",
    "server": "🖥️ ",
    "source": "📡",
    "download": "⬇️ ",
    "upload": "⬆️ ",
    "brain": "🧠",
    "robot": "🤖",
    "wave": "🌊",
    "music": "🎵",
    "mic": "🎤",
    "speaker": "🔊",
    "extract": "🎯",
    "normalize": "📊",
    "clip": "✂️ ",
    "book": "📖",
    "movie": "🎬",
    "tv": "📺",
    "trash": "🗑️ ",
    "plug": "🔌",
    "globe": "🌐",
    "shield": "🛡️ ",
    "ship": "🛳️ ",
}


def icon(name: str, default: str = "") -> str:
    """Look up a semantic icon by name. Unknown names return ``default``."""
    return ICONS.get(name, default)
