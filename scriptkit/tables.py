"""Table rendering: a thin, declarative wrapper over ``rich.table.Table``.

Columns are described as dicts so callers stay declarative; falls back to an
aligned plain-text grid when ``rich`` is unavailable.
"""

from __future__ import annotations

from . import style
from .console import HAS_RICH, console


def table(columns, rows, *, title: str | None = None, caption: str | None = None) -> None:
    """Print a table.

    ``columns`` is a list of either strings (header names) or dicts with keys:
    ``name`` (header), ``justify`` ("left"/"right"/"center"), ``style`` (rich
    style), ``width``/``max_width``, ``no_wrap``. ``rows`` is a list of cell
    sequences (cells stringified by the caller, may contain rich markup).
    """
    specs = [{"name": c} if isinstance(c, str) else dict(c) for c in columns]

    if HAS_RICH and console is not None:
        from rich.table import Table

        rich_table = Table(title=title, caption=caption, header_style="bold cyan", title_style="bold")
        for spec in specs:
            rich_table.add_column(
                spec.get("name", ""),
                justify=spec.get("justify", "left"),
                style=spec.get("style"),
                width=spec.get("width"),
                max_width=spec.get("max_width"),
                no_wrap=spec.get("no_wrap", False),
            )
        for row in rows:
            rich_table.add_row(*[str(cell) for cell in row])
        console.print(rich_table)
        return

    _plain_table(specs, rows, title)


def _plain_table(specs, rows, title) -> None:
    headers = [s.get("name", "") for s in specs]
    str_rows = [[style.strip_ansi(str(cell)) for cell in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    def fmt(cells):
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    if title:
        print(title)
    print(fmt(headers))
    print("  ".join("-" * w for w in widths))
    for row in str_rows:
        print(fmt(row))
