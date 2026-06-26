"""Tests for scriptkit.config — merge, nested access, three-tier loading."""

import json
import sys

import pytest

import scriptkit.config as config
from scriptkit.config import Config


def test_deep_merge_nested():
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    override = {"a": {"c": 9, "e": 5}, "f": 6}
    assert config.deep_merge(base, override) == {
        "a": {"b": 1, "c": 9, "e": 5}, "d": 3, "f": 6,
    }


def test_deep_merge_does_not_mutate():
    base = {"a": {"b": 1}}
    config.deep_merge(base, {"a": {"b": 2}})
    assert base == {"a": {"b": 1}}


def test_get_nested():
    data = {"a": {"b": {"c": 42}}}
    assert config.get_nested(data, "a.b.c") == 42
    assert config.get_nested(data, "a.x", "fallback") == "fallback"
    assert config.get_nested(data, "a.b.c.d", "fb") == "fb"  # past a leaf


def test_set_nested_creates_path():
    data = {}
    config.set_nested(data, "a.b.c", 1)
    assert data == {"a": {"b": {"c": 1}}}


def test_set_nested_overwrites_non_dict():
    data = {"a": 5}
    config.set_nested(data, "a.b", 1)
    assert data == {"a": {"b": 1}}


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("MYTOOL_WEB__PORT", "9000")
    monkeypatch.setenv("MYTOOL_NAME", "demo")
    monkeypatch.setenv("OTHER_X", "ignored")
    out = config.config_from_env("MYTOOL")
    assert out == {"web": {"port": "9000"}, "name": "demo"}


def test_config_load_defaults_only(tmp_path):
    cfg = Config(tmp_path / "c.json", defaults={"a": 1})
    assert cfg.load() == {"a": 1}


def test_config_load_merges_file(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"b": 2}))
    cfg = Config(path, defaults={"a": 1, "b": 0})
    assert cfg.load() == {"a": 1, "b": 2}


def test_config_load_corrupt_file_falls_back(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("{not json")
    cfg = Config(path, defaults={"a": 1})
    assert cfg.load() == {"a": 1}


def test_config_env_overrides_file(tmp_path, monkeypatch):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"web": {"port": 1}}))
    monkeypatch.setenv("MYTOOL_WEB__PORT", "2")
    cfg = Config(path, defaults={"web": {"port": 0}}, env_prefix="MYTOOL")
    assert cfg.load()["web"]["port"] == "2"


def test_config_save_roundtrip_and_perms(tmp_path):
    path = tmp_path / "sub" / "c.json"
    cfg = Config(path, defaults={})
    cfg.save({"x": 1})
    assert json.loads(path.read_text()) == {"x": 1}
    if sys.platform != "win32":
        assert (path.stat().st_mode & 0o777) == 0o600


def test_coerce_scalar():
    assert config.coerce_scalar("true") is True
    assert config.coerce_scalar("YES") is True
    assert config.coerce_scalar("false") is False
    assert config.coerce_scalar("no") is False
    assert config.coerce_scalar("null") is None
    assert config.coerce_scalar("none") is None
    assert config.coerce_scalar("42") == 42
    assert config.coerce_scalar("3.5") == 3.5
    assert config.coerce_scalar("hello") == "hello"
    assert config.coerce_scalar(99) == 99  # non-string passthrough


def test_set_nested_coerce():
    data = {}
    config.set_nested(data, "a.port", "9000", coerce=True)
    assert data["a"]["port"] == 9000


def test_config_from_env_coerce(monkeypatch):
    monkeypatch.setenv("MYTOOL_WEB__PORT", "9000")
    out = config.config_from_env("MYTOOL", coerce=True)
    assert out == {"web": {"port": 9000}}


def test_config_static_get_set():
    data = {"a": {"b": 1}}
    assert Config.get(data, "a.b") == 1
    Config.set(data, "a.c", 2)
    assert data["a"]["c"] == 2
