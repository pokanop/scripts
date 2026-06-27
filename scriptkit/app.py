"""Tool identity & CLI framing: one house style for banners, --help, examples.

Every tool presents the same first impression — an identity line
(``{icon} name vX.Y.Z — tagline``), a ``-v/--version`` flag, and an aligned
``Examples:`` epilog — by building its parser through :func:`make_parser`.
The same identity is reused at runtime via :func:`banner`.
"""

from __future__ import annotations

import argparse

from . import style
from .style import BOLD, CYAN, DIM


class BannerFirstParser(argparse.ArgumentParser):
    """An ArgumentParser whose ``--help`` leads with the identity banner.

    Stock argparse always prints ``usage:`` before the description; this puts
    the description (the tool's identity line) *above* usage, so help reads
    "what is this → how to call it". Mirrors ArgumentParser.format_help with
    the usage/description order swapped.
    """

    def format_help(self) -> str:
        formatter = self._get_formatter()
        formatter.add_text(self.description)                       # identity banner FIRST
        formatter.add_usage(
            self.usage, self._actions, self._mutually_exclusive_groups
        )
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()
        formatter.add_text(self.epilog)
        return formatter.format_help()


def banner(name: str, version: str, tagline: str = "", icon: str = "") -> str:
    """The house identity line, ANSI-styled (and NO_COLOR-aware).

    ``{icon} {name} v{version} — {tagline}`` with the name bold+accent, the
    version dim, and the em-dash dim. Safe for argparse descriptions (argparse
    prints it verbatim) and for plain ``print()`` at runtime.
    """
    prefix = f"{icon.strip()} " if icon else ""
    head = style.styled(name, BOLD, CYAN)
    ver = style.styled(f"v{version}", DIM)
    line = f"{prefix}{head} {ver}"
    if tagline:
        line += f" {style.styled('—', DIM)} {tagline}"
    return line


def examples_block(items, title: str = "Examples") -> str:
    """Format examples into an aligned epilog block.

    ``items`` is a list of ``(command, description)`` pairs (description
    optional) or bare command strings. Commands are column-aligned.
    """
    rows = []
    for item in items:
        if isinstance(item, (tuple, list)):
            cmd = str(item[0])
            desc = str(item[1]) if len(item) > 1 and item[1] else ""
        else:
            cmd, desc = str(item), ""
        rows.append((cmd, desc))
    width = max((len(c) for c, d in rows if d), default=0)
    lines = [f"{title}:"]
    for cmd, desc in rows:
        lines.append(f"  {cmd.ljust(width)}  {desc}".rstrip() if desc else f"  {cmd}")
    return "\n".join(lines)


def make_parser(
    prog: str,
    version: str,
    tagline: str = "",
    *,
    icon: str = "",
    description: str | None = None,
    examples=None,
    epilog: str | None = None,
    add_version: bool = True,
    **kwargs,
) -> argparse.ArgumentParser:
    """Build an ``ArgumentParser`` with the house identity, version, and epilog.

    - ``description`` defaults to :func:`banner` (override to supply your own).
    - ``examples`` (list of pairs/strings) renders an aligned ``Examples:``
      epilog; ``epilog`` takes precedence if both are given.
    - ``add_version`` wires a ``-v/--version`` flag printing ``{prog} {version}``.

    Extra ``kwargs`` pass straight through to ``ArgumentParser``. Add
    subparsers/arguments on the returned parser as usual.
    """
    desc = description if description is not None else banner(prog, version, tagline, icon)
    if epilog is None and examples is not None:
        epilog = examples_block(examples)
    kwargs.setdefault("formatter_class", argparse.RawDescriptionHelpFormatter)
    parser = BannerFirstParser(prog=prog, description=desc, epilog=epilog, **kwargs)
    if add_version:
        parser.add_argument(
            "-v", "--version", action="version", version=f"{prog} {version}"
        )
    return parser
