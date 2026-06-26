#!/usr/bin/env python3
"""
toolname — One-line description  v0.1.0
A short paragraph describing what this tool does and why someone runs it.

This is the canonical scaffold for a new pokanop/scripts tool. To create one:

    cp templates/tool_template.py mytool        # extension-less, house style
    chmod +x mytool
    # then: replace "toolname"/"TOOLNAME", add subcommands, register in `scripts`

Everything visual or structural (color, icons, messages, tables, progress,
config, subprocess, prompts, error handling) comes from the shared `scriptkit`
library so the tool matches the rest of the toolkit for free.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make `scriptkit` importable regardless of where this file is invoked from:
# walk up from the file's real location to the toolkit root that holds it.
_here = Path(__file__).resolve().parent
for _base in (_here, *_here.parents):
    if (_base / "scriptkit" / "__init__.py").exists():
        sys.path.insert(0, str(_base))
        break

import scriptkit as sk

__version__ = "0.1.0"

# --- configuration ---------------------------------------------------------
# Three-tier config: defaults < ~/.toolname/config.json < TOOLNAME_* env vars.
CONFIG_DIR = Path(os.environ.get("TOOLNAME_CONFIG", Path.home() / ".toolname"))
CONFIG = sk.Config(
    CONFIG_DIR / "config.json",
    defaults={"greeting": "hello", "count": 1},
    env_prefix="TOOLNAME",
    coerce_env=True,
)


# --- commands --------------------------------------------------------------
def cmd_hello(args: argparse.Namespace) -> None:
    """Demonstrate messages, steps, config, and a tracked loop."""
    cfg = CONFIG.load()
    name = args.name or "world"
    greeting = sk.get_nested(cfg, "greeting", "hello")

    sk.header("Greeting")
    sk.info(f"loaded config from {CONFIG.path}")
    for i in sk.track(range(args.count), "Greeting"):
        sk.step(i + 1, args.count, f"{greeting}, {name}!")
    sk.success("done")


def cmd_doctor(args: argparse.Namespace) -> None:
    """Demonstrate a status table and dependency checks."""
    sk.table(
        [{"name": "Check"}, {"name": "Status"}, {"name": "Detail", "style": "dim"}],
        [
            ["python", "✅", sys.version.split()[0]],
            ["git", "✅" if sk.which("git") else "❌", "version control"],
        ],
        title="toolname doctor",
    )


def cmd_run(args: argparse.Namespace) -> None:
    """Demonstrate subprocess handling and CliError."""
    result = sk.run(["git", "rev-parse", "--show-toplevel"])
    if not result.ok:
        raise sk.CliError(f"not a git repo: {result.err}")
    sk.kv("repo root", result.out)


# --- CLI -------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toolname",
        description=f"toolname v{__version__} — one-line description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  toolname hello --name Ada\n"
            "  toolname doctor\n"
        ),
    )
    parser.add_argument("-v", "--version", action="version", version=f"toolname {__version__}")
    sub = parser.add_subparsers(dest="command")

    hello = sub.add_parser("hello", help="Print a greeting")
    hello.add_argument("--name", help="Who to greet")
    hello.add_argument("--count", type=int, default=1, help="How many times")

    sub.add_parser("doctor", help="Check the environment")
    sub.add_parser("run", help="Show the git repo root")
    return parser


HANDLERS = {"hello": cmd_hello, "doctor": cmd_doctor, "run": cmd_run}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return sk.dispatch(args, HANDLERS, parser)


if __name__ == "__main__":
    sys.exit(sk.run_cli(main))
