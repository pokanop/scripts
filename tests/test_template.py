"""Smoke test for the new-tool scaffold so it never rots."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "templates" / "tool_template.py"


@pytest.mark.parametrize(
    "argv,needle",
    [
        (["--version"], "toolname 0.1.0"),
        (["--help"], "toolname"),
        (["hello", "--name", "Ada"], "hello, Ada!"),
        (["doctor"], "doctor"),
    ],
)
def test_template_commands(argv, needle):
    proc = subprocess.run(
        [sys.executable, str(TEMPLATE), *argv],
        capture_output=True, text=True, timeout=60, env={**os.environ, "NO_COLOR": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    assert needle in proc.stdout
