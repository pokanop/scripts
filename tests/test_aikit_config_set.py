"""Tests for aikit config set CLI key validation (mirrors POST /api/config)."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def aikit(tool_loader, tmp_path, monkeypatch):
    m = tool_loader("aikit")
    config_dir = tmp_path / ".aikit"
    monkeypatch.setattr(m, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(m, "CONFIG_FILE", config_dir / "config.json")
    monkeypatch.delenv("AIKIT_SETTINGS__WEB_PORT", raising=False)
    return m, config_dir / "config.json"


def test_config_set_rejects_unknown_top_level_key(aikit):
    m, config_file = aikit
    with pytest.raises(m.AikitError) as exc:
        m.do_config_set("bogus.key", "val")
    assert "Unknown config key" in str(exc.value)
    assert "bogus" in str(exc.value)
    assert not config_file.exists()


def test_config_set_rejects_typoed_section(aikit):
    m, config_file = aikit
    with pytest.raises(m.AikitError):
        m.do_config_set("setting.web_port", "9000")
    assert not config_file.exists()


def test_config_set_rejects_empty_key(aikit):
    m, _ = aikit
    with pytest.raises(m.AikitError):
        m.do_config_set("", "val")


def test_config_set_writes_known_key(aikit):
    m, config_file = aikit
    m.do_config_set("settings.web_port", "9000")
    saved = json.loads(config_file.read_text())
    assert saved["settings"]["web_port"] == 9000


def test_config_set_allows_new_leaf_under_known_section(aikit):
    # Only the top-level segment is validated (same contract as the API patch),
    # so adding a leaf under a known section still works.
    m, config_file = aikit
    m.do_config_set("settings.new_flag", "true")
    saved = json.loads(config_file.read_text())
    assert saved["settings"]["new_flag"] is True
