"""Tests for aikit POST /api/config deep-merge and validation."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def aikit_app(tool_loader, tmp_path, monkeypatch):
    m = tool_loader("aikit")
    config_dir = tmp_path / ".aikit"
    config_file = config_dir / "config.json"
    monkeypatch.setattr(m, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(m, "CONFIG_FILE", config_file)
    monkeypatch.delenv("AIKIT_SETTINGS__WEB_PORT", raising=False)
    app = m.create_flask_app()
    app.config["TESTING"] = True
    return m, app.test_client(), config_file


def _write_config(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def test_api_config_post_deep_merges_settings(aikit_app):
    m, client, config_file = aikit_app
    _write_config(config_file, {
        "version": 1,
        "agents": {"cursor": {"installed": True, "version": "1.0"}},
        "settings": {"web_port": 8765, "web_host": "localhost"},
    })

    resp = client.post(
        "/api/config",
        json={"settings": {"web_port": 8801}, "version": 1, "agents": {}},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}

    saved = json.loads(config_file.read_text())
    assert saved["settings"]["web_port"] == 8801
    assert saved["settings"]["web_host"] == "localhost"
    assert saved["agents"] == {"cursor": {"installed": True, "version": "1.0"}}


def test_api_config_post_rejects_unknown_keys(aikit_app):
    _, client, config_file = aikit_app
    _write_config(config_file, {"version": 1, "agents": {}, "settings": {}})

    resp = client.post("/api/config", json={"bogus": 1})
    assert resp.status_code == 400
    assert "Unknown config keys" in resp.get_json()["error"]


def test_api_config_post_rejects_non_object(aikit_app):
    _, client, _ = aikit_app

    resp = client.post(
        "/api/config",
        data="[]",
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Request body must be a JSON object"


def test_api_config_post_rejects_invalid_types(aikit_app):
    _, client, config_file = aikit_app
    _write_config(config_file, {"version": 1, "agents": {}, "settings": {}})

    resp = client.post("/api/config", json={"settings": "nope"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "settings must be an object"


def test_validate_config_patch_accepts_partial(aikit_app):
    m, _, _ = aikit_app
    assert m._validate_config_patch({"settings": {"web_port": 9000}}) is None
