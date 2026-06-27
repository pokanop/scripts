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
        (["doctor"], "System"),       # the shared doctor report leads with System
        ([], "usage:"),               # bare invocation → banner-led help, exit 0
    ],
)
def test_template_commands(argv, needle):
    proc = subprocess.run(
        [sys.executable, str(TEMPLATE), *argv],
        capture_output=True, text=True, timeout=60, env={**os.environ, "NO_COLOR": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    assert needle in proc.stdout


def test_template_banner_on_subcommand_goes_to_stderr():
    """A subcommand prints the identity banner to stderr, never to stdout."""
    proc = subprocess.run(
        [sys.executable, str(TEMPLATE), "doctor"],
        capture_output=True, text=True, timeout=60, env={**os.environ, "NO_COLOR": "1"},
    )
    assert "toolname v0.1.0" in proc.stderr
    assert "toolname v0.1.0" not in proc.stdout
