"""Opt-in real six-tool lifecycle rehearsal; downloads large PyPI CUDA dependencies.

Run: python tests/rehearse_manager.py /path/to/empty/private/directory
Not a required CI job: the hermetic transaction tests run on every platform.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    from pokanop_manager.catalog import load
    from pokanop_manager.lifecycle import install, destination, marker, uninstall
    root = Path(sys.argv[1]).resolve()
    root.mkdir(exist_ok=False)
    shutil.copytree(ROOT / "requirements", root / "requirements")
    names = list(load())
    for name in names:
        shutil.copyfile(ROOT / name, root / name)
    sentinel = root / "venv/preserve-user-state"
    sentinel.parent.mkdir()
    sentinel.write_text("unchanged")
    value = install(root, root / "bin", names, legacy_wrapper=lambda _: "")
    for name in names:
        subprocess.run([str(destination(root / "bin", name)), "--help"], check=True)
    assert len({Path(cmd[0]).parent.parent for cmd in value["runners"].values()}) == 6
    assert sentinel.read_text() == "unchanged"
    evidence = {"tools": names, "receipts": value["receipts"], "runners": value["runners"],
                "isolation": "six distinct environments; old state retained"}
    (root / "evidence.json").write_text(json.dumps(evidence, indent=2))
    uninstall(root, root / "bin", ["pluck"])
    assert "pluck" not in marker(root)["tools"]
    assert "netsy" in marker(root)["tools"]
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
