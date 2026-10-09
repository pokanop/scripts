"""Crash/commit-boundary regressions for the collection routing adapter."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_manager_migration import installation, setup_root, snapshot
from pokanop_manager import lifecycle as life


def test_hard_exit_during_wrapper_publication_keeps_previous_routing(installation):
    root, bin_dir = installation
    setup_root(root)
    before = life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=snapshot)
    code = '''
import os,sys
from pathlib import Path
sys.path.insert(0, sys.argv[3])
from test_manager_migration import snapshot
from pokanop_manager.lifecycle import install
install(Path(sys.argv[1]), Path(sys.argv[2]), ['pluck'], legacy_wrapper=lambda _: '',
        prepare_tool=snapshot, checkpoint=lambda phase: os._exit(23) if phase == 'wrapper' else None)
'''
    result = subprocess.run([sys.executable, "-c", code, str(root), str(bin_dir), str(Path(__file__).parent)])
    assert result.returncode == 23
    assert life.marker(root) == before
    assert subprocess.check_output([str(life.destination(bin_dir, "pluck"))], text=True).strip() == "working"
    # Kernel lock was released; no manual lock deletion or recovery needed.
    life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=snapshot)


def test_interrupt_after_marker_replace_keeps_committed_dispatcher(installation, monkeypatch):
    from scriptkit.manager import storage
    root, bin_dir = installation
    setup_root(root)
    (root / life.MARKER).write_text(json.dumps({"version": 1, "tools": ["pluck"]}))
    dest = life.destination(bin_dir, "pluck")
    dest.write_bytes(b"legacy")
    publish = storage.publish
    def interrupt(path, value):
        publish(path, value)
        if path == root / life.MARKER:
            raise KeyboardInterrupt()
    monkeypatch.setattr(storage, "publish", interrupt)
    with pytest.raises(KeyboardInterrupt):
        life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "legacy", prepare_tool=snapshot)
    assert life.marker(root)["version"] == 2
    assert dest.read_bytes() == life.wrapper(root, "pluck")
    assert subprocess.check_output([str(dest)], text=True).strip() == "working"


def test_rollback_rejects_changed_previous_marker(installation):
    root, bin_dir = installation
    setup_root(root)
    value = life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=snapshot)
    Path(value["previous_marker"]).write_text('{}')
    with pytest.raises(ValueError, match="modified"):
        life.rollback(root, bin_dir)
    assert life.marker(root) == value


def test_blob_tampering_rejected_before_activation(installation):
    root, bin_dir = installation
    setup_root(root)
    def corrupt(*args):
        snap = snapshot(*args)
        art = snap.plan().artifacts[0]
        (snap.directory / art.sha256).write_bytes(b"tampered")
        return snap
    with pytest.raises(ValueError, match="hash|size"):
        life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=corrupt)
    assert not (root / life.MARKER).exists()
    assert not list(bin_dir.iterdir())
