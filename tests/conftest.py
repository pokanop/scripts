"""Shared pytest fixtures for the scriptkit + tools test suite."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def _reset_color(monkeypatch):
    """Isolate color state: no NO_COLOR/FORCE_COLOR, auto-detection restored."""
    import scriptkit.style as style

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    style.set_color(None)
    yield
    style.set_color(None)


@pytest.fixture
def no_color(monkeypatch):
    """Force color off for deterministic, plain-text assertions."""
    import scriptkit.style as style

    style.set_color(False)
    return style


def load_tool(name: str):
    """Import a tool (an extension-less script) as a module by file path.

    Cached on the module registry so repeated loads in one session are cheap.
    """
    mod_name = f"_tool_{name}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    path = REPO_ROOT / name
    # Tools are extension-less scripts; force the source loader so importlib
    # treats them as Python regardless of the missing ``.py`` suffix.
    loader = importlib.machinery.SourceFileLoader(mod_name, str(path))
    spec = importlib.util.spec_from_loader(mod_name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    loader.exec_module(module)
    return module


@pytest.fixture
def tool_loader():
    return load_tool
