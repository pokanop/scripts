"""Regressions from POK-387's first review round."""

import shlex
import sys

import pytest

from test_aikit_updates import aikit, executable, node_install


def current_hermes(tmp_path, check="Release check unavailable right now"):
    return executable(tmp_path / "bin/hermes", f'''if [ "$1" = "--version" ]; then echo 2.24.0;
elif [ "$2" = "--check" ]; then echo {shlex.quote(check)};
else echo 'Nothing to do.'; fi
''')


def test_current_hermes_inconclusive_check_is_not_failure(aikit, tmp_path, capsys):
    current_hermes(tmp_path)
    outcome, _, _ = aikit.execute_agent_update("hermes")
    assert outcome["status"] == "unchanged"
    assert outcome["exit_code"] == 0
    assert "error" not in outcome
    assert aikit.do_update(["hermes"]) == 0
    output = capsys.readouterr()
    assert "inconclusive" in output.out
    assert "Failed" not in output.out + output.err


def test_inconclusive_update_dashboard_remains_successful(aikit, tmp_path):
    current_hermes(tmp_path)
    result = aikit.create_flask_app().test_client().post("/api/update/hermes").get_json()
    assert result["status"] == "unchanged"
    assert result["success"] is True
    assert result["exit_code"] == 0


@pytest.mark.parametrize("check", ["You're on the latest release.", "Latest version already installed.", "Already on the latest version.", "No updates found.", "No update available."])
def test_explicit_current_phrasing_is_recognized(aikit, tmp_path, check):
    current_hermes(tmp_path, check)
    assert aikit.should_skip_update("hermes")[0] is True


def test_conflicting_text_verdicts_stay_inconclusive(aikit):
    spec = aikit.AGENTS["hermes"]["version_check"]
    assert aikit._text_update_availability(spec, "Already up to date.\nUpdate available.") is None


def test_spawn_failure_retries_manager_with_real_subprocess(aikit, monkeypatch, tmp_path):
    shim = node_install(tmp_path, "@xai/grok", "grok")
    marker = tmp_path / "version"
    marker.write_text("1.0.0")
    executable(shim.resolve(), f"/bin/cat {shlex.quote(str(marker))}\n")
    executable(tmp_path / "bin/npm", f"echo 2.0.0 > {shlex.quote(str(marker))}\n")
    # The shim disappears after planning but before spawning the native updater.
    original_plan = aikit._update_plan
    def plan(key):
        result = original_plan(key)
        result["commands"][0][0] = str(tmp_path / "removed/grok")
        return result
    monkeypatch.setattr(aikit, "_update_plan", plan)
    monkeypatch.setattr(aikit, "check_update_status", lambda *a, **k: {"available": False})
    outcome, _, _ = aikit.execute_agent_update("grok")
    assert outcome["status"] == "upgraded"
    assert len(outcome["attempts"]) == 2
    assert outcome["attempts"][-1].startswith("npm install")


@pytest.mark.parametrize("variable", ["NPM_CONFIG_PREFIX", "npm_config_prefix"])
def test_npm_discovery_and_uninstall_keep_environment_prefix(aikit, monkeypatch, tmp_path, variable):
    root = tmp_path / "env prefix"
    node_install(root, "@google/gemini-cli", "gemini")
    monkeypatch.setenv(variable, str(root))
    executable(tmp_path / "bin/npm", f'echo "${{{variable}}}"\n')
    assert root in aikit._npm_global_prefixes()
    assert str(root) in aikit.npm_uninstall_cmd("@google/gemini-cli")
    assert str(aikit._NPM_INSTALL_PREFIX) not in aikit.npm_uninstall_cmd("@google/gemini-cli")


@pytest.mark.parametrize("foreign", [False, True])
def test_arch_updates_only_query_and_explain_system_workflow(aikit, tmp_path, foreign):
    marker = tmp_path / "commands"
    executable(tmp_path / "bin/hermes", 'echo 2.24.0\n')
    executable(tmp_path / "bin/pacman", f'''echo "$1" >> {shlex.quote(str(marker))}
case "$1" in
  -Qoq) echo hermes-agent ;;
  -Qm) exit {0 if foreign else 1} ;;
  *) exit 33 ;;
esac
''')
    outcome, _, _ = aikit.execute_agent_update("hermes")
    assert outcome["status"] == "failed"
    assert "hermes-agent" in outcome["error"]
    assert "-Syu" in outcome["error"]
    assert all(line in ("-Qoq", "-Qm") for line in marker.read_text().splitlines())
    assert not outcome.get("attempts")  # no native/system mutation


