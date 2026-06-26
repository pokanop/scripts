"""Progress indicators: bars, spinners/status, tracked iteration, parallel map.

Built on ``rich`` when present, with graceful no-rich fallbacks so the tools
keep working in minimal environments. ``bar()`` is a pure-string renderer for
inline ``\\r`` progress with no dependency at all.
"""

from __future__ import annotations

import concurrent.futures
from contextlib import contextmanager

from . import style
from .console import HAS_RICH, console


def bar(pct: float, width: int = 30) -> str:
    """Render a unicode progress bar string: ``[████░░░░] 50%``."""
    pct = max(0.0, min(100.0, float(pct)))
    filled = int(width * pct / 100)
    glyph = "█" * filled + "░" * (width - filled)
    color = style.GREEN if pct >= 100 else style.CYAN
    return style.styled(f"[{glyph}] {pct:.0f}%", color, style.BOLD)


@contextmanager
def status(message: str):
    """Spinner + message for indeterminate work. Falls back to a printed line."""
    if HAS_RICH and console is not None and style.use_color():
        with console.status(message) as st:
            yield st
        return

    class _Plain:
        def update(self, msg):
            print(f"  {style.styled(str(msg), style.DIM)}")

    print(f"  {style.styled(message, style.DIM)}")
    yield _Plain()


def track(iterable, description: str = "Working", total: int | None = None):
    """Iterate ``iterable`` while showing a progress bar (rich) or plainly."""
    if total is None:
        try:
            total = len(iterable)
        except TypeError:
            total = None
    if HAS_RICH and console is not None and style.use_color():
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeElapsedColumn,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(description, total=total)
            for item in iterable:
                yield item
                progress.advance(task)
    else:
        yield from iterable


def parallel_map(fn, items, description: str = "Working", max_workers: int = 8):
    """Run ``fn`` over ``items`` concurrently, showing combined progress.

    Returns results in completion order. Exceptions propagate from the worker.
    """
    items = list(items)
    results = []
    if not items:
        return results

    use_progress = HAS_RICH and console is not None and style.use_color()
    if use_progress:
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeElapsedColumn,
        )

        progress_cm = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        )
    else:
        progress_cm = None

    workers = max(1, min(max_workers, len(items)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fn, it) for it in items]
        if progress_cm is not None:
            with progress_cm as progress:
                task = progress.add_task(description, total=len(items))
                for fut in concurrent.futures.as_completed(futures):
                    results.append(fut.result())
                    progress.advance(task)
        else:
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())
    return results
