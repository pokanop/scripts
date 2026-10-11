"""Native batch uninstall regressions, including legacy and managed launchers."""

import os
from pathlib import Path
import shutil
import subprocess
import time
import venv

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires cmd.exe and Windows file locking")


def wait_cleanup(output):
    log = Path(next(line.removeprefix("Cleanup log: ") for line in output.splitlines()
                    if line.startswith("Cleanup log: ")))
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        text = log.read_text()
        if "Cleanup finished" in text:
            assert "Retained:" not in text, text
            log.unlink()
            return text
        time.sleep(0.1)
    pytest.fail(f"cleanup did not finish: {log.read_text()}")


@pytest.fixture
def installed_host(tool_loader, tmp_path):
    host = tool_loader("scripts")
    root = tmp_path / "install with spaces"
    root.mkdir()
    source = Path(host.__file__).resolve().parent
    shutil.copy2(source / "scripts", root / "scripts")
    shutil.copytree(source / "pokanop_manager", root / "pokanop_manager")
    venv.EnvBuilder(with_pip=False).create(root / "venv")
    bindir = tmp_path / "bin with spaces"
    host.install_wrappers(root, bindir, [])
    return host, root, bindir


@pytest.mark.parametrize("status", [0, 7])
@pytest.mark.parametrize("restore_marker", [False, True])
def test_deferred_self_deletion_preserves_status(installed_host, status, restore_marker):
    host, root, bindir = installed_host
    wrapper = bindir / "scripts.cmd"
    state = root / ".scripts-state"
    state.mkdir()
    (state / "sentinel").write_text("keep")
    (root / "scripts").write_text(
        "from pathlib import Path\nimport sys\n"
        "from pokanop_manager.windows_cleanup import defer_cleanup\n"
        "root = Path(sys.prefix).parent\n"
        "marker = root / '.scripts-install.json'\n"
        "defer_cleanup([Path(sys.argv[1]), root / 'venv', root / '.scripts-state'], marker)\n"
        f"if {restore_marker}: marker.write_text('reinstalled')\n"
        f"sys.exit({status})\n"
    )
    result = subprocess.run(
        f'"{wrapper}" "{wrapper}"', shell=True, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode == status, output
    assert "batch file cannot be found" not in output.lower()
    log = wait_cleanup(output)
    assert wrapper.exists() == restore_marker
    assert (root / "venv").exists() == restore_marker
    assert state.exists() == restore_marker
    if restore_marker:
        assert "Cleanup skipped: installation marker exists" in log
        assert (root / ".scripts-install.json").read_text() == "reinstalled"
        assert (state / "sentinel").read_text() == "keep"
        assert host.venv_python(root).exists()


@pytest.mark.parametrize("managed_wrapper", [False, True])
def test_full_uninstall_through_public_wrapper(installed_host, tmp_path, managed_wrapper, monkeypatch):
    host, root, bindir = installed_host
    (root / "pluck").write_text("# retained source\n")
    host.install_wrappers(root, bindir, ["pluck"])
    if managed_wrapper:
        from pokanop_manager import lifecycle
        (bindir / "scripts.cmd").unlink()
        with monkeypatch.context() as patch:
            patch.setattr(lifecycle, "install", lambda *a, **k: None)
            patch.setattr(host.sys, "executable", str(host.venv_python(root)))
            host.managed_install(root, bindir, [])
    host.write_marker(root, bindir, ["pluck"])
    home = tmp_path / "home"
    home.mkdir()
    config = home / ".pluck"
    config.mkdir()
    (config / "config.json").write_text("{}")
    result = subprocess.run(
        f'"{bindir / "scripts.cmd"}" uninstall -y --keep-path '
        f'--dir "{root}" --bin-dir "{bindir}"',
        shell=True, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "HOME": str(home), "USERPROFILE": str(home), "PYTHONUTF8": "1"},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "batch file cannot be found" not in output.lower()
    wait_cleanup(output)
    assert not list(bindir.iterdir())
    assert not (root / ".scripts-install.json").exists()
    assert not (root / "venv").exists()
    assert (root / "scripts").exists()
    assert (config / "config.json").read_text() == "{}"
    assert "Cleanup scheduled" in output
