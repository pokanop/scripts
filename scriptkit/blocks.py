"""Managed text blocks — insert, replace, or remove a marked region in a file.

A *managed block* is a span of lines fenced by a ``begin``/``end`` marker pair
(e.g. the ``# >>> … >>>`` / ``# <<< … <<<`` stanzas shells use). The point of
this module is that the block is **reversible and idempotent**: writing the same
body twice is a no-op, and removing the block restores the surrounding file —
the inverse of an insert. That makes it the right primitive for anything a tool
needs to add to a user's file and later take back out cleanly (shell rc env
blocks, managed config stanzas, hosts-file entries, …).

The pure string helpers (:func:`upsert_block`, :func:`remove_block`) do the
splicing; :class:`ManagedBlock` is a thin file wrapper that snapshots a ``.bak``
before the first write and applies/clears on disk.

    block = ManagedBlock("# >>> mytool >>>", "# <<< mytool <<<")
    block.apply(rc_path, 'export FOO="bar"')   # idempotent insert/replace
    block.clear(rc_path)                        # pristine removal

Markers are matched on their own (stripped) line, so leading indentation never
hides a block.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def render_block(begin: str, end: str, body: str = "") -> str:
    """Render ``body`` fenced by the markers, as ``begin\\n[body\\n]end\\n``.

    Edge newlines on ``body`` are trimmed so the block has a single, stable
    shape — re-rendering the same body is byte-identical (the property that
    makes :func:`upsert_block` idempotent).
    """
    body = body.strip("\n")
    if body:
        return f"{begin}\n{body}\n{end}\n"
    return f"{begin}\n{end}\n"


def find_block(text: str, begin: str, end: str) -> tuple[int, int] | None:
    """Return the ``(start, stop)`` offsets of the block's full lines, or ``None``.

    ``start`` is the first column of the ``begin`` marker line; ``stop`` is just
    past the newline that ends the ``end`` marker line. ``text[start:stop]`` is
    therefore the complete block including its trailing newline.
    """
    bi = text.find(begin)
    if bi == -1:
        return None
    ei = text.find(end, bi + len(begin))
    if ei == -1:
        return None
    start = text.rfind("\n", 0, bi) + 1  # 0 when the marker is on the first line
    nl = text.find("\n", ei + len(end))
    stop = len(text) if nl == -1 else nl + 1
    return start, stop


def has_block(text: str, begin: str, end: str) -> bool:
    """True if ``text`` already contains a complete managed block."""
    return find_block(text, begin, end) is not None


def upsert_block(text: str, begin: str, end: str, body: str) -> tuple[str, str]:
    """Insert or replace the managed block. Returns ``(new_text, action)``.

    ``action`` is ``"update"`` when an existing block was replaced (surrounding
    content untouched) or ``"create"`` when the block was appended. Appending to
    a non-empty file inserts one blank separator line before the block; that
    separator is exactly what :func:`remove_block` takes back out, so
    ``upsert`` then ``remove`` round-trips.
    """
    block = render_block(begin, end, body)
    span = find_block(text, begin, end)
    if span:
        start, stop = span
        return text[:start] + block + text[stop:], "update"
    if not text:
        return block, "create"
    base = text if text.endswith("\n") else text + "\n"
    return base + "\n" + block, "create"


def remove_block(text: str, begin: str, end: str) -> tuple[str, bool]:
    """Strip the managed block. Returns ``(new_text, removed)``.

    Removes the block's lines and the single blank separator an appended block
    carries, leaving the rest of the file intact — the inverse of
    :func:`upsert_block`. ``removed`` is ``False`` when no block was present.
    """
    span = find_block(text, begin, end)
    if not span:
        return text, False
    start, stop = span
    pre, post = text[:start], text[stop:]
    if start > 0 and pre.endswith("\n\n"):
        pre = pre[:-1]
    return pre + post, True


@dataclass(frozen=True)
class ManagedBlock:
    """A begin/end marker pair, with on-disk apply/clear helpers.

    ``apply`` writes (or replaces) the block in a file, snapshotting a backup
    once before the first write; ``clear`` removes it. Both are idempotent.
    """

    begin: str
    end: str

    def render(self, body: str = "") -> str:
        return render_block(self.begin, self.end, body)

    def present_in(self, text: str) -> bool:
        return has_block(text, self.begin, self.end)

    def block_in(self, text: str) -> str | None:
        """Return the block's exact current text (for drift checks), or ``None``."""
        span = find_block(text, self.begin, self.end)
        return text[span[0]:span[1]] if span else None

    def apply(self, path, body: str, *, backup_suffix: str | None = ".bak") -> str:
        """Write the block into ``path``; return ``"create"`` or ``"update"``.

        A backup (``<path><backup_suffix>``) is written once — only when the
        file exists, has no managed block yet, and no backup exists — so it
        captures the genuine pre-block state and is never clobbered by a later
        ``apply``.
        """
        path = Path(path)
        current = path.read_text() if path.exists() else ""
        new_text, action = upsert_block(current, self.begin, self.end, body)
        if backup_suffix and path.exists() and not self.present_in(current):
            backup = path.with_name(path.name + backup_suffix)
            if not backup.exists():
                backup.write_text(current)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_text)
        return action

    def clear(self, path, *, backup_suffix: str | None = ".bak",
              remove_backup: bool = False) -> bool:
        """Remove the block from ``path``; return whether anything was removed.

        With ``remove_backup`` the ``.bak`` snapshot is deleted too (the state
        it guarded is gone once the block is out).
        """
        path = Path(path)
        if not path.exists():
            return False
        new_text, removed = remove_block(path.read_text(), self.begin, self.end)
        if removed:
            path.write_text(new_text)
        if remove_backup and backup_suffix:
            backup = path.with_name(path.name + backup_suffix)
            try:
                backup.unlink()
            except OSError:
                pass
        return removed
