"""Unit tests for the aikit gateway engine (Stage 2).

Pure pieces only — registry, env-pair building, manifest, shell/rc detection,
model-list parsing with a mocked getter — plus an on→status→off round-trip that
exercises the managed env block and manifest on a temp rc file. No real network.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def aikit(tool_loader):
    return tool_loader("aikit")


# --- provider registry (the data that ships "support for each provider") ----
def test_registry_is_complete_and_unique(aikit):
    ids = [p[0] for p in aikit.GATEWAY_PROVIDERS]
    prefixes = [p[2] for p in aikit.GATEWAY_PROVIDERS]
    assert len(ids) == 65
    assert len(ids) == len(set(ids))         # ids unique
    assert len(prefixes) == len(set(prefixes))  # prefixes unique
    for expected in ("openai", "anthropic", "gemini", "bedrock", "vertex_ai",
                     "azure", "ollama", "vllm", "groq", "cohere"):
        assert expected in ids


def test_registry_native_passthrough_routes(aikit):
    routes = {p[0]: p[5] for p in aikit.GATEWAY_PROVIDERS}
    assert routes["anthropic"] == "/anthropic"
    assert routes["gemini"] == "/gemini"
    assert routes["bedrock"] == "/bedrock"
    assert routes["vertex_ai"] == "/vertex_ai"
    assert routes["openai"] == "/v1"


def test_registry_local_providers_have_no_key_envs(aikit):
    by_id = {p[0]: p for p in aikit.GATEWAY_PROVIDERS}
    assert by_id["ollama"][3] == []  # no API key for local Ollama
    assert "litellm" in {t[0] for t in aikit.OPENAI_COMPATIBLE_TOOLS}


# --- env-pair building ------------------------------------------------------
def test_build_env_pairs_universal_block(aikit):
    pairs = aikit.build_env_pairs("https://gw.example.com/", "sk-secret")
    d = dict(pairs)
    assert d["OPENAI_API_KEY"] == "sk-secret"
    assert d["OPENAI_BASE_URL"] == "https://gw.example.com/v1"
    assert d["OPENAI_API_BASE"] == "https://gw.example.com/v1"
    assert d["LITELLM_PROXY_API_BASE"] == "https://gw.example.com"
    assert d["LITELLM_PROXY_API_KEY"] == "sk-secret"
    # per-provider routing (native pass-through + key fan-out)
    assert d["ANTHROPIC_BASE_URL"] == "https://gw.example.com/anthropic"
    assert d["ANTHROPIC_API_KEY"] == "sk-secret"
    assert d["GROQ_API_BASE"] == "https://gw.example.com/v1"


def test_build_env_pairs_dedups_and_preserves_order(aikit):
    pairs = aikit.build_env_pairs("https://gw", "k")
    keys = [k for k, _ in pairs]
    assert len(keys) == len(set(keys))           # no dupes
    assert keys[0] == "OPENAI_API_KEY"           # universal block first


def test_build_env_pairs_never_clobbers_general_credentials(aikit):
    d = dict(aikit.build_env_pairs("https://gw", "k"))
    for forbidden in ("AWS_ACCESS_KEY_ID", "GITHUB_TOKEN", "GH_TOKEN",
                      "GOOGLE_APPLICATION_CREDENTIALS", "HF_TOKEN", "DATABRICKS_TOKEN"):
        assert forbidden not in d
    # only inference-scoped cloud vars are set
    assert d["AWS_BEARER_TOKEN_BEDROCK"] == "k"
    assert d["GITHUB_API_KEY"] == "k"


def test_build_env_pairs_only_discovered(aikit):
    d = dict(aikit.build_env_pairs("https://gw", "k", only_providers={"anthropic"}))
    assert "ANTHROPIC_BASE_URL" in d        # targeted provider present
    assert "GROQ_API_BASE" not in d         # untargeted provider absent
    assert "OPENAI_API_KEY" in d            # universal block still present


def test_render_env_block_body_is_shell_specific_and_deterministic(aikit):
    pairs = [("FOO", "bar")]
    bash = aikit.render_env_block_body("bash", pairs)
    fish = aikit.render_env_block_body("fish", pairs)
    assert 'export FOO="bar"' in bash
    assert 'set -gx FOO "bar"' in fish
    # no volatile timestamp → re-render is byte-identical (idempotency)
    assert aikit.render_env_block_body("bash", pairs) == bash


# --- url / secret helpers ---------------------------------------------------
def test_normalize_gateway_url(aikit):
    assert aikit._normalize_gateway_url("gw.example.com/") == "https://gw.example.com"
    assert aikit._normalize_gateway_url("http://x/") == "http://x"
    assert aikit._normalize_gateway_url("  https://y  ") == "https://y"
    assert aikit._normalize_gateway_url("") == ""


def test_mask_secret(aikit):
    assert aikit._mask_secret("sk-1234567890") == "sk-12…"
    assert aikit._mask_secret("short") == "***"
    assert aikit._mask_secret("") == ""


# --- model discovery with a mocked getter (no network) ----------------------
def test_parse_models_list(aikit):
    data = {"data": [{"id": "openai/gpt-4o"}, {"id": "groq/llama"}, {"no_id": 1}]}
    models, detail = aikit.parse_models_list(data)
    assert models == ["openai/gpt-4o", "groq/llama"]
    assert detail["openai/gpt-4o"] == {}


def test_discover_models_merges_model_info(aikit):
    def fake_getter(url, key):
        if url.endswith("/v1/models"):
            return {"data": [{"id": "openai/gpt-4o"}, {"id": "groq/llama"}]}
        if url.endswith("/model/info"):
            return {"data": [{
                "model_name": "openai/gpt-4o",
                "litellm_params": {"custom_llm_provider": "openai"},
                "model_info": {"max_tokens": 128000},
            }]}
        raise AssertionError(f"unexpected url {url}")

    models, detail = aikit.discover_models("https://gw/", "sk-x", getter=fake_getter)
    assert models == ["groq/llama", "openai/gpt-4o"]        # sorted, de-duped
    assert detail["openai/gpt-4o"]["provider"] == "openai"
    assert detail["openai/gpt-4o"]["max_tokens"] == 128000


def test_discover_models_ignores_model_info_failure(aikit):
    def fake_getter(url, key):
        if url.endswith("/v1/models"):
            return {"data": [{"id": "x/y"}]}
        raise aikit.AikitError("privileged endpoint denied")

    models, _ = aikit.discover_models("https://gw", "k", getter=fake_getter)
    assert models == ["x/y"]


def test_discover_models_surfaces_v1_models_error(aikit):
    def fake_getter(url, key):
        raise aikit.AikitError("could not reach gateway")

    with pytest.raises(aikit.AikitError):
        aikit.discover_models("https://gw", "k", getter=fake_getter)


def test_providers_in_use(aikit):
    models = ["openai/gpt-4o", "anthropic/claude", "bogusprov/x", "bare-model"]
    detail = {"openai/gpt-4o": {"provider": "openai"}}
    used = aikit.providers_in_use(models, detail)
    assert "openai" in used and "anthropic" in used
    assert "bogusprov" not in used


# --- shell / rc detection ---------------------------------------------------
def test_detect_shell(aikit, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert aikit.detect_shell("zsh") == ("zsh", tmp_path / ".zshrc")
    assert aikit.detect_shell("fish") == ("fish", tmp_path / ".config" / "fish" / "config.fish")
    # bash prefers ~/.bash_profile when it exists, else ~/.bashrc
    assert aikit.detect_shell("bash")[1] == tmp_path / ".bashrc"
    (tmp_path / ".bash_profile").write_text("")
    assert aikit.detect_shell("bash")[1] == tmp_path / ".bash_profile"


# --- manifest read/write/clear ----------------------------------------------
def test_manifest_roundtrip(aikit, tmp_path):
    p = tmp_path / "state.json"
    data = aikit.build_manifest("https://gw", "zsh", tmp_path / ".zshrc", "BLOCK",
                                model_count=3, only_discovered=False)
    aikit.write_manifest(data, p)
    assert (p.stat().st_mode & 0o777) == 0o600     # secrets-grade perms
    got = aikit.read_manifest(p)
    assert got["active"] is True
    assert got["gateway_url"] == "https://gw"
    assert got["model_count"] == 3
    assert got["config_files"] == []               # Stage 3 slot present
    aikit.clear_manifest(p)
    assert aikit.read_manifest(p) == {}
    aikit.clear_manifest(p)                          # idempotent


def test_read_manifest_tolerates_bad_json(aikit, tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{ not json")
    assert aikit.read_manifest(p) == {}


def test_undo_config_file_deletes_created(aikit, tmp_path):
    created = tmp_path / "made-by-aikit.json"
    created.write_text("{}")
    aikit._undo_config_file({"path": str(created), "created_by_aikit": True})
    assert not created.exists()


# --- on → status → off round-trip (managed block + manifest, no network) -----
@pytest.fixture
def isolated_gateway(aikit, tmp_path, monkeypatch):
    """Point the gateway dir/config/manifest, HOME, and shell rc at a temp dir; stub
    discovery and default every wrapped tool to *not* installed (no real-home writes)."""
    rc = tmp_path / ".zshrc"
    rc.write_text("# existing rc\nalias g=git\n")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(aikit, "GATEWAY_DIR", tmp_path / "gw")
    monkeypatch.setattr(aikit, "GATEWAY_CONFIG_FILE", tmp_path / "gw" / "config.json")
    monkeypatch.setattr(aikit, "GATEWAY_STATE_FILE", tmp_path / "gw" / "state.json")
    monkeypatch.setattr(aikit, "detect_shell", lambda explicit=None: ("zsh", rc))
    monkeypatch.setattr(aikit, "discover_models",
                        lambda u, k, **kw: (["anthropic/claude-3", "openai/gpt-4o"], {}))
    monkeypatch.setattr(aikit, "detect_gateway_tool", lambda agent_key: False)
    return rc


def test_gateway_on_off_roundtrip_is_pristine(aikit, isolated_gateway):
    rc = isolated_gateway
    original = rc.read_text()
    key = "sk-test-key-1234567890"

    aikit.do_gateway_on("https://gw.example.com", key, yes=True)
    text = rc.read_text()
    assert aikit.GATEWAY_BLOCK.present_in(text)
    assert key in text                              # key lands in the env block
    assert 'export OPENAI_BASE_URL="https://gw.example.com/v1"' in text
    backup = rc.with_name(rc.name + aikit.GATEWAY_RC_BACKUP_SUFFIX)
    assert backup.read_text() == original           # pre-block snapshot

    manifest = aikit.read_manifest()
    assert manifest["active"] is True
    assert manifest["model_count"] == 2
    assert aikit.load_gateway_config()["key"] == key  # credential persisted

    # idempotent: same args again → byte-identical rc, manifest still active
    aikit.do_gateway_on("https://gw.example.com", key, yes=True)
    assert rc.read_text() == text
    assert aikit.read_manifest()["active"] is True

    # off → rc pristine, manifest + backup gone
    aikit.do_gateway_off()
    assert rc.read_text() == original
    assert aikit.read_manifest() == {}
    assert not backup.exists()

    # second off → friendly no-op (no crash)
    aikit.do_gateway_off()
    assert rc.read_text() == original


def test_gateway_on_off_pristine_when_rc_has_no_trailing_newline(aikit, isolated_gateway):
    """`off` restores an rc that did not end in a newline byte-for-byte (no stray \\n)."""
    rc = isolated_gateway
    rc.write_text("# rc without trailing newline\nalias g=git")  # no final \n
    original = rc.read_text()
    assert not original.endswith("\n")

    aikit.do_gateway_on("https://gw.example.com", "sk-key-1234567890", yes=True)
    assert aikit.GATEWAY_BLOCK.present_in(rc.read_text())

    aikit.do_gateway_off()
    assert rc.read_text() == original  # pristine — no trailing newline introduced


def test_gateway_on_dry_run_writes_nothing_and_masks_key(aikit, isolated_gateway, capsys):
    rc = isolated_gateway
    original = rc.read_text()
    key = "sk-secret-abcdef-9999"

    aikit.do_gateway_on("https://gw.example.com", key, dry_run=True)

    assert rc.read_text() == original               # nothing written
    assert aikit.read_manifest() == {}              # no manifest
    out = capsys.readouterr().out
    assert "Dry run" in out
    assert key not in out                            # full key never printed


def test_gateway_off_dry_run_keeps_block(aikit, isolated_gateway):
    rc = isolated_gateway
    aikit.do_gateway_on("https://gw.example.com", "sk-key-12345678", yes=True)
    active = rc.read_text()
    aikit.do_gateway_off(dry_run=True)
    assert rc.read_text() == active                  # dry-run off changed nothing
    assert aikit.read_manifest()["active"] is True
