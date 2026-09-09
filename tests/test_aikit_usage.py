"""aikit usage — unified subscription/credits/rate-limit snapshot.

All HTTP is stubbed via ``_usage_http``; credential files live in a tmp home.
No real provider is ever contacted and no token appears in any output.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN = "sk-test-secret-token-0123456789"


@pytest.fixture
def aikit(tool_loader, tmp_path, monkeypatch):
    m = tool_loader("aikit")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(m, "_usage_home", lambda: home)
    monkeypatch.setattr(m, "_CURRENT_PLATFORM", "Linux")
    for var in ("CODEX_HOME", "CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "GROK_HOME",
                "GH_TOKEN", "GITHUB_TOKEN", "COPILOT_GITHUB_TOKEN", "AMP_API_KEY", "FACTORY_API_KEY",
                "KILO_API_KEY", "KILOCODE_API_KEY", "OPENROUTER_API_KEY", "OPENROUTER_MANAGEMENT_API_KEY",
                "SYNTHETIC_API_KEY", "Z_AI_API_KEY", "ZAI_API_KEY", "KIMI_API_KEY", "DEVIN_BEARER_TOKEN",
                "DEVIN_AUTHORIZATION", "DEVIN_ORG_ID", "CURSOR_SESSION_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    m._test_home = home
    return m


def stub_http(monkeypatch, aikit, responses):
    """responses: {url_prefix: (status, json_body)}; records requests for assertions."""
    calls = []

    def fake(url, *, headers=None, method="GET", body=None, timeout=15):
        calls.append({"url": url, "headers": dict(headers or {}), "method": method, "body": body})
        for prefix, (status, payload) in responses.items():
            if url.startswith(prefix):
                text = json.dumps(payload) if payload is not None else ""
                return status, payload, text
        raise aikit.UsageProbeError(f"unexpected url {url}")

    monkeypatch.setattr(aikit, "_usage_http", fake)
    return calls


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


# --- normalisation helpers ----------------------------------------------------

def test_usage_window_derives_percent_and_iso_reset(aikit):
    w = aikit.usage_window("weekly", used=25, limit=100, unit="req", resets_at=1_700_000_000)
    assert w["used_pct"] == 25.0
    assert w["resets_at"] == "2023-11-14T22:13:20Z"


def test_usage_window_accepts_millis_and_zero_limit(aikit):
    assert aikit.usage_window("x", resets_at=1_700_000_000_000)["resets_at"] == "2023-11-14T22:13:20Z"
    assert aikit.usage_window("x", used=5, limit=0)["used_pct"] is None


def test_usage_result_shape_and_registry_metadata(aikit):
    r = aikit.usage_result("claude", aikit.USAGE_OK, plan="max")
    assert r["name"] == "Claude Code" and r["vendor"] == "Anthropic"
    assert r["status"] == "ok" and r["windows"] == [] and r["extra"] == {}
    assert set(r) >= {"provider", "account", "plan", "source", "credits", "spend", "message", "fetched_at"}


def test_probe_usage_unsupported_and_error_paths(aikit, monkeypatch):
    assert aikit.probe_usage("goose")["status"] == aikit.USAGE_UNSUPPORTED
    monkeypatch.setitem(aikit.USAGE_PROBES, "boom", lambda: (_ for _ in ()).throw(KeyError("x")))
    assert aikit.probe_usage("boom")["status"] == aikit.USAGE_ERROR
    assert "KeyError" in aikit.probe_usage("boom")["message"]


def test_usage_get_json_maps_http_errors_without_leaking_headers(aikit, monkeypatch):
    monkeypatch.setattr(aikit, "_usage_http", lambda url, **kw: (401, {"error": "bad"}, ""))
    with pytest.raises(aikit.UsageProbeError) as e:
        aikit._usage_get_json("https://x", {"Authorization": f"Bearer {TOKEN}"})
    assert "401" in str(e.value) and TOKEN not in str(e.value)
    monkeypatch.setattr(aikit, "_usage_http", lambda url, **kw: (500, {"message": "boom"}, ""))
    with pytest.raises(aikit.UsageProbeError, match="HTTP 500 — boom"):
        aikit._usage_get_json("https://x", {})


# --- providers ----------------------------------------------------------------

def test_codex_probe_reads_auth_json_and_parses_windows(aikit, monkeypatch):
    write_json(aikit._test_home / ".codex" / "auth.json",
               {"tokens": {"access_token": TOKEN, "account_id": "acct_1"}})
    calls = stub_http(monkeypatch, aikit, {
        "https://chatgpt.com/backend-api/wham/usage": (200, {
            "plan_type": "plus",
            "rate_limit": {
                "primary_window": {"used_percent": 42, "reset_at": 1_700_000_000},
                "secondary_window": {"used_percent": 10, "reset_at": 1_700_600_000},
            },
            "credits": {"has_credits": True, "balance": 12.5, "unlimited": False},
        }),
    })
    r = aikit.probe_usage("codex")
    assert r["status"] == "ok" and r["plan"] == "plus" and r["account"] == "acct_1"
    assert [w["label"] for w in r["windows"]] == ["5h session", "weekly"]
    assert r["windows"][0]["used_pct"] == 42.0
    assert r["credits"]["remaining"] == 12.5
    assert calls[0]["headers"]["ChatGPT-Account-Id"] == "acct_1"
    assert calls[0]["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert TOKEN not in json.dumps(r)


def test_codex_probe_unauthenticated_without_auth_file(aikit, monkeypatch):
    stub_http(monkeypatch, aikit, {})
    r = aikit.probe_usage("codex")
    assert r["status"] == "unauthenticated" and "codex login" in r["message"]


def test_claude_probe_honours_config_dir_and_extra_usage(aikit, monkeypatch):
    cfg = aikit._test_home / "claude-cfg"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cfg))
    write_json(cfg / ".credentials.json", {"claudeAiOauth": {"accessToken": TOKEN, "subscriptionType": "max"}})
    calls = stub_http(monkeypatch, aikit, {
        "https://api.anthropic.com/api/oauth/usage": (200, {
            "five_hour": {"utilization": 63.2, "resets_at": "2026-01-01T00:00:00Z"},
            "seven_day": {"utilization": 20, "resets_at": "2026-01-05T00:00:00Z"},
            "seven_day_opus": {"utilization": None},
            "extra_usage": {"is_enabled": True, "monthly_limit": 50, "used_credits": 12},
        }),
    })
    r = aikit.probe_usage("claude")
    assert r["status"] == "ok" and r["plan"] == "max"
    assert [w["label"] for w in r["windows"]] == ["5h session", "weekly"]
    assert r["spend"] == {"amount": 12, "currency": "USD", "period": "monthly", "limit": 50}
    assert calls[0]["headers"]["anthropic-beta"] == "oauth-2025-04-20"


def test_copilot_probe_prefers_env_token_and_parses_quota_snapshots(aikit, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", TOKEN)
    calls = stub_http(monkeypatch, aikit, {
        "https://api.github.com/copilot_internal/user": (200, {
            "copilot_plan": "individual_pro",
            "quota_reset_date": "2026-02-01",
            "quota_snapshots": {
                "premium_interactions": {"entitlement": 300, "remaining": 120, "percent_remaining": 40},
                "chat": {"unlimited": True},
            },
        }),
        "https://api.github.com/user": (200, {"login": "octocat"}),
    })
    r = aikit.probe_usage("copilot")
    assert r["status"] == "ok" and r["account"] == "octocat" and r["plan"] == "individual_pro"
    assert r["source"] == "$GH_TOKEN"
    premium = next(w for w in r["windows"] if w["label"] == "premium_interactions")
    assert premium["used"] == 180 and premium["limit"] == 300 and premium["used_pct"] == 60.0
    assert calls[0]["headers"]["Authorization"] == f"token {TOKEN}"


def test_copilot_probe_falls_back_to_gh_hosts_file(aikit, monkeypatch):
    hosts = aikit._test_home / ".config" / "gh" / "hosts.yml"
    hosts.parent.mkdir(parents=True)
    hosts.write_text(f"github.com:\n    oauth_token: {TOKEN}\n    user: octocat\n")
    stub_http(monkeypatch, aikit, {
        "https://api.github.com/copilot_internal/user": (200, {"quota_snapshots": {}}),
        "https://api.github.com/user": (200, {"login": "octocat"}),
    })
    r = aikit.probe_usage("copilot")
    assert r["status"] == "ok" and r["source"].endswith("hosts.yml")


def test_gemini_probe_reports_expired_token_without_network(aikit, monkeypatch):
    write_json(aikit._test_home / ".gemini" / "oauth_creds.json",
               {"access_token": TOKEN, "expiry_date": 1_000_000_000_000})
    calls = stub_http(monkeypatch, aikit, {})
    r = aikit.probe_usage("gemini")
    assert r["status"] == "unauthenticated" and "expired" in r["message"]
    assert calls == []


def test_gemini_probe_loads_project_then_quota(aikit, monkeypatch):
    write_json(aikit._test_home / ".gemini" / "oauth_creds.json",
               {"access_token": TOKEN, "expiry_date": 9_999_999_999_999})
    calls = stub_http(monkeypatch, aikit, {
        "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist": (200, {
            "cloudaicompanionProject": "gen-lang-client-123", "currentTier": {"id": "standard-tier"}}),
        "https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota": (200, {
            "buckets": [{"modelId": "gemini-2.5-pro", "remainingFraction": 0.25, "resetTime": "2026-01-01T00:00:00Z"}]}),
    })
    r = aikit.probe_usage("gemini")
    assert r["status"] == "ok" and r["account"] == "gen-lang-client-123" and r["plan"] == "standard-tier"
    assert r["windows"][0]["label"] == "gemini-2.5-pro" and r["windows"][0]["used_pct"] == 75.0
    assert calls[1]["body"] == {"project": "gen-lang-client-123"}


def test_grok_probe_prefers_oidc_scope(aikit, monkeypatch):
    write_json(aikit._test_home / ".grok" / "auth.json", {
        "https://legacy": {"key": "legacy-key", "email": "old@x.ai"},
        "https://oidc.x.ai": {"key": TOKEN, "auth_mode": "oidc", "email": "me@x.ai"},
    })
    calls = stub_http(monkeypatch, aikit, {
        "https://cli-chat-proxy.grok.com/v1/billing": (200, {"config": {
            "subscriptionTier": "SuperGrok", "creditUsagePercent": 33,
            "currentPeriod": {"end": "2026-03-01T00:00:00Z"},
            "onDemandCap": {"val": 20}, "onDemandUsed": {"val": 4.5}}}),
    })
    r = aikit.probe_usage("grok")
    assert r["status"] == "ok" and r["account"] == "me@x.ai" and r["plan"] == "SuperGrok"
    assert r["windows"][0]["used_pct"] == 33.0
    assert r["spend"]["amount"] == 4.5 and r["spend"]["limit"] == 20
    assert calls[0]["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert calls[0]["headers"]["x-xai-token-auth"] == "xai-grok-cli"


def test_kiro_probe_reads_sqlite_and_derives_region(aikit, monkeypatch):
    db = aikit._test_home / ".local" / "share" / "kiro-cli" / "data.sqlite3"
    db.parent.mkdir(parents=True)
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE auth_kv (key TEXT, value TEXT)")
    con.execute("CREATE TABLE state (key TEXT, value TEXT)")
    con.execute("INSERT INTO auth_kv VALUES ('kirocli:odic:token', ?)", (json.dumps({"access_token": TOKEN}),))
    con.execute("INSERT INTO state VALUES ('api.codewhisperer.profile', ?)",
                (json.dumps({"arn": "arn:aws:codewhisperer:eu-central-1:123:profile/abc"}),))
    con.commit()
    con.close()
    calls = stub_http(monkeypatch, aikit, {
        "https://q.eu-central-1.amazonaws.com/": (200, {
            "usageBreakdownList": [{"resourceType": "CREDIT", "usageLimitWithPrecision": 1000,
                                    "currentUsageWithPrecision": 250.5, "nextDateReset": 1_800_000_000}],
            "subscriptionInfo": {"subscriptionTitle": "KIRO PRO"},
        }),
    })
    r = aikit.probe_usage("kiro")
    assert r["status"] == "ok" and r["plan"] == "KIRO PRO"
    assert r["credits"]["remaining"] == 749.5 and r["windows"][0]["unit"] == "credits"
    assert calls[0]["headers"]["X-Amz-Target"] == "AmazonCodeWhispererService.GetUsageLimits"
    assert calls[0]["body"] == {"profileArn": "arn:aws:codewhisperer:eu-central-1:123:profile/abc"}


def test_cursor_probe_builds_session_cookie_from_state_db(aikit, monkeypatch):
    import base64
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "auth0|user_42"}).encode()).rstrip(b"=").decode()
    jwt = f"hdr.{payload}.sig"
    db = aikit._test_home / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    db.parent.mkdir(parents=True)
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
    con.execute("INSERT INTO ItemTable VALUES ('cursorAuth/accessToken', ?)", (jwt,))
    con.commit()
    con.close()
    calls = stub_http(monkeypatch, aikit, {
        "https://cursor.com/api/usage-summary": (200, {
            "membershipType": "pro", "billingCycleEnd": "2026-02-01T00:00:00Z",
            "individualUsage": {"plan": {"used": 12.5, "limit": 20}, "onDemand": {"used": 3, "limit": 50}},
        }),
    })
    r = aikit.probe_usage("cursor")
    assert r["status"] == "ok" and r["plan"] == "pro"
    assert r["windows"][0]["used"] == 12.5 and r["spend"]["limit"] == 50
    assert calls[0]["headers"]["Cookie"] == f"WorkosCursorSessionToken=user_42%3A%3A{jwt}"


def test_amp_probe_uses_env_key_and_balance_rpc(aikit, monkeypatch):
    monkeypatch.setenv("AMP_API_KEY", TOKEN)
    calls = stub_http(monkeypatch, aikit, {
        "https://ampcode.com/api/internal?userDisplayBalanceInfo": (200, {"result": {
            "email": "me@example.com", "plan": "Pro", "freeQuota": 10, "freeUsed": 4, "individualCredits": 55.25}}),
    })
    r = aikit.probe_usage("amp")
    assert r["status"] == "ok" and r["account"] == "me@example.com"
    assert r["windows"][0]["used_pct"] == 40.0 and r["credits"]["remaining"] == 55.25
    assert calls[0]["method"] == "POST" and calls[0]["body"] == {"method": "userDisplayBalanceInfo"}


def test_droid_probe_reads_factory_env_file(aikit, monkeypatch):
    env = aikit._test_home / ".factory" / ".env"
    env.parent.mkdir()
    env.write_text(f'export FACTORY_API_KEY="{TOKEN}"\n')
    stub_http(monkeypatch, aikit, {
        "https://app.factory.ai/api/organization/subscription/usage": (200, {
            "plan": "Pro", "endDate": "2026-02-01T00:00:00Z",
            "standard": {"usage": 100, "allowance": 400}, "premium": {"usage": 5, "allowance": 10},
            "overage": {"used": 1.5, "limit": 10}}),
    })
    r = aikit.probe_usage("droid")
    assert r["status"] == "ok" and r["source"].endswith(".env")
    assert [w["label"] for w in r["windows"]] == ["standard tokens", "premium tokens"]
    assert r["windows"][0]["used_pct"] == 25.0 and r["spend"]["amount"] == 1.5


def test_kilo_probe_sums_credit_blocks_in_musd(aikit, monkeypatch):
    write_json(aikit._test_home / ".local" / "share" / "kilo" / "auth.json", {"kilo": {"access": TOKEN}})
    calls = stub_http(monkeypatch, aikit, {
        "https://app.kilo.ai/api/trpc/user.getCreditBlocks": (200, {"result": {"data": {"json": {
            "blocks": [{"balance_mUsd": 1500}, {"balance_mUsd": 250}]}}}}),
    })
    r = aikit.probe_usage("kilo")
    assert r["status"] == "ok" and r["credits"] == {"remaining": 1.75, "total": None, "used": None, "unit": "USD"}
    assert "input=" in calls[0]["url"]


def test_opencode_go_probe_reads_auth_json_windows(aikit, monkeypatch):
    write_json(aikit._test_home / ".local" / "share" / "opencode" / "auth.json",
               {"opencode-go": {"type": "api", "key": TOKEN}})
    stub_http(monkeypatch, aikit, {
        "https://opencode.ai/zen/go/v1/usage": (200, {"usage": {
            "rolling": {"usagePercent": 12, "resetsAt": "2026-01-01T05:00:00Z"},
            "weekly": {"used": 30, "limit": 100},
            "monthly": {"usagePercent": 8}}}),
    })
    r = aikit.probe_usage("opencode")
    assert r["status"] == "ok" and [w["label"] for w in r["windows"]] == ["rolling window", "weekly", "monthly"]
    assert r["windows"][1]["used_pct"] == 30.0


def test_openrouter_probe_combines_key_and_credits(aikit, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", TOKEN)
    stub_http(monkeypatch, aikit, {
        "https://openrouter.ai/api/v1/key": (200, {"data": {"label": "laptop", "usage": 3.2, "limit": 10, "is_free_tier": False}}),
        "https://openrouter.ai/api/v1/credits": (200, {"data": {"total_credits": 50, "total_usage": 20}}),
    })
    r = aikit.probe_usage("openrouter")
    assert r["status"] == "ok" and r["account"] == "laptop" and r["plan"] == "paid"
    assert r["credits"]["remaining"] == 30 and r["windows"][0]["used_pct"] == 32.0


def test_devin_probe_requires_org_id(aikit, monkeypatch):
    monkeypatch.setenv("DEVIN_BEARER_TOKEN", TOKEN)
    stub_http(monkeypatch, aikit, {})
    assert aikit.probe_usage("devin")["status"] == "unauthenticated"
    monkeypatch.setenv("DEVIN_ORG_ID", "org-abc")
    calls = stub_http(monkeypatch, aikit, {
        "https://app.devin.ai/api/org-abc/billing/quota/usage": (200, {"used": 40, "limit": 250, "plan": "Team"}),
    })
    r = aikit.probe_usage("devin")
    assert r["status"] == "ok" and r["windows"][0]["unit"] == "ACU" and r["windows"][0]["used_pct"] == 16.0
    assert calls[0]["headers"]["Authorization"] == f"Bearer {TOKEN}"


def test_every_probe_degrades_to_unauthenticated_in_empty_home(aikit, monkeypatch):
    calls = stub_http(monkeypatch, aikit, {})
    results = [aikit.probe_usage(k) for k in aikit.USAGE_PROBES]
    assert {r["status"] for r in results} == {"unauthenticated"}
    assert calls == []


# --- collection & rendering ---------------------------------------------------

def test_collect_usage_keeps_registry_order(aikit, monkeypatch):
    monkeypatch.setattr(aikit, "probe_usage", lambda k: aikit.usage_result(k, aikit.USAGE_OK))
    assert [r["provider"] for r in aikit.collect_usage(["grok", "codex", "claude"])] == ["grok", "codex", "claude"]


def test_do_usage_rejects_unknown_provider(aikit):
    with pytest.raises(aikit.AikitError, match="unknown provider"):
        aikit.do_usage(["nope"])


def test_do_usage_json_output_never_contains_tokens(aikit, monkeypatch, capsys):
    write_json(aikit._test_home / ".codex" / "auth.json", {"tokens": {"access_token": TOKEN}})
    stub_http(monkeypatch, aikit, {"https://chatgpt.com/backend-api/wham/usage": (200, {"plan_type": "pro"})})
    aikit.do_usage(["codex", "goose"], as_json=True)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert [d["provider"] for d in data] == ["codex", "goose"]
    assert data[0]["plan"] == "pro" and data[1]["status"] == "unsupported"
    assert TOKEN not in out


def test_fmt_window_renders_percent_and_counts(aikit):
    assert aikit._fmt_window(aikit.usage_window("weekly", used_pct=42)) == "weekly: 42% used"
    assert aikit._fmt_window(aikit.usage_window("credits", used=10, limit=100, unit="credits")) == "credits: 10/100 credits (10%)"
    assert "(resets in" in aikit._fmt_window(aikit.usage_window("x", used_pct=1, resets_at=4_000_000_000))


def test_usage_cli_help_smoke():
    res = subprocess.run([sys.executable, str(REPO_ROOT / "aikit"), "usage", "--help"],
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0
    assert "--json" in res.stdout and "--all" in res.stdout