def test_manager_probes_are_cached_until_binary_changes(aikit, tmp_path):
    marker = tmp_path / "queries"
    binary = executable(tmp_path / "bin/codex", "echo 1.0.0\n")
    executable(tmp_path / "bin/pacman", f'''echo query >> {shlex.quote(str(marker))}
if [ "$1" = "-Qoq" ]; then echo codex; else exit 1; fi
''')
    for _ in range(3):
        aikit.resolve_update_cmd("codex")
    assert len(marker.read_text().splitlines()) == 2
    binary.write_text("#!/bin/sh\necho 2.0.0\n# updated executable\n")
    aikit.resolve_update_cmd("codex")
    assert len(marker.read_text().splitlines()) == 4


def test_dashboard_error_response_is_bounded(aikit, monkeypatch, tmp_path):
    current_hermes(tmp_path)
    monkeypatch.setattr(aikit, "execute_agent_update", lambda _: ({"status": "failed", "exit_code": 1, "error": "x" * 2000}, "", ""))
    result = aikit.create_flask_app().test_client().post("/api/update/hermes?force=1").get_json()
    assert len(result["stderr"]) == 500


@pytest.mark.parametrize("manager", ["brew", "mise", "pipx", "uv", "pip", "cargo"])
def test_receipt_owner_handles_updates_without_native_overwrite(aikit, monkeypatch, tmp_path, manager):
    marker = tmp_path / "version"
    marker.write_text("1.0.0")
    binary = executable(tmp_path / "bin/grok", f'''if [ "$1" = "--version" ]; then /bin/cat {shlex.quote(str(marker))};
else echo 'native updater must not run' >&2; exit 44; fi
''')
    updater = executable(tmp_path / "bin" / manager, f"echo 2.0.0 > {shlex.quote(str(marker))}\n")
    monkeypatch.setattr(aikit, "_manager_installation", lambda _: (manager, [str(updater), "upgrade"], {}, ""))
    monkeypatch.setattr(aikit, "check_update_status", lambda *a, **k: {"available": False})
    outcome, _, stderr = aikit.execute_agent_update("grok")
    assert outcome["status"] == "upgraded"
    assert outcome["attempts"] == [f"{updater} upgrade"]
    assert "native updater" not in stderr
    # Even a failed manager must not trigger an untracked native overwrite.
    executable(updater, "exit 4\n")
    outcome, _, stderr = aikit.execute_agent_update("grok")
    assert outcome["status"] == "failed"
    assert len(outcome["attempts"]) == 1
    assert "native updater" not in stderr


def test_real_timeout_stops_before_manager_retry(aikit, monkeypatch, tmp_path):
    node_install(tmp_path, "@xai/grok", "grok")
    original_plan, original_run = aikit._update_plan, aikit.run
    def plan(key):
        result = original_plan(key)
        result["commands"][0] = [sys.executable, "-c", "import time; time.sleep(30)"]
        return result
    def short_timeout(command, **kwargs):
        if isinstance(command, list) and command[0] == sys.executable:
            kwargs["timeout"] = 0.03
        return original_run(command, **kwargs)
    monkeypatch.setattr(aikit, "_update_plan", plan)
    monkeypatch.setattr(aikit, "run", short_timeout)
    outcome, _, _ = aikit.execute_agent_update("grok")
    assert outcome["status"] == "failed"
    assert outcome["updater_exit_code"] == -1
    assert len(outcome["attempts"]) == 1
    assert "timed out" in outcome["error"]


def test_update_reprobes_owner_even_with_warm_cache(aikit, tmp_path):
    marker = tmp_path / "queries"
    executable(tmp_path / "bin/codex", "echo 1.0.0\n")
    executable(tmp_path / "bin/pacman", f'''echo query >> {shlex.quote(str(marker))}
if [ "$1" = "-Qoq" ]; then echo codex; else exit 1; fi
''')
    aikit.resolve_update_cmd("codex")
    assert len(marker.read_text().splitlines()) == 2
    aikit.execute_agent_update("codex")
    assert len(marker.read_text().splitlines()) == 4
