"""V1 routing and bare-Python dry-run remain usable through migration."""
import json
import subprocess
import sys
import venv
from pathlib import Path

from test_manager_migration import installation, snapshot
from pokanop_manager import lifecycle as life


def test_v1_migration_and_rollback_preserve_old_environment(installation, tool_loader):
    root, bin_dir = installation
    (root / "pluck").write_text('print("legacy")\n')
    venv.EnvBuilder(with_pip=False).create(root / "venv")
    sentinel = root / "venv/sentinel"
    sentinel.write_text("keep")
    old = {"version": 1, "tools": ["pluck", "netsy"], "install_dir": str(root), "bin_dir": str(bin_dir)}
    (root / life.MARKER).write_text(json.dumps(old))
    host = tool_loader("scripts")
    wrapper = lambda name: host.wrapper_content(name, root, bin_dir)
    path = life.destination(bin_dir, "pluck")
    path.write_bytes(wrapper("pluck").encode())
    path.chmod(0o755)
    other = life.destination(bin_dir, "netsy")
    other.write_bytes(b"unrelated")
    life.install(root, bin_dir, ["pluck"], legacy_wrapper=wrapper, prepare_tool=snapshot)
    assert subprocess.check_output([str(path)], text=True).strip() == "working"
    assert life.marker(root)["tools"] == ["netsy", "pluck"]
    life.rollback(root, bin_dir)
    assert subprocess.check_output([str(path)], text=True).strip() == "legacy"
    assert life.marker(root) == old
    assert sentinel.read_text() == "keep"
    assert other.read_bytes() == b"unrelated"


def test_bare_dry_run_creates_nothing(installation):
    root, bin_dir = installation
    before = sorted(str(p) for p in root.rglob("*"))
    script = Path(__file__).resolve().parents[1] / "scripts"
    result = subprocess.run([sys.executable, "-S", str(script), "migrate", "pluck", "--dry-run",
                             "--dir", str(root), "--bin-dir", str(bin_dir)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "requested_dependencies" in result.stdout
    assert before == sorted(str(p) for p in root.rglob("*"))
