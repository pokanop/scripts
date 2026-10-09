"""Pip is the resolver/builder; ScriptKit owns lock validation and installation.

Resolution is an explicit preparation step. Every resulting wheel and legacy
bundle is frozen in a content-addressed snapshot before any environment is staged.
"""
from __future__ import annotations

import hashlib
import io
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

from scriptkit.contracts import (Artifact, CatalogRelease, CommandSpec, DependencyLock,
                                LockedPackage, Platform, PythonRequirement, ToolRelease, ToolSpec)
from scriptkit.contracts.catalog import InstallPlan, Registry, ResolvedPlan
from scriptkit.contracts.artifacts import ArtifactPolicy

POLICY = ArtifactPolicy(max_archive_bytes=2 * 1024**3, max_expanded_bytes=8 * 1024**3,
                        max_entries=100000, command_timeout=3600,
                        member_name_grammar="permissive-wheel")
ORIGIN = "https://github.com/pokanop/scripts/"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def host() -> Platform:
    return Platform({"Linux": "linux", "Darwin": "macos", "Windows": "windows"}[platform.system()],
                    {"amd64": "x86_64", "x86_64": "x86_64", "aarch64": "arm64", "arm64": "arm64"}[platform.machine().lower()])


def bundle(root: Path, name: str, item: dict) -> tuple[ToolSpec, bytes]:
    python = PythonRequirement("3.11.0", "3.15.0")
    if "project" in item:
        project = Path(item["project"])
        spec = ToolSpec.from_json((project / "tool.json").read_text(encoding="utf-8"))
        files = {p.relative_to(project / "src").as_posix(): p.read_bytes()
                 for p in (project / "src").rglob("*.py")}
    else:
        source = (root / name).read_bytes()
        version = re.search(rb'__version__\s*=\s*"([^"]+)"', source)
        if version is None:
            raise ValueError(f"missing version: {name}")
        module = name.replace("-", "_")
        spec = ToolSpec(1, name, version[1].decode(), item["description"], "pokanop_entry:main",
                        python, (host(),), (CommandSpec(1, "doctor", "Check prerequisites", ()),))
        files = {module + ".py": source, "pokanop_entry.py": (
            "import sys\n"
            "sys.stdout.reconfigure(encoding='utf-8')\n"
            "sys.stderr.reconfigure(encoding='utf-8')\n"
            f"from {module} import main as tool_main\n"
            "from scriptkit import run_cli\n"
            "def main():\n    return run_cli(tool_main)\n").encode()}
    if spec.name != name:
        raise ValueError("registered name differs from tool spec")
    # A release snapshot targets the executing interpreter/host only.
    spec = ToolSpec.from_dict({**spec.to_dict(), "platforms": [host().to_dict()]})
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as z:
        for path, data in sorted(files.items()):
            z.writestr(zipfile.ZipInfo(path, (2020, 1, 1, 0, 0, 0)), data)
    return spec, raw.getvalue()


def build_wheels(root: Path, item: dict, target: Path) -> None:
    project = Path(item.get("project", root))
    command = [sys.executable, "-m", "pip", "--isolated", "wheel", "--index-url",
               "https://pypi.org/simple", "--wheel-dir", str(target),
               "-c", str(root / "requirements/runtime-constraints.txt"),
               "-r", str(project / item["requirements"])]
    subprocess.run(command, check=True, timeout=3600)


def prepare(root: Path, name: str, item: dict, directory: Path, *, builder=build_wheels) -> "Snapshot":
    spec, raw = bundle(root, name, item)
    directory.mkdir(parents=True, exist_ok=False)
    artifact = directory / (name + ".scripts.zip")
    artifact.write_bytes(raw)
    wheel_dir = directory / "build"
    wheel_dir.mkdir()
    builder(root, item, wheel_dir)
    packages = []
    for wheel in sorted(wheel_dir.glob("*.whl")):
        with zipfile.ZipFile(wheel) as z:
            names = [p for p in z.namelist() if re.fullmatch(r"[^/]+\.dist-info/METADATA", p)]
            if len(names) != 1:
                raise ValueError("wheel must declare exactly one top-level identity")
            meta = BytesParser().parsebytes(z.read(names[0]))
        art = Artifact(wheel.name, digest(wheel), wheel.stat().st_size)
        packages.append(LockedPackage(re.sub(r"[-_.]+", "-", meta["Name"]).lower(), meta["Version"], art))
        wheel.rename(directory / art.sha256)
    wheel_dir.rmdir()
    art = Artifact(artifact.name, digest(artifact), artifact.stat().st_size)
    artifact.rename(directory / art.sha256)
    lock = DependencyLock(1, host(), spec.python, "pip", tuple(packages))
    catalog = CatalogRelease(1, "pokanop", "1.0.0", (ToolRelease(spec, art, (lock,)),))
    # Round-trip strict framework contracts before publishing the immutable snapshot.
    catalog = CatalogRelease.from_json(catalog.canonical_json())
    (directory / "catalog.json").write_text(catalog.canonical_json(), encoding="utf-8")
    (directory / "requirements.lock").write_text("\n".join(
        f"{p.name}=={p.version} --hash=sha256:{p.artifact.sha256}" for p in packages) + "\n", encoding="utf-8")
    return Snapshot(directory, digest(directory / "catalog.json"))


class Snapshot:
    """Pinned local InstallationSource, not a second package resolver."""
    def __init__(self, directory: Path, expected: str):
        self.directory = directory
        if digest(directory / "catalog.json") != expected:
            raise ValueError("catalog digest mismatch")
        self.catalog = CatalogRelease.from_json((directory / "catalog.json").read_text(encoding="utf-8"))
        self.registry = Registry(1, "pokanop", ORIGIN,
                                 Artifact("catalog.json", expected, (directory / "catalog.json").stat().st_size),
                                 4102444800)

    def plan(self, generation: str = "g1") -> ResolvedPlan:
        release = self.catalog.releases[0]
        locks = release.locks
        plan = InstallPlan(1, generation, None, self.registry.catalog.sha256, release,
                           host(), platform.python_version(), ("pip",), release.tool.name)
        return ResolvedPlan(1, self.registry, plan, "legacy-scripts",
                            tuple(hashlib.sha256(x.canonical_json().encode()).hexdigest() for x in locks),
                            (release.artifact, *(p.artifact for lock in locks for p in lock.packages)))

    def authorize(self, plan: ResolvedPlan) -> None:
        if (digest(self.directory / "catalog.json") != self.registry.catalog.sha256
                or plan != self.plan(plan.installation.generation)):
            raise ValueError("snapshot authorization changed")

    def fetch_into(self, artifact: Artifact, destination: Path) -> None:
        if artifact not in self.plan().artifacts:
            raise ValueError("artifact not in pinned snapshot")
        source = self.directory / artifact.sha256
        if source.is_symlink():
            raise ValueError("symlink snapshot artifact")
        # Installer independently streams hashes/size and validates its private copy.
        with source.open("rb") as src, destination.open("xb") as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)

    def fetch(self, artifact: Artifact) -> bytes:
        raise ValueError("use the framework streaming InstallationSource interface")
