"""Console output: semantic message helpers, prompts, rules, and key/values.

Messages are emitted with plain ``print`` + ANSI styling (deterministic and
trivial to capture in tests). Richer rendering — tables, panels, progress,
spinners — lives in sibling modules and uses ``rich`` when available.

The visual contract (indent + emoji + color) is unified from aikit / keyferry
/ pluck / voxtract so every tool looks like it came from the same author.
"""

from __future__ import annotations

import sys

from . import style
from .style import BOLD, CYAN, DIM, GREEN, RED, YELLOW

INDENT = "  "

# Optional rich consoles for advanced rendering. Stay importable without rich.
try:  # pragma: no cover - exercised indirectly
    from rich.console import Console as _RichConsole

    console = _RichConsole()
    err_console = _RichConsole(stderr=True)
    HAS_RICH = True
except Exception:  # pragma: no cover
    console = None
    err_console = None
    HAS_RICH = False


def _emit(text: str, *codes: str, stream=None) -> None:
    stream = stream if stream is not None else sys.stdout
    print(INDENT + style.styled(text, *codes, stream=stream), file=stream)


# --- Semantic messages -----------------------------------------------------
def success(text: str) -> None:
    """A completed action. Green ✅ on stdout."""
    _emit(f"✅ {text}", BOLD, GREEN)


def error(text: str) -> None:
    """A failure. Red ❌ on stderr."""
    _emit(f"❌ {text}", BOLD, RED, stream=sys.stderr)


def warning(text: str) -> None:
    """A caution that did not stop the run. Yellow ⚠️ on stdout."""
    _emit(f"⚠️  {text}", BOLD, YELLOW)


def info(text: str) -> None:
    """Secondary, low-emphasis context. Dim ℹ️ on stdout."""
    _emit(f"ℹ️  {text}", DIM, CYAN)


def detail(text: str) -> None:
    """A dim continuation/sub-line (no icon)."""
    _emit(text, DIM)


def step(n: int, total: int, text: str) -> None:
    """A numbered step in a known-length sequence: ``[2/5] doing thing``."""
    label = style.styled(f"[{n}/{total}]", BOLD, CYAN)
    print(f"{INDENT}{label} {text}")


def header(text: str, width: int = 50) -> None:
    """A section header — one consistent look everywhere: ``━━━ Text ━━━━━``.

    Bold accent rule, padded to ``width``. Kept identical across tools (and
    across TTY/non-TTY) so sections feel familiar; color strips when off.
    """
    pad = max(3, width - len(text) - 5)
    print("\n" + style.styled(f"━━━ {text} {'━' * pad}", BOLD, CYAN))


def elapsed(label: str, seconds: float) -> None:
    """A dim timing line: ``⏱️  label: 1.2s``."""
    from .text import human_duration

    _emit(f"⏱️  {label}: {human_duration(seconds)}", DIM)


def kv(label: str, value, label_width: int = 0) -> None:
    """A key/value line: a bold-ish dim label followed by its value."""
    key = f"{label}:".ljust(label_width + 1) if label_width else f"{label}:"
    print(f"{INDENT}{style.styled(key, DIM)} {value}")


# --- Prompts ---------------------------------------------------------------
def ask(prompt: str, default: str = "") -> str:
    """Prompt for a line of input. Returns ``default`` on empty/EOF."""
    suffix = style.styled(f" [{default}]", DIM) if default else ""
    text = f"{INDENT}{style.styled(prompt, BOLD, CYAN)}{suffix}: "
    try:
        value = input(text).strip()
    except EOFError:
        print()
        return default
    return value or default


def confirm(prompt: str, default: bool = False) -> bool:
    """Yes/no prompt. Returns ``default`` on empty/EOF/interrupt."""
    hint = "Y/n" if default else "y/N"
    try:
        value = input(f"{INDENT}{style.styled(prompt, BOLD, CYAN)} ({hint}) ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not value:
        return default
    return value[0] == "y"
