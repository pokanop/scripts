"""Progress indicators: bars, spinners/status, tracked iteration, parallel map.

Built on ``rich`` when present, with graceful no-rich fallbacks so the tools
keep working in minimal environments. ``bar()`` is a pure-string renderer for
inline ``\\r`` progress with no dependency at all.
"""

from __future__ import annotations

import queue
import threading
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

    Workers are daemon threads and the main thread collects their results
    through a queue polled with a short timeout, so a Ctrl-C is raised promptly
    in the main thread and the interpreter can exit without waiting on in-flight
    work. A plain ``ThreadPoolExecutor`` would instead block at shutdown until
    every started task finished — e.g. a version check stuck in a 20s network
    timeout — making the interrupt look like a hang (POK-85).
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
    pending = queue.Queue()
    for item in items:
        pending.put(item)
    completed = queue.Queue()  # (ok: bool, payload: result | exception)

    def _worker():
        while True:
            try:
                item = pending.get_nowait()
            except queue.Empty:
                return
            try:
                completed.put((True, fn(item)))
            except BaseException as exc:  # surfaced in the main thread below
                completed.put((False, exc))

    for i in range(workers):
        threading.Thread(
            target=_worker, name=f"parallel_map-{i}", daemon=True
        ).start()

    def _drain(on_done=None):
        for _ in range(len(items)):
            # Poll with a timeout so a pending SIGINT is raised here between
            # waits instead of being held off by an untimed blocking get().
            while True:
                try:
                    ok, payload = completed.get(timeout=0.1)
                    break
                except queue.Empty:
                    continue
            if not ok:
                raise payload
            results.append(payload)
            if on_done is not None:
                on_done()

    if progress_cm is not None:
        with progress_cm as progress:
            task = progress.add_task(description, total=len(items))
            _drain(lambda: progress.advance(task))
    else:
        _drain()

    return results
