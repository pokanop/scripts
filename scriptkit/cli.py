"""CLI plumbing: the user-facing error type and a uniform run/dispatch flow.

The whole app lifecycle is centralized here so tools don't re-roll it:

- :func:`run` wraps ``main`` with one error + interrupt + exit policy.
- :func:`parse_args` parses argv, optionally injecting a *default subcommand*
  (so bare ``netsy`` runs ``scan`` with the scan parser's defaults).
- :func:`dispatch` routes to a handler, prints the identity banner for actual
  commands, and falls back to banner-led help on a bare invocation.

A tool's ``main`` collapses to::

    def main() -> int:
        parser = build_parser()
        args = sk.parse_args(parser, default=DEFAULT_COMMAND)
        return sk.dispatch(args, HANDLERS, parser,
                           banner=sk.banner(NAME, __version__, TAGLINE, ICON))

    if __name__ == "__main__":
        sys.exit(sk.run_cli(main))
"""

from __future__ import annotations

import argparse
import sys

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INTERRUPT = 130  # 128 + SIGINT, the POSIX convention


class CliError(Exception):
    """A clean, user-facing error.

    Raise this (or a subclass — e.g. a tool's ``PluckError``) for expected
    failures: bad input, a missing dependency, a remote error. :func:`run`
    prints the message without a traceback and exits 1. Unexpected exceptions
    propagate so the traceback is visible.
    """


def run(main_fn, *args, on_interrupt=None, **kwargs) -> int:
    """Invoke ``main_fn`` with unified error + interrupt handling.

    - :class:`CliError` (and subclasses) -> print ``❌ message`` to stderr, exit 1.
    - ``KeyboardInterrupt`` -> run ``on_interrupt`` (if given), print
      ``⏹ Interrupted.``, exit 130.
    - return value (or 0) is used as the exit code.

    ``on_interrupt`` is an optional zero-arg cleanup callback (e.g. removing
    temp files); exceptions it raises are swallowed so cleanup can't mask the
    interrupt. Callers typically ``sys.exit(run(main))``.
    """
    from . import console

    try:
        rc = main_fn(*args, **kwargs)
        return rc if isinstance(rc, int) and not isinstance(rc, bool) else EXIT_OK
    except CliError as exc:
        console.error(str(exc))
        return EXIT_ERROR
    except KeyboardInterrupt:
        if on_interrupt is not None:
            try:
                on_interrupt()
            except Exception:
                pass
        print("\n  ⏹ Interrupted.", file=sys.stderr)
        return EXIT_INTERRUPT


def _subcommand_choices(parser) -> set[str]:
    """The set of registered subcommand names for ``parser`` (empty if none)."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    return set()


def parse_args(parser, *, default=None, argv=None) -> argparse.Namespace:
    """Parse argv, optionally treating a bare invocation as ``default``.

    When ``default`` is given and the user supplied no recognized subcommand
    (and isn't asking for ``-h``/``--help``/``-v``/``--version``), the default
    subcommand is injected so its parser defaults populate the namespace — e.g.
    bare ``netsy`` becomes ``netsy scan`` with all scan defaults intact.
    """
    raw = list(sys.argv[1:] if argv is None else argv)
    if default is not None:
        choices = _subcommand_choices(parser)
        asks_meta = any(t in ("-h", "--help", "-v", "--version") for t in raw)
        if choices and not asks_meta and not any(t in choices for t in raw):
            raw = [default, *raw]
    return parser.parse_args(raw)


def dispatch(args, handlers, parser=None, *, default=None, banner=None) -> int:
    """Route ``args.command`` to ``handlers[command](args)``.

    - A resolved command (explicit, or ``default`` when none was given) prints
      ``banner`` to stderr — identity is always visible without polluting
      piped stdout — then runs its handler.
    - A bare invocation with no command and no ``default`` prints banner-led
      help (the parser's ``--help`` body already leads with the identity) and
      exits 0 — running a tool with no args is a valid "how do I use this?".
    - An unknown command prints help and exits 1.

    Handlers may return an int exit code; ``None`` is treated as success.
    """
    command = getattr(args, "command", None) or default
    if command is None:
        if parser is not None:
            parser.print_help()
        return EXIT_OK
    handler = handlers.get(command)
    if handler is None:
        if parser is not None:
            parser.print_help()
        return EXIT_ERROR
    if banner:
        print(banner, file=sys.stderr)
    rc = handler(args)
    return rc if isinstance(rc, int) and not isinstance(rc, bool) else EXIT_OK
