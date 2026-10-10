"""Multi-tool migration boundary: stage privately, then publish one routing marker.

ScriptKit manages each tool's environments, receipts, validation and smoke tests.
This adapter only coordinates the legacy public-wrapper/marker handoff. No old
venv or user configuration is modified or removed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import sys
import uuid
from pathlib import Path

from .catalog import load, read_json

MARKER = ".scripts-install.json"
DISPATCH = '''import json, os, subprocess, sys
from pathlib import Path
root, name = Path(sys.argv[1]), sys.argv[2]
try:
    marker = json.loads((root / ".scripts-install.json").read_text(encoding="utf-8"))
    if name not in marker.get("tools", []):
        raise ValueError("tool is not installed")
    command = marker.get("runners", {}).get(name)
    if command is None:
        python = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        command = [str(python), str(root / name)]
    args = [*command, *sys.argv[3:]]
    if os.name == "nt":
        sys.exit(subprocess.call(args))
    os.execv(command[0], args)
except (OSError, ValueError, KeyError) as exc:
    print("scripts: " + str(exc), file=sys.stderr)
    sys.exit(1)
'''


def marker(root: Path) -> dict:
    path = root / MARKER
    value = read_json(path) if path.exists() else {"version": 1, "tools": []}
    if value.get("version") not in (1, 2) or not isinstance(value.get("tools"), list):
        raise ValueError("unsupported installation marker")
    return value


def wrapper(root: Path, name: str) -> bytes:
    python = str(Path(getattr(sys, "_base_executable", sys.executable)).resolve())
    dispatcher = str(root / ".scripts-state/dispatch.py")
    if os.name == "nt":
        for part in (python, dispatcher, str(root), name):
            if any(c in part for c in '%!"\r\n'):
                raise ValueError("unsafe Windows launcher path")
        from scriptkit.bootstrap import cmd_launcher
        return cmd_launcher(python, root / ".scripts-state/launch" / (name + ".py"), utf8=True).encode()
    args = " ".join(shlex.quote(s) for s in (python, "-I", dispatcher, str(root), name))
    return f'#!/bin/sh\nexec {args} "$@"\n'.encode()


def legacy_wrapper_bytes(content: str) -> list[bytes]:
    """Recognize exact legacy output, including Windows text-mode translation."""
    allowed = [content.encode()]
    if os.name == "nt":
        # V1 wrote already-CRLF text through write_text's newline translation.
        allowed.append(content.replace("\r\n", "\r\r\n").encode())
    return allowed


def destination(bin_dir: Path, name: str) -> Path:
    return bin_dir / (name + (".cmd" if os.name == "nt" else ""))


def check_paths(root: Path, bin_dir: Path) -> None:
    for path in (root / ".scripts-state", root / MARKER, bin_dir):
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError("symlink installation state or bin directory")


def requested_dependencies(path: Path, seen=None) -> list[str]:
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen:
        return []
    seen.add(path)
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r ", "-c ")):
            lines.extend(requested_dependencies(path.parent / line[3:].strip(), seen))
        else:
            lines.append(line)
    return lines


def preview(root: Path, bin_dir: Path, names: list[str]) -> dict:
    tools = load(root)
    old = marker(root)
    return {"operation": "stage, validate all, atomically activate",
            "marker": str(root / MARKER), "bin_dir": str(bin_dir),
            "preserved_legacy_venv": str(root / "venv"),
            "preserved_tools": sorted(set(old["tools"]) - set(names)),
            "tools": [{"name": name, "requirements": str(Path(tools[name].get("project", root)) / tools[name]["requirements"]),
                       "requested_dependencies": requested_dependencies(Path(tools[name].get("project", root)) / tools[name]["requirements"]),
                       "generation_root": str(root / ".scripts-state/transactions/<new>/tools" / name),
                       "wrapper": str(destination(bin_dir, name))} for name in names],
            "dependency_resolution": "pip wheel against https://pypi.org/simple; complete hashed wheel locks before staging; Linux Torch uses PyPI CUDA wheels",
            "failure": "old marker stays selected; environments and user state retained"}


def install(root: Path, bin_dir: Path, names: list[str], *, legacy_wrapper,
            prepare_tool=None, installer_type=None, checkpoint=lambda phase: None) -> dict:
    from scriptkit.manager import Installer, storage
    from .locks import POLICY, prepare
    prepare_tool = prepare_tool or prepare
    installer_type = installer_type or Installer
    check_paths(root, bin_dir)
    root, bin_dir = root.resolve(), bin_dir.resolve()
    check_paths(root, bin_dir)
    tools = load(root)
    if len(set(names)) != len(names) or any(n not in tools for n in names):
        raise ValueError("unknown or duplicate tool selection")
    state = root / ".scripts-state"
    with storage.locked(state):
        old = marker(root)
        # Ownership is checked before resolution/build/staging, for the entire selection.
        for name in names:
            path = destination(bin_dir, name)
            allowed = [wrapper(root, name)]
            if name in old["tools"]:
                allowed.extend(legacy_wrapper_bytes(legacy_wrapper(name)))
            if path.is_symlink() or (path.exists() and path.read_bytes() not in allowed):
                raise ValueError(f"refusing foreign or edited wrapper: {path}")
        windows_loaders = {}
        if os.name == "nt":
            for name in names:
                loader = state / "launch" / (name + ".py")
                content = ("import runpy, sys\n" + f"sys.argv[1:1] = {[str(root), name]!r}\n"
                           + f"runpy.run_path({str(state / 'dispatch.py')!r}, run_name='__main__')\n").encode()
                if loader.is_symlink() or (loader.exists() and loader.read_bytes() != content):
                    raise ValueError("refusing edited Windows loader")
                windows_loaders[loader] = content
        dispatcher = state / "dispatch.py"
        if dispatcher.is_symlink() or (dispatcher.exists() and dispatcher.read_bytes() != DISPATCH.encode()):
            raise ValueError("refusing edited dispatcher")
        transaction = state / "transactions" / ("t" + uuid.uuid4().hex)
        transaction.mkdir(parents=True)
        storage.publish(transaction / "before.json", old)
        snapshots = {name: prepare_tool(root, name, tools[name], transaction / "locks" / name) for name in names}
        checkpoint("locked")
        runners = dict(old.get("runners", {}))
        receipts = dict(old.get("receipts", {}))
        for name, source in snapshots.items():
            manager = installer_type(transaction / "tools", transaction / "bin", source, policy=POLICY)
            receipt = manager.install(source.plan())
            generation = receipt.parent
            py = generation / "env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            runners[name] = [str(py), "-I", "-B", str(generation / "run.py")]
            receipts[name] = str(receipt)
        checkpoint("staged")
        # Wrapper replacement before marker commit is safe even after process death:
        # the dispatcher understands v1 and the previous v2 marker.
        bin_dir.mkdir(parents=True, exist_ok=True)
        if not dispatcher.exists():
            dispatcher.write_bytes(DISPATCH.encode())
        for loader, content in windows_loaders.items():
            loader.parent.mkdir(exist_ok=True)
            if not loader.exists():
                with loader.open("xb") as stream:
                    stream.write(content)
        backups = {}
        value = None
        try:
            for name in names:
                path = destination(bin_dir, name)
                allowed = [wrapper(root, name)]
                if name in old["tools"]:
                    allowed.extend(legacy_wrapper_bytes(legacy_wrapper(name)))
                if path.is_symlink() or (path.exists() and path.read_bytes() not in allowed):
                    raise ValueError(f"wrapper changed while staging: {path}")
                backups[path] = path.read_bytes() if path.exists() else None
                temp = path.with_name(path.name + "." + transaction.name)
                with temp.open("xb") as f:
                    f.write(wrapper(root, name)); f.flush(); os.fsync(f.fileno())
                temp.chmod(0o755)
                os.replace(temp, path)
                checkpoint("wrapper")
            value = {**old, "version": 2, "install_dir": str(root), "bin_dir": str(bin_dir),
                     "tools": sorted(set(old["tools"]) | set(names)), "runners": runners,
                     "receipts": receipts, "previous_marker": str(transaction / "before.json"),
                     "previous_marker_sha256": hashlib.sha256((transaction / "before.json").read_bytes()).hexdigest()}
            checkpoint("commit")
            storage.publish(root / MARKER, value)
        except BaseException:
            # Publication may have committed immediately before interruption.
            # Universal wrappers can route either marker; never restore legacy
            # wrappers after the new marker became visible.
            try:
                committed = value is not None and marker(root) == value
            except (OSError, ValueError):
                committed = True
            if committed:
                raise
            for path, content in backups.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)
            raise
        return value


def rollback(root: Path, bin_dir: Path) -> None:
    from scriptkit.manager import Installer, storage
    check_paths(root, bin_dir)
    with storage.locked(root / ".scripts-state"):
        current = marker(root)
        path = Path(current.get("previous_marker", ""))
        if not path.is_relative_to(root / ".scripts-state/transactions") or not path.is_file():
            raise ValueError("no previous migration snapshot")
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != current.get("previous_marker_sha256"):
            raise ValueError("previous marker modified")
        old = read_json(path)
        # Manager receipts retain immutable generations; verify before restoring routing.
        for receipt in old.get("receipts", {}).values():
            receipt = Path(receipt)
            Installer(receipt.parent.parent.parent.parent, root / ".scripts-state/unused-bin", None)._verify_generation(receipt.parent.parent.parent, receipt.parent.name)
        storage.publish(root / MARKER, old)
        for name in set(current["tools"]) - set(old["tools"]):
            dest = destination(bin_dir, name)
            if dest.exists() and dest.read_bytes() == wrapper(root, name):
                dest.unlink()


def uninstall(root: Path, bin_dir: Path, names: list[str], *, legacy_wrapper=None) -> None:
    from scriptkit.manager import storage
    check_paths(root, bin_dir)
    with storage.locked(root / ".scripts-state"):
        old = marker(root)
        for name in names:
            dest = destination(bin_dir, name)
            allowed = [wrapper(root, name)]
            if legacy_wrapper and name in old["tools"] and name not in old.get("runners", {}):
                allowed.extend(legacy_wrapper_bytes(legacy_wrapper(name)))
            if dest.is_symlink() or (dest.exists() and dest.read_bytes() not in allowed):
                raise ValueError(f"refusing foreign wrapper: {dest}")
        value = {**old, "tools": sorted(set(old["tools"]) - set(names)),
                 "runners": {k: v for k, v in old.get("runners", {}).items() if k not in names},
                 "receipts": {k: v for k, v in old.get("receipts", {}).items() if k not in names}}
        if set(names) & set(old["tools"]):
            # A pre-install snapshot may refer to wrappers removed by uninstall.
            # Do not advertise rollback to a routing table we can no longer serve.
            value.pop("previous_marker", None)
            value.pop("previous_marker_sha256", None)
        storage.publish(root / MARKER, value)
        for name in names:
            destination(bin_dir, name).unlink(missing_ok=True)
