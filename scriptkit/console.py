"""Console output: semantic message helpers, prompts, rules, and key/values.

Semantic messages use ``rich`` when available so inline markup like
``[dim]…[/dim]`` and ``[bold]…[/bold]`` renders correctly; they fall back to
plain ``print`` + ANSI styling (markup tags stripped) when color is off or
``rich`` is missing. Tables, panels, progress, and spinners also live in
sibling modules.

The visual contract (indent + emoji + color) is unified from aikit / keyferry
/ pluck / voxtract so every tool looks like it came from the same author.
"""

from __future__ import annotations

import re
import sys

from . import style
from .style import BOLD, CYAN, DIM, GREEN, RED, YELLOW

INDENT = "  "
_MARKUP_RE = re.compile(r"\[/?[^\]]+\]")


# Optional rich consoles for advanced rendering. Stay importable without rich.
try:  # pragma: no cover - exercised indirectly
    from rich.console import Console as _RichConsole

    def _rich_console_for(stream=None):
        """Rich Console honoring scriptkit color resolution (FORCE_COLOR, override, TTY)."""
        stream = stream if stream is not None else sys.stdout
        color = style.use_color(stream)
        return _RichConsole(
            stderr=(stream is sys.stderr),
            force_terminal=color,
            no_color=not color,
        )

    console = _rich_console_for(sys.stdout)
    err_console = _rich_console_for(sys.stderr)
    HAS_RICH = True
except Exception:  # pragma: no cover
    _rich_console_for = None  # type: ignore[misc, assignment]

    console = None
    err_console = None
    HAS_RICH = False


def _strip_markup(text: str) -> str:
    """Remove Rich markup tags for plain / no-color output."""
    return _MARKUP_RE.sub("", text)


def _emit(text: str, *codes: str, rich_style: str | None = None, stream=None) -> None:
    """Emit an indented line. ``rich_style`` enables nested Rich markup in ``text``."""
    stream = stream if stream is not None else sys.stdout
    use_rich = rich_style and HAS_RICH and style.use_color(stream)
    if use_rich:
        try:
            use_rich = stream.isatty()
        except Exception:
            use_rich = False
    if use_rich:
        _rich_console_for(stream).print(INDENT + text, style=rich_style)
        return
    plain = _strip_markup(text) if "[" in text else text
    print(INDENT + style.styled(plain, *codes, stream=stream), file=stream)


# --- Semantic messages -----------------------------------------------------
def success(text: str) -> None:
    """A completed action. Green ✅ on stdout."""
    _emit(f"✅ {text}", BOLD, GREEN, rich_style="bold green")


def error(text: str) -> None:
    """A failure. Red ❌ on stderr."""
    _emit(f"❌ {text}", BOLD, RED, stream=sys.stderr, rich_style="bold red")


def warning(text: str) -> None:
    """A caution that did not stop the run. Yellow ⚠️ on stdout."""
    _emit(f"⚠️  {text}", BOLD, YELLOW, rich_style="bold yellow")


def info(text: str) -> None:
    """Secondary, low-emphasis context. Dim ℹ️ on stdout."""
    _emit(f"ℹ️  {text}", DIM, CYAN, rich_style="dim cyan")


def detail(text: str) -> None:
    """A dim continuation/sub-line (no icon)."""
    _emit(text, DIM, rich_style="dim")


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
    print("\n" + style.styled(f"━━━ {text} {'━' * pad}", BOLD))


def elapsed(label: str, seconds: float) -> None:
    """A dim timing line: ``⏱️  label: 1.2s``."""
    from .text import human_duration

    _emit(f"⏱️  {label}: {human_duration(seconds)}", DIM, rich_style="dim")


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
