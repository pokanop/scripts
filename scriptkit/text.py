"""Human-friendly formatting helpers: sizes, durations, counts, truncation."""

from __future__ import annotations


def human_size(num_bytes: float, *, binary: bool = True) -> str:
    """Format a byte count as a human string (``1.5 MB``).

    ``binary`` uses 1024 steps (the default, matching disk/file tooling);
    pass ``binary=False`` for 1000-based SI units.
    """
    step = 1024.0 if binary else 1000.0
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < step:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= step
    return f"{value:.1f} PB"


def human_duration(seconds: float) -> str:
    """Format a span as ``850ms`` / ``4.2s`` / ``3m 5s`` / ``1h 2m``."""
    seconds = float(seconds)
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        m, s = divmod(int(round(seconds)), 60)
        return f"{m}m {s}s"
    h, rem = divmod(int(round(seconds)), 3600)
    m = rem // 60
    return f"{h}h {m}m"


def format_timecode(seconds: float) -> str:
    """Format a position as a media timecode: ``m:ss.ss`` or ``h:mm:ss.ss``."""
    seconds = float(seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:05.2f}"
    return f"{m}:{s:05.2f}"


def human_count(n: int, singular: str, plural: str | None = None) -> str:
    """Pluralize a count: ``human_count(1, 'host') -> '1 host'``."""
    word = singular if n == 1 else (plural or singular + "s")
    return f"{n} {word}"


def truncate(text: str, width: int, ellipsis: str = "…") -> str:
    """Truncate ``text`` to ``width`` columns, appending an ellipsis if cut."""
    if width <= 0 or len(text) <= width:
        return text
    if width <= len(ellipsis):
        return text[:width]
    return text[: width - len(ellipsis)].rstrip() + ellipsis
