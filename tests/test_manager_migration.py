"""Offline transaction and real installed-wrapper acceptance tests."""
import json
import os
from pathlib import Path
import subprocess
import sys
from functools import partial

import pytest

from pokanop_manager import lifecycle as life
from pokanop_manager.catalog import load
from pokanop_manager.locks import prepare, Snapshot


def no_dependencies(root, item, target):
    pass


@pytest.fixture
def installation(tmp_path):
    root = tmp_path / "scripts café"
    root.mkdir()
    (root / "requirements").mkdir()
    (root / "requirements/pluck.txt").write_text("# no fixture dependencies\n")
    # Tiny self-contained legacy program exercises the actual framework backend.
    (root / "pluck").write_text('__version__ = "1.0.0"\ndef main():\n print("old")\n')
    bin_dir = tmp_path / "bin café"
    bin_dir.mkdir()
    return root, bin_dir


def snapshot(root, name, item, directory):
    # Generated repo-style source avoids needing the external runtime in fixture venvs.
    project = root / (name + "-project")
    project.mkdir(exist_ok=True)
    (project / "src").mkdir(exist_ok=True)
    (project / "src/demo.py").write_text('def main():\n print("working")\n')
    spec = {"schema_version": 1, "name": name, "version": "1.0.0", "description": "fixture",
            "entrypoint": "demo:main", "python": {"minimum": "3.11.0", "maximum_exclusive": "3.15.0"},
            "platforms": [{"os": "linux", "arch": "x86_64"}],
            "commands": [{"schema_version": 1, "name": "doctor", "help": "", "arguments": []}]}
    (project / "tool.json").write_text(json.dumps(spec))
    return prepare(root, name, {**item, "project": str(project)}, directory, builder=no_dependencies)


def setup_root(root):
    # Fixture builder uses projects under these names rather than source files.
    (root / "pluck").unlink()


def test_catalog_is_lazy_and_six_tools():
    assert list(load()) == ["medcat", "keyferry", "voxtract", "netsy", "pluck", "aikit"]
    assert "torch" not in sys.modules


def test_preview_has_no_side_effects(installation):
    root, bin_dir = installation
    before = sorted(str(p) for p in root.rglob("*"))
    plan = life.preview(root, bin_dir, ["pluck"])
    assert plan["preserved_legacy_venv"] == str(root / "venv")
    assert Path(plan["tools"][0]["requirements"]).parts[-2:] == ("requirements", "pluck.txt")
    assert sorted(str(p) for p in root.rglob("*")) == before


def test_real_install_update_rollback_uninstall(installation):
    root, bin_dir = installation
    setup_root(root)
    sentinel = root / "venv/user-state"
    sentinel.parent.mkdir()
    sentinel.write_text("keep")
    first = life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=snapshot)
    launcher = life.destination(bin_dir, "pluck")
    assert subprocess.check_output([str(launcher)], text=True).strip() == "working"
    first_runner = first["runners"]["pluck"]
    second = life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=snapshot)
    assert second["runners"]["pluck"] != first_runner
    life.rollback(root, bin_dir)
    assert life.marker(root)["runners"]["pluck"] == first_runner
    life.uninstall(root, bin_dir, ["pluck"])
    assert not launcher.exists()
    assert Path(first_runner[0]).exists()
    assert sentinel.read_text() == "keep"


@pytest.mark.parametrize("phase", ["locked", "staged", "wrapper", "commit"])
@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt])
def test_failure_rolls_back_without_deleting_state(installation, phase, failure):
    root, bin_dir = installation
    setup_root(root)
    old = {"version": 1, "tools": ["pluck"]}
    (root / life.MARKER).write_text(json.dumps(old))
    dest = life.destination(bin_dir, "pluck")
    dest.write_bytes(b"legacy")
    def fail(point):
        if point == phase:
            raise failure("injected")
    with pytest.raises(failure):
        life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "legacy",
                     prepare_tool=snapshot, checkpoint=fail)
    assert life.marker(root) == old
    assert dest.read_bytes() == b"legacy"
    assert list((root / ".scripts-state/transactions").iterdir())


def test_partial_batch_never_activates(installation):
    root, bin_dir = installation
    setup_root(root)
    from scriptkit.manager import Installer
    class FailSecond(Installer):
        def install(self, plan, **kwargs):
            if plan.installation.release.tool.name == "netsy":
                raise ValueError("second tool failed")
            return super().install(plan, **kwargs)
    with pytest.raises(ValueError, match="second"):
        life.install(root, bin_dir, ["pluck", "netsy"], legacy_wrapper=lambda _: "",
                     prepare_tool=snapshot, installer_type=FailSecond)
    assert not (root / life.MARKER).exists()
    assert not list(bin_dir.iterdir())


def test_foreign_wrapper_is_rejected_before_resolution(installation):
    root, bin_dir = installation
    life.destination(bin_dir, "pluck").write_bytes(b"foreign")
    def forbidden(*args):
        pytest.fail("must not resolve dependencies")
    with pytest.raises(ValueError, match="foreign"):
        life.install(root, bin_dir, ["pluck"], legacy_wrapper=lambda _: "", prepare_tool=forbidden)


def test_snapshot_tampering_rejected(installation, tmp_path):
    root, _ = installation
    setup_root(root)
    snap = snapshot(root, "pluck", load()["pluck"], tmp_path / "locked")
    plan = snap.plan()
    (snap.directory / "catalog.json").write_text("{}")
    with pytest.raises(ValueError, match="authorization"):
        snap.authorize(plan)
