"""Three-tier configuration: defaults < saved file < environment overrides.

Synthesized from aikit/medcat. Supports deep-merging nested dicts, dot-path
get/set, and a ``PREFIX_A__B=value`` environment convention that maps onto
``a.b``. ``save()`` writes pretty JSON with ``0600`` permissions.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def coerce_scalar(value: Any) -> Any:
    """Coerce a string into its natural scalar type (for env-var config).

    ``"true"/"yes" -> True``, ``"false"/"no" -> False``,
    ``"null"/"none" -> None``, then int, then float, else the string as-is.
    Non-strings pass through unchanged.
    """
    if not isinstance(value, str):
        return value
    low = value.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "none"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` onto a copy of ``base``."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_nested(data: dict, path: str, default: Any = None) -> Any:
    """Read a value by dot-path (``"services.kavita.url"``)."""
    node: Any = data
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node


def set_nested(data: dict, path: str, value: Any, *, coerce: bool = False) -> None:
    """Set a value by dot-path, creating intermediate dicts as needed.

    With ``coerce=True``, string values are run through :func:`coerce_scalar`.
    """
    parts = path.split(".")
    node = data
    for part in parts[:-1]:
        nxt = node.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            node[part] = nxt
        node = nxt
    node[parts[-1]] = coerce_scalar(value) if coerce else value


def config_from_env(prefix: str, *, coerce: bool = False) -> dict:
    """Build an overrides dict from ``PREFIX_*`` env vars.

    ``PREFIX_WEB__PORT=9000`` -> ``{"web": {"port": "9000"}}``. The prefix is
    matched case-insensitively; ``__`` becomes a path separator. With
    ``coerce=True``, scalar strings become their natural types.
    """
    overrides: dict = {}
    norm = prefix.upper()
    if not norm.endswith("_"):
        norm += "_"
    for key, value in os.environ.items():
        if not key.upper().startswith(norm):
            continue
        path = key[len(norm):].lower().replace("__", ".")
        if path:
            set_nested(overrides, path, value, coerce=coerce)
    return overrides


class Config:
    """A tool's config file with three-tier loading and dot-path access.

    >>> cfg = Config(Path.home() / ".mytool" / "config.json",
    ...              defaults={"web": {"port": 8765}}, env_prefix="MYTOOL")
    >>> data = cfg.load()
    >>> cfg.get(data, "web.port")
    """

    def __init__(self, path, defaults: dict | None = None, env_prefix: str | None = None,
                 coerce_env: bool = False):
        self.path = Path(path)
        self.defaults = defaults or {}
        self.env_prefix = env_prefix
        self.coerce_env = coerce_env

    def load(self) -> dict:
        """Return defaults merged with the saved file and env overrides."""
        data = dict(self.defaults)
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text())
                if isinstance(saved, dict):
                    data = deep_merge(data, saved)
            except (json.JSONDecodeError, OSError):
                pass
        if self.env_prefix:
            env = config_from_env(self.env_prefix, coerce=self.coerce_env)
            if env:
                data = deep_merge(data, env)
        return data

    def save(self, data: dict, *, mode: int = 0o600) -> None:
        """Write ``data`` as pretty JSON, creating parent dirs, chmod ``mode``."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2) + "\n")
        try:
            self.path.chmod(mode)
        except OSError:
            pass

    @staticmethod
    def get(data: dict, path: str, default: Any = None) -> Any:
        return get_nested(data, path, default)

    @staticmethod
    def set(data: dict, path: str, value: Any) -> None:
        set_nested(data, path, value)
