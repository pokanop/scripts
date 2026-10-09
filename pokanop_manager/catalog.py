"""Dependency-free discovery; tool modules and heavy dependencies are never imported."""
from __future__ import annotations

import json
import re
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate catalog key: {key}")
        result[key] = value
    return result


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def load(root: Path | None = None) -> dict:
    value = read_json(Path(__file__).with_name("catalog.json"))
    if set(value) != {"schema_version", "tools"} or value["schema_version"] != 1:
        raise ValueError("unsupported Pokanop catalog")
    tools = value["tools"]
    if root and (root / ".scripts-catalog.json").exists():
        extra = read_json(root / ".scripts-catalog.json")
        if set(extra) & set(tools):
            raise ValueError("registered tool collides with built-in catalog")
        tools.update(extra)
    for name, tool in tools.items():
        if not re.fullmatch(r"[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*", name) or name == "scripts":
            raise ValueError("invalid catalog tool name")
        if set(tool) not in ({"description", "requirements", "system"},
                             {"description", "requirements", "system", "project"}):
            raise ValueError(f"unknown catalog fields: {name}")
        if not isinstance(tool["description"], str) or not isinstance(tool["requirements"], str):
            raise ValueError("invalid catalog metadata")
        req = Path(tool["requirements"])
        if req.is_absolute() or ".." in req.parts:
            raise ValueError("requirements must be relative and confined")
        if not isinstance(tool["system"], list):
            raise ValueError("invalid system dependencies")
        for entry in tool["system"]:
            if (not isinstance(entry, list) or len(entry) != 3
                    or not isinstance(entry[0], str) or type(entry[1]) is not bool
                    or not isinstance(entry[2], str)):
                raise ValueError("invalid system dependency")
    return tools
