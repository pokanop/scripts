"""scriptkit — shared scaffolding for the pokanop CLI toolkit.

A small, dependency-light library that unifies how every tool in this repo
looks and behaves: color + icons, semantic messages, prompts, progress,
tables, three-tier config, subprocess handling, human-friendly formatting,
and CLI dispatch. ``rich`` is used when available, with graceful fallbacks.

Typical use::

    import scriptkit as sk

    sk.success("done")
    sk.error("nope")            # -> stderr, exit via sk.CliError
    for item in sk.track(items, "Processing"):
        ...
    cfg = sk.Config(path, defaults={...}, env_prefix="MYTOOL").load()
    res = sk.run(["git", "status"])     # -> Result(code, out, err)
    sys.exit(sk.run_cli(main))
"""

from __future__ import annotations

from . import app, config, console, proc, progress, style, tables, text
from .app import banner, examples_block, make_parser
from .cli import (
    EXIT_ERROR,
    EXIT_INTERRUPT,
    EXIT_OK,
    CliError,
    dispatch,
    parse_args,
)
from .cli import run as run_cli
from .doctor import Check, check_binary, check_python, doctor
from .config import Config, coerce_scalar, config_from_env, deep_merge, get_nested, set_nested
from .console import (
    HAS_RICH,
    ask,
    confirm,
    detail,
    elapsed,
    err_console,
    error,
    header,
    info,
    kv,
    step,
    success,
    warning,
)
from .console import console as rich_console
from .proc import Result, require, run, which
from .progress import bar, parallel_map, status, track
from .style import ICONS, icon, set_color, strip_ansi, styled, use_color
from .tables import table
from .text import (
    format_timecode,
    human_count,
    human_duration,
    human_size,
    truncate,
)

__version__ = "1.1.0"

__all__ = [
    # submodules
    "app", "config", "console", "proc", "progress", "style", "tables", "text",
    # app / identity
    "banner", "examples_block", "make_parser",
    # doctor
    "doctor", "Check", "check_binary", "check_python",
    # style
    "styled", "icon", "ICONS", "use_color", "set_color", "strip_ansi",
    # console / messages
    "success", "error", "warning", "info", "detail", "step", "header",
    "elapsed", "kv", "ask", "confirm", "rich_console", "err_console", "HAS_RICH",
    # progress
    "bar", "track", "status", "parallel_map",
    # tables
    "table",
    # config
    "Config", "deep_merge", "get_nested", "set_nested", "config_from_env", "coerce_scalar",
    # proc
    "run", "which", "require", "Result",
    # text
    "human_size", "human_duration", "format_timecode", "human_count", "truncate",
    # cli
    "CliError", "run_cli", "dispatch", "parse_args",
    "EXIT_OK", "EXIT_ERROR", "EXIT_INTERRUPT",
    "__version__",
]
