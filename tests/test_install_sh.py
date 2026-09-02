"""Regression tests for the shell installer entry points."""

import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "install.sh"


def _write_executable(path, content):
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _installer_env(tmp_path):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls"

    _write_executable(
        fake_bin / "git",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "{calls}"
install_dir="${{@: -1}}"
mkdir -p "$install_dir"
touch "$install_dir/scripts"
""",
    )
    _write_executable(
        fake_bin / "python",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'python %s\\n' "$*" >> "{calls}"
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "SCRIPTS_HOME": str(tmp_path / "install"),
            "SCRIPTS_BIN": str(tmp_path / "bin"),
            "SCRIPTS_PYTHON": str(fake_bin / "python"),
            "SCRIPTS_REPO_URL": "https://example.test/pokanop/scripts.git",
        }
    )
    return env, calls


def test_piped_installer_clones_without_bash_source(tmp_path):
    env, calls = _installer_env(tmp_path)

    result = subprocess.run(
        ["bash", "-u"],
        cwd=tmp_path,
        env=env,
        input=INSTALLER.read_text(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "unbound variable" not in result.stderr
    assert calls.read_text().splitlines() == [
        f"clone --depth 1 --branch main https://example.test/pokanop/scripts.git {tmp_path / 'install'}",
        f"python {tmp_path / 'install' / 'scripts'} install --dir {tmp_path / 'install'} --bin-dir {tmp_path / 'bin'} --no-pull",
    ]


def test_local_installer_uses_checkout_without_cloning(tmp_path):
    env, calls = _installer_env(tmp_path)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".git").mkdir()
    (checkout / "requirements").mkdir()
    (checkout / "scripts").touch()
    local_installer = checkout / "install.sh"
    local_installer.write_text(INSTALLER.read_text())

    result = subprocess.run(
        ["bash", "-u", str(local_installer)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "unbound variable" not in result.stderr
    assert calls.read_text().splitlines() == [
        f"python {checkout / 'scripts'} install --dir {checkout} --bin-dir {tmp_path / 'bin'}"
    ]
