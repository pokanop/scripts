"""Networked clean-venv migration/rollback acceptance test (run directly).

Builds the real pre-extraction wheel from a pinned git commit, never a mock.
No existing environment, user config or wrapper is touched.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LEGACY = "458104a52bafe619a259ed2b83ecd7a3b29c82c1"


def run(*args: object, cwd: Path, env: dict[str, str]) -> None:
    command = [str(a) for a in args]
    if Path(command[0]).name.lower().startswith("python"):
        command[1:1] = ["-X", "utf8"]
    subprocess.run(command, cwd=cwd, env=env, check=True)


def python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="scripts-migration-") as directory:
        work = Path(directory)
        env = {**os.environ, "HOME": str(work / "home"), "USERPROFILE": str(work / "home"),
               "NO_COLOR": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PYTHONUTF8": "1"}
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        Path(env["HOME"]).mkdir()
        old = work / "old"
        old.mkdir()
        archive = work / "old.zip"
        run("git", "archive", "--format=zip", f"--output={archive}", LEGACY, cwd=ROOT, env=env)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(old)
        wheels = work / "wheels"
        for source in (old, ROOT):
            run(sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", wheels, source, cwd=work, env=env)
        legacy_wheel = next(wheels.glob("pokanop_scripts-1.0.0-*.whl"))
        new_wheel = next(wheels.glob("pokanop_scripts-1.1.0-*.whl"))
        with zipfile.ZipFile(new_wheel) as zipped:
            assert not any(n.startswith("scriptkit/") for n in zipped.namelist())

        install = work / "install"
        shutil.copytree(ROOT, install, ignore=shutil.ignore_patterns(
            ".git", "venv", ".venv", "__pycache__", ".pytest_cache", "*.egg-info", "build", "dist"))
        assert not (install / "scriptkit").exists()
        bindir = work / "bin"
        config = Path(env["HOME"]) / ".pluck" / "config.json"
        config.parent.mkdir()
        config.write_text('{"preserve": "user-config"}\n')
        initial_config = config.read_bytes()
        # System Python with -S cannot import the external runtime: exercise fallback.
        common = ["--dir", install, "--bin-dir", bindir, "--no-path", "--no-pull"]
        run(sys.executable, "-S", install / "scripts", "install", *common, cwd=work, env=env)
        py = python(install / "venv")
        # Both platform bootstrap entry points delegate to the same installer.
        bootstrap_env = {**env, "SCRIPTS_PYTHON": sys.executable}
        if os.name == "nt":
            run("pwsh", "-NoProfile", "-File", install / "install.ps1", "-Dir", install,
                "-BinDir", bindir, "-NoPath", cwd=work, env=bootstrap_env)
        else:
            run("bash", install / "install.sh", "--dir", install,
                "--bin-dir", bindir, "--no-path", cwd=work, env=bootstrap_env)
        failure_dir = work / "failed-install"
        failure_dir.mkdir()
        (failure_dir / "scripts").write_text("raise SystemExit(23)\n")
        if os.name == "nt":
            command = ["pwsh", "-NoProfile", "-File", str(install / "install.ps1"),
                       "-Dir", str(failure_dir), "-BinDir", str(bindir), "-NoPath"]
        else:
            command = ["bash", str(install / "install.sh"), "--dir", str(failure_dir),
                       "--bin-dir", str(bindir), "--no-path"]
        failed = subprocess.run(command, cwd=work, env=bootstrap_env, capture_output=True, text=True)
        assert failed.returncode != 0, "bootstrap swallowed installer failure"
        run(py, "-I", "-c", "import scriptkit; assert scriptkit.__version__ == '1.3.0'", cwd=work, env=env)
        # Per-tool, update and published consumer-wheel install paths.
        run(sys.executable, "-S", install / "scripts", "install", "pluck", *common, cwd=work, env=env)
        wrapper = bindir / ("pluck.cmd" if os.name == "nt" else "pluck")
        original_wrapper = wrapper.read_bytes()
        run(wrapper, "--help", cwd=work, env=env)
        run(sys.executable, "-S", install / "scripts", "update", "pluck",
            "--dir", install, "--bin-dir", bindir, cwd=work, env=env)
        run(py, "-m", "pip", "install", new_wheel, cwd=work, env=env)
        run(py, "-m", "pip", "check", cwd=work, env=env)
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
        pin = next(r for r in metadata["project"]["dependencies"] if " @ " in r)
        bad_hash = pin.split("#sha256=")[0] + "#sha256=" + "0" * 64
        for requirements, expected in [([bad_hash], "HASHES"),
                                       ([pin, "pokanop-scriptkit>=1.4,<2"], "ResolutionImpossible")]:
            rejected = subprocess.run([str(py), "-m", "pip", "install", "--dry-run",
                                       "--ignore-installed", "--no-deps", *requirements],
                                      cwd=work, env=env, capture_output=True, text=True)
            assert rejected.returncode != 0, rejected.stdout
            assert expected in rejected.stdout + rejected.stderr, rejected.stderr

        # Deliberately recreate the historical overlapping ownership. The supported
        # installer must uninstall the old owner first, then restore runtime files.
        run(py, "-m", "pip", "install", "--no-deps", "--force-reinstall", legacy_wheel, cwd=work, env=env)
        run(sys.executable, "-S", install / "scripts", "install", *common, cwd=work, env=env)
        run(py, "-I", "-c", "from importlib.metadata import distributions; "
            "assert 'pokanop-scripts' not in [d.metadata['Name'] for d in distributions()]; "
            "import scriptkit; assert scriptkit.__version__ == '1.3.0'", cwd=work, env=env)

        # Interruption after uninstall: the runtime metadata survives, its files do
        # not. A second bare-Python repair must not trust that stale metadata.
        run(py, "-m", "pip", "install", "--no-deps", legacy_wheel, cwd=work, env=env)
        run(py, "-m", "pip", "uninstall", "-y", "pokanop-scripts", cwd=work, env=env)
        run(sys.executable, "-S", install / "scripts", "install", *common, cwd=work, env=env)
        run(py, "-I", install / "pluck", "--help", cwd=work, env=env)
        assert config.read_bytes() == initial_config
        assert wrapper.read_bytes() == original_wrapper

        # Old editable ownership uses a finder instead of listing runtime files.
        run(py, "-m", "pip", "install", "--no-deps", "-e", old, cwd=work, env=env)
        run(sys.executable, "-S", install / "scripts", "install", *common, cwd=work, env=env)
        run(py, "-I", "-c", "import scriptkit; from pathlib import Path; "
            f"assert not Path(scriptkit.__file__).is_relative_to({str(old)!r})", cwd=work, env=env)

        # Roll back BOTH ownership and source without changing install/bin paths.
        run(py, "-m", "pip", "uninstall", "-y", "pokanop-scriptkit", "pokanop-scripts", cwd=work, env=env)
        shutil.copytree(old, install, dirs_exist_ok=True)
        run(py, "-m", "pip", "install", "--no-deps", legacy_wheel, cwd=work, env=env)
        run(py, "-I", "-c", "import scriptkit; from importlib.metadata import version; "
            "assert version('pokanop-scripts') == '1.0.0'", cwd=work, env=env)
        run(wrapper, "--help", cwd=work, env=env)
        assert config.read_bytes() == initial_config
        assert wrapper.read_bytes() == original_wrapper
        assert (install / ".scripts-install.json").exists()
        print("PASS: fresh/harness/per-tool/update/wheel/legacy/interruption/rollback; configs and wrappers preserved")


if __name__ == "__main__":
    main()
