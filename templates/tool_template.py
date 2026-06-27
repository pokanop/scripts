#!/usr/bin/env python3
"""
toolname — One-line description  v0.1.0
A short paragraph describing what this tool does and why someone runs it.

This is the canonical scaffold for a new pokanop/scripts tool. To create one:

    cp templates/tool_template.py mytool        # extension-less, house style
    chmod +x mytool
    # then: replace "toolname"/"TOOLNAME", add subcommands, register in `scripts`

Everything visual or structural (color, icons, messages, tables, progress,
config, subprocess, prompts, the doctor report, the run/dispatch lifecycle, and
error handling) comes from the shared `scriptkit` library so the tool matches
the rest of the toolkit for free.
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

# Brand identity — one house style for --help, --version, and runtime banners.
# Pick a distinct emoji; keep the tagline short. See docs/scriptkit.md.
ICON = "🧰"
TAGLINE = "one-line description"

# A bare invocation (no subcommand) runs this command after showing the banner.
# Set to None to show banner-led help instead (the right choice for tools that
# mutate state — don't make an implicit action destructive).
DEFAULT_COMMAND = None


# --- errors ----------------------------------------------------------------
# Subclass CliError so `run_cli` prints "❌ message" and exits 1 — no traceback,
# no per-command try/except. Raise it for any expected, user-facing failure.
class ToolnameError(sk.CliError):
    """A clean, user-facing error for toolname."""


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


def cmd_doctor(args: argparse.Namespace) -> int:
    """The shared diagnostic report — identical look across every tool.

    Build a list of checks per section; `sk.doctor` auto-adds a System section,
    rolls up issues, prints tips, and returns 1 if any required check FAILs.
    """
    return sk.doctor(
        "toolname", __version__, TAGLINE, ICON,
        sections={
            "Tools": [
                sk.check_binary("git", hint="install git"),
                sk.check_binary("ffmpeg", required=False, hint="brew install ffmpeg"),
            ],
            "Python packages": [
                sk.check_python("rich", required=False, hint="pip install rich"),
            ],
            "Config": [
                sk.Check.ok("Config file", str(CONFIG.path)) if CONFIG.path.exists()
                else sk.Check.warn("Config file", "not found", "run: toolname hello"),
            ],
        },
        tips=["Run `toolname hello --name Ada` to try it out"],
    )


def cmd_run(args: argparse.Namespace) -> None:
    """Demonstrate subprocess handling and the tool's error type."""
    result = sk.run(["git", "rev-parse", "--show-toplevel"])
    if not result.ok:
        raise ToolnameError(f"not a git repo: {result.err}")
    sk.kv("repo root", result.out)


# --- CLI -------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    # sk.make_parser gives the house identity line, a -v/--version flag, and an
    # aligned Examples: epilog — the same first impression as every other tool.
    parser = sk.make_parser(
        "toolname", __version__, TAGLINE, icon=ICON,
        examples=[
            ("toolname hello --name Ada", "print a greeting"),
            ("toolname doctor", "check the environment"),
        ],
    )
    sub = parser.add_subparsers(dest="command")

    hello = sub.add_parser("hello", help="Print a greeting")
    hello.add_argument("--name", help="Who to greet")
    hello.add_argument("--count", type=int, default=1, help="How many times")

    sub.add_parser("doctor", help="Check the environment")
    sub.add_parser("run", help="Show the git repo root")
    return parser


HANDLERS = {"hello": cmd_hello, "doctor": cmd_doctor, "run": cmd_run}


def main() -> int:
    # One lifecycle for every tool: parse (optionally defaulting a subcommand),
    # then dispatch (which prints the identity banner to stderr for any command
    # and falls back to banner-led help on a bare invocation).
    parser = build_parser()
    args = sk.parse_args(parser, default=DEFAULT_COMMAND)
    return sk.dispatch(
        args, HANDLERS, parser, default=DEFAULT_COMMAND,
        banner=sk.banner("toolname", __version__, TAGLINE, ICON),
    )


if __name__ == "__main__":
    # run_cli centralizes clean exit: CliError → "❌ …" exit 1; Ctrl-C →
    # "⏹ Interrupted." exit 130. Pass on_interrupt=<cleanup> if the tool leaves
    # temp files or partial state behind on interrupt.
    sys.exit(sk.run_cli(main))
