"""CLI plumbing: the user-facing error type and a uniform dispatch wrapper."""

from __future__ import annotations

import sys

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INTERRUPT = 130  # 128 + SIGINT, the POSIX convention


class CliError(Exception):
    """A clean, user-facing error.

    Raise this for expected failures (bad input, missing dependency, remote
    error). :func:`run` prints the message without a traceback and exits 1.
    Unexpected exceptions propagate so the traceback is visible.
    """


def run(main_fn, *args, **kwargs) -> int:
    """Invoke ``main_fn`` with unified error + interrupt handling.

    - :class:`CliError` -> print ``❌ message`` to stderr, exit 1.
    - ``KeyboardInterrupt`` -> print ``⏹ Interrupted.``, exit 130.
    - return value (or 0) is used as the exit code.

    Returns the exit code; callers typically ``sys.exit(run(main))``.
    """
    from . import console

    try:
        rc = main_fn(*args, **kwargs)
        return rc if isinstance(rc, int) and not isinstance(rc, bool) else EXIT_OK
    except CliError as exc:
        console.error(str(exc))
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("\n  ⏹ Interrupted.", file=sys.stderr)
        return EXIT_INTERRUPT


def dispatch(args, handlers, parser=None) -> int:
    """Route ``args.command`` to ``handlers[command](args)``.

    With no/unknown command, print help (if ``parser`` given) and return 1.
    Handlers may return an int exit code; ``None`` is treated as success.
    """
    command = getattr(args, "command", None)
    handler = handlers.get(command) if command else None
    if handler is None:
        if parser is not None:
            parser.print_help()
        return EXIT_ERROR
    rc = handler(args)
    return rc if isinstance(rc, int) and not isinstance(rc, bool) else EXIT_OK
