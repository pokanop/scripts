"""Tests for scriptkit.blocks — the reversible managed-block primitive."""

from __future__ import annotations

import pytest

import scriptkit as sk
from scriptkit.blocks import (
    find_block,
    has_block,
    remove_block,
    render_block,
    upsert_block,
)

BEGIN = "# >>> demo >>>"
END = "# <<< demo <<<"
BODY = 'export A="1"\nexport B="2"'


# --- pure helpers ----------------------------------------------------------
def test_render_block_shapes():
    assert render_block(BEGIN, END, BODY) == f"{BEGIN}\nexport A=\"1\"\nexport B=\"2\"\n{END}\n"
    assert render_block(BEGIN, END, "") == f"{BEGIN}\n{END}\n"
    # edge newlines are trimmed so the shape is stable / idempotent
    assert render_block(BEGIN, END, "\n\nx\n\n") == f"{BEGIN}\nx\n{END}\n"


def test_create_into_empty_file():
    new, action = upsert_block("", BEGIN, END, BODY)
    assert action == "create"
    assert new == render_block(BEGIN, END, BODY)
    assert has_block(new, BEGIN, END)


def test_create_appends_with_single_blank_separator():
    new, action = upsert_block("setopt foo\n", BEGIN, END, BODY)
    assert action == "create"
    assert new == "setopt foo\n\n" + render_block(BEGIN, END, BODY)


def test_upsert_is_idempotent():
    once, _ = upsert_block("setopt foo\n", BEGIN, END, BODY)
    twice, action = upsert_block(once, BEGIN, END, BODY)
    assert action == "update"
    assert twice == once  # same body → byte-identical, no drift


def test_update_replaces_only_the_block():
    base, _ = upsert_block("pre\n", BEGIN, END, BODY)
    updated, action = upsert_block(base, BEGIN, END, 'export A="changed"')
    assert action == "update"
    assert "pre\n" in updated
    assert 'export A="changed"' in updated
    assert 'export B="2"' not in updated


def test_remove_restores_pristine_for_trailing_newline_file():
    original = "line one\nline two\n"
    inserted, _ = upsert_block(original, BEGIN, END, BODY)
    restored, removed = remove_block(inserted, BEGIN, END)
    assert removed is True
    assert restored == original  # byte-for-byte


def test_remove_on_empty_file_content():
    inserted, _ = upsert_block("", BEGIN, END, BODY)
    restored, removed = remove_block(inserted, BEGIN, END)
    assert removed is True
    assert restored == ""


def test_remove_preserves_content_after_block():
    text = f"pre\n\n{render_block(BEGIN, END, BODY)}post line\n"
    restored, removed = remove_block(text, BEGIN, END)
    assert removed is True
    assert restored == "pre\npost line\n"


def test_remove_missing_block_is_noop():
    restored, removed = remove_block("nothing here\n", BEGIN, END)
    assert removed is False
    assert restored == "nothing here\n"


@pytest.mark.parametrize("original", ["", "x", "x\n", "x\n\n", "a\nb", "a\nb\n"])
def test_upsert_remove_roundtrip_is_byte_for_byte(original):
    """create → remove restores the original exactly, regardless of trailing newline.

    The no-trailing-newline shapes (``"x"``, ``"a\\nb"``) are the ones that
    falsified the pristine guarantee before the paired upsert/remove fix.
    """
    inserted, action = upsert_block(original, BEGIN, END, BODY)
    assert action == "create"
    assert has_block(inserted, BEGIN, END)
    restored, removed = remove_block(inserted, BEGIN, END)
    assert removed is True
    assert restored == original  # byte-for-byte, trailing-newline state preserved


@pytest.mark.parametrize("original", ["x", "x\n", "a\nb"])
def test_upsert_distinguishes_trailing_newline(original):
    """A no-newline file and its newline-terminated sibling produce distinct output."""
    with_nl, _ = upsert_block(original.rstrip("\n") + "\n", BEGIN, END, BODY)
    without_nl, _ = upsert_block(original.rstrip("\n"), BEGIN, END, BODY)
    assert with_nl != without_nl


def test_indented_marker_still_matched():
    text = f"    {BEGIN}\n    body\n    {END}\n"
    assert has_block(text, BEGIN, END)
    span = find_block(text, BEGIN, END)
    assert span == (0, len(text))


# --- ManagedBlock file wrapper ---------------------------------------------
def test_managed_block_apply_and_clear_roundtrip(tmp_path):
    rc = tmp_path / ".zshrc"
    rc.write_text("# my shell\nalias g=git\n")
    original = rc.read_text()

    block = sk.ManagedBlock(BEGIN, END)
    action = block.apply(rc, BODY, backup_suffix=".bak")
    assert action == "create"
    assert block.present_in(rc.read_text())
    # backup captured the genuine pre-block state
    assert (tmp_path / ".zshrc.bak").read_text() == original

    # re-apply with same body is a no-op update; backup is not clobbered
    action2 = block.apply(rc, BODY, backup_suffix=".bak")
    assert action2 == "update"

    removed = block.clear(rc, backup_suffix=".bak", remove_backup=True)
    assert removed is True
    assert rc.read_text() == original
    assert not (tmp_path / ".zshrc.bak").exists()


def test_managed_block_apply_creates_missing_file(tmp_path):
    rc = tmp_path / "sub" / ".bashrc"
    block = sk.ManagedBlock(BEGIN, END)
    action = block.apply(rc, BODY)
    assert action == "create"
    assert rc.exists()
    # nothing pre-existed, so no backup was written
    assert not (rc.parent / ".bashrc.bak").exists()


def test_managed_block_clear_missing_file(tmp_path):
    block = sk.ManagedBlock(BEGIN, END)
    assert block.clear(tmp_path / "nope") is False


def test_managed_block_backup_not_overwritten_after_interrupted_apply(tmp_path):
    """A re-apply over a file that already has the block must not snapshot it."""
    rc = tmp_path / ".zshrc"
    rc.write_text("orig\n")
    block = sk.ManagedBlock(BEGIN, END)
    block.apply(rc, BODY, backup_suffix=".bak")
    # simulate a fresh run: backup already exists and file has the block
    block.apply(rc, 'export A="2"', backup_suffix=".bak")
    assert (tmp_path / ".zshrc.bak").read_text() == "orig\n"


def test_block_in_returns_exact_block(tmp_path):
    block = sk.ManagedBlock(BEGIN, END)
    text = "x\n\n" + render_block(BEGIN, END, BODY)
    assert block.block_in(text) == render_block(BEGIN, END, BODY)
    assert block.block_in("no block") is None
