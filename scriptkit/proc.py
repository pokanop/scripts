"""Subprocess helpers with a uniform result and graceful failure modes.

``run()`` never raises for a non-zero exit (unless ``check=True``); it always
returns a :class:`Result`, folding timeouts / missing binaries into a code and
an ``err`` string. This is the shape every tool's CLI-coordination code wants.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from .cli import CliError


@dataclass(frozen=True)
class Result:
    """Outcome of a command: exit ``code`` plus captured ``out``/``err``."""

    code: int
    out: str
    err: str

    @property
    def ok(self) -> bool:
        return self.code == 0

    def __bool__(self) -> bool:  # truthy when the command succeeded
        return self.ok


def run(
    cmd,
    *,
    timeout: float | None = 300,
    input: str | None = None,
    shell: bool = False,
    cwd=None,
    env=None,
    check: bool = False,
) -> Result:
    """Run ``cmd`` and capture output, returning a :class:`Result`.

    Timeouts return code ``-1``; a missing binary returns ``-127``. With
    ``check=True`` a non-zero exit raises :class:`CliError` with stderr.
    """
    try:
        proc = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input,
            cwd=cwd,
            env=env,
        )
        result = Result(proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip())
    except subprocess.TimeoutExpired:
        result = Result(-1, "", f"timed out after {timeout}s")
    except FileNotFoundError:
        binary = cmd if isinstance(cmd, str) else (cmd[0] if cmd else "")
        result = Result(-127, "", f"command not found: {binary}")
    except Exception as exc:  # noqa: BLE001 - surface as a result, not a crash
        result = Result(-1, "", str(exc))

    if check and not result.ok:
        shown = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
        detail = result.err or result.out or f"exit {result.code}"
        raise CliError(f"command failed: {shown}\n{detail}")
    return result


def which(binary: str) -> bool:
    """True if ``binary`` is found on ``PATH``."""
    return shutil.which(binary) is not None


def require(binary: str, hint: str | None = None) -> None:
    """Raise :class:`CliError` if ``binary`` is not installed."""
    if not which(binary):
        msg = f"required command not found: {binary}"
        if hint:
            msg += f" — {hint}"
        raise CliError(msg)
