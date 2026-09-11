"""Installation-aware updates, including the mixed-manager Omarchy report."""

import json
import os
import shlex
import sys

import pytest


@pytest.fixture
def aikit(tool_loader, monkeypatch, tmp_path):
    m = tool_loader("aikit")
    monkeypatch.setattr(m.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    monkeypatch.setattr(m, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(m, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(m, "_npm_global_bin_dirs", lambda: [])
    m.UPDATE_CHECK_CACHE.clear()
    m.INSTALL_MANAGER_CACHE.clear()
    return m


def executable(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return path


def node_install(root, package, name, *, bun=False):
    tree = root / ("install/global/node_modules" if bun else "lib/node_modules")
    package_dir = tree / package
    binary = executable(package_dir / "cli.js", 'echo "1.0.0"\n')
    (package_dir / "package.json").write_text(json.dumps({"name": package}))
    link = root / "bin" / name
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(binary)
    return link


def test_npm_update_targets_active_prefix_not_aikits_default(aikit, monkeypatch, tmp_path):
    root = tmp_path / "node 22"
    node_install(root, "@openai/codex", "codex")
    monkeypatch.setenv("PATH", str(root / "bin"))
    manager, command = aikit.detect_install_manager("codex")
    assert manager == "npm"
    assert shlex.split(command) == ["npm", "install", "-g", "@openai/codex@latest", "--prefix", str(root)]
    assert aikit.resolve_update_cmd("codex") == command


def test_omp_bun_install_is_updated_in_place(aikit, monkeypatch, tmp_path):
    root = tmp_path / ".bun"
    node_install(root, "@oh-my-pi/pi-coding-agent", "omp", bun=True)
    monkeypatch.setenv("PATH", str(root / "bin"))
    manager, command = aikit.detect_install_manager("omp")
    assert manager == "bun"
    assert "@oh-my-pi/pi-coding-agent@latest" in shlex.split(command)
    assert aikit._update_plan("omp")["env"]["BUN_INSTALL_GLOBAL_DIR"] == str(root / "install/global")
    assert aikit.resolve_update_cmd("omp") == command


@pytest.mark.parametrize("relocated", [False, True])
def test_bun_update_accepts_only_supported_flags_and_preserves_destinations(aikit, monkeypatch, tmp_path, relocated):
    root = tmp_path / "custom packages" if relocated else tmp_path / ".bun/install/global"
    bin_dir = tmp_path / "custom binaries" if relocated else tmp_path / ".bun/bin"
    package = root / "node_modules/@oh-my-pi/pi-coding-agent"
    version = package / "version"
    binary = executable(package / "cli.js", f"/bin/cat {shlex.quote(str(version))}\n")
    version.write_text("18.1.15")
    bin_dir.mkdir(parents=True)
    (bin_dir / "omp").symlink_to(binary)
    if relocated:
        monkeypatch.setenv("BUN_INSTALL_GLOBAL_DIR", str(root))
    else:
        # A conflicting inherited destination must not redirect the update.
        monkeypatch.setenv("BUN_INSTALL_GLOBAL_DIR", str(tmp_path / "wrong packages"))
    monkeypatch.setenv("BUN_INSTALL_BIN", str(tmp_path / "wrong bin"))
    executable(bin_dir / "bun", f'''if [ "$#" -ne 3 ] || [ "$1" != install ] || [ "$2" != -g ] || [ "$3" != @oh-my-pi/pi-coding-agent@latest ]; then
  echo 'Unsupported bun install arguments' >&2; exit 64
fi
[ "$BUN_INSTALL_GLOBAL_DIR" = {shlex.quote(str(root))} ] || exit 65
[ "$BUN_INSTALL_BIN" = {shlex.quote(str(bin_dir))} ] || exit 66
echo 18.1.17 > "$BUN_INSTALL_GLOBAL_DIR/node_modules/@oh-my-pi/pi-coding-agent/version"
''')
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(aikit, "fetch_latest_version", lambda _: "18.1.17")
    assert aikit.do_update(["omp"], force=True) == 0
    assert aikit.detect_agent_version("omp") == "18.1.17"
    assert not (tmp_path / "wrong packages").exists()
    assert not (tmp_path / "wrong bin").exists()


def test_hermes_unrecognized_check_is_unknown_not_current(aikit, monkeypatch, tmp_path):
    executable(tmp_path / "bin/hermes", 'echo "Checking... remote fetch unavailable"\n')
    status = aikit.check_update_status("hermes")
    assert status["available"] is None
    assert not aikit.should_skip_update("hermes")[0]


def test_update_removes_inherited_python_and_node_injection(aikit, monkeypatch, tmp_path):
    marker = tmp_path / "version"
    marker.write_text("1.0.0")
    executable(tmp_path / "bin/grok", f'''if [ "$1" = "--version" ]; then
  /bin/cat {shlex.quote(str(marker))}
elif [ "$2" = "--check" ]; then
  echo '{{"updateAvailable": false, "currentVersion": "2.0.0"}}'
elif [ "$1" = "update" ]; then
  [ -z "${{PYTHONPATH+x}}" ] && [ -z "${{NODE_OPTIONS+x}}" ] || exit 17
  echo 2.0.0 > {shlex.quote(str(marker))}
fi
''')
    monkeypatch.setenv("PYTHONPATH", "/wrong/python")
    monkeypatch.setenv("NODE_OPTIONS", "--require=/wrong/node.js")
    outcome, _, _ = aikit.execute_agent_update("grok")
    assert outcome["status"] == "upgraded"
    assert marker.read_text().strip() == "2.0.0"


def test_shadowed_binary_noop_is_failure_with_paths(aikit, monkeypatch, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    executable(first / "grok", 'echo 1.0.0\n')
    executable(second / "grok", 'echo 2.0.0\n')
    monkeypatch.setenv("PATH", os.pathsep.join(map(str, (first, second))))
    monkeypatch.setattr(aikit, "check_update_status", lambda *a, **k: {"available": True, "latest": "2.0.0"})
    outcome, _, _ = aikit.execute_agent_update("grok")
    assert outcome["status"] == "unchanged_outdated"
    assert outcome["exit_code"] == 1
    assert str(first / "grok") in outcome["error"]
    assert str(second / "grok") in outcome["error"]
    assert "PATH" in outcome["error"]


@pytest.mark.parametrize("foreign,helper,manager", [(False, None, "pacman"), (True, "paru", "aur"), (True, "yay", "aur")])
def test_arch_owner_comes_from_database_not_binary_name(aikit, monkeypatch, tmp_path, foreign, helper, manager):
    binary = executable(tmp_path / "bin/codex", "echo 1.0.0\n")
    executable(tmp_path / "bin/pacman", f'''case "$1" in
  -Qoq) echo openai-codex-bin ;;
  -Qm) exit {0 if foreign else 1} ;;
esac
''')
    if helper:
        executable(tmp_path / "bin" / helper, "exit 0\n")
    owner, command = aikit.detect_install_manager("codex")
    assert owner == manager
    assert command is None  # system mutations require the full system workflow
    reason = aikit._update_plan("codex")["error"]
    assert "openai-codex-bin" in reason
    assert "-Syu" in reason
    assert aikit._installed_bin_path("codex") == binary


def test_linux_and_pacman_presence_do_not_imply_ownership(aikit, tmp_path):
    node_install(tmp_path, "@openai/codex", "codex")
    executable(tmp_path / "bin/pacman", "exit 1\n")
    assert aikit.detect_install_manager("codex")[0] == "npm"


def test_aur_without_helper_fails_without_reinstalling(aikit, tmp_path):
    executable(tmp_path / "bin/codex", "echo 1.0.0\n")
    executable(tmp_path / "bin/pacman", "echo codex-bin\n")
    outcome, _, _ = aikit.execute_agent_update("codex")
    assert outcome["status"] == "failed"
    assert "paru -Syu" in outcome["error"]
    assert "codex-bin" in outcome["error"]


@pytest.mark.parametrize("manager,variable,subdir", [("pipx", "PIPX_HOME", "venvs"), ("uv", "UV_TOOL_DIR", "")])
def test_relocated_python_manager_root_is_retained(aikit, monkeypatch, tmp_path, manager, variable, subdir):
    root = tmp_path / "custom tools"
    monkeypatch.setenv(variable, str(root))
    binary = executable(root / subdir / "aider-chat/bin/aider", "echo 1.0.0\n")
    (tmp_path / "bin").mkdir(exist_ok=True)
    (tmp_path / "bin/aider").symlink_to(binary)
    plan = aikit._update_plan("aider")
    assert plan["manager"] == manager
    assert plan["env"][variable] == str(root)
    assert plan["commands"][0][-1] == "aider-chat"


def test_pip_uses_launcher_interpreter_and_record(aikit, monkeypatch, tmp_path):
    # An isolated real venv with a synthetic wheel RECORD: no network or pip
    # install is needed to prove interpreter/distribution ownership.
    import subprocess
    venv = tmp_path / "python-env"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    python = venv / "bin/python"
    binary = executable(venv / "bin/aider", "")
    binary.write_text(f"#!{python}\nprint('1.0.0')\n")
    site = next((venv / "lib").glob("python*/site-packages"))
    dist = site / "aider_chat-1.0.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Name: aider-chat\nVersion: 1.0.0\n")
    (dist / "RECORD").write_text("../../../bin/aider,,\n")
    monkeypatch.setenv("PATH", str(venv / "bin"))
    manager, command = aikit.detect_install_manager("aider")
    assert manager == "pip"
    assert shlex.split(command)[:4] == [str(python), "-m", "pip", "--isolated"]
    assert shlex.split(command)[-1] == "aider-chat"


def test_cargo_uses_receipt_crate_and_root(aikit, monkeypatch, tmp_path):
    root = tmp_path / "custom cargo"
    executable(root / "bin/codex", "echo 1.0.0\n")
    (root / ".crates2.json").write_text(json.dumps({"installs": {
        "codex-cli 1.0.0 (registry+https://github.com/rust-lang/crates.io-index)": {"bins": ["codex"]}
    }}))
    monkeypatch.setenv("PATH", str(root / "bin"))
    manager, command = aikit.detect_install_manager("codex")
    assert manager == "cargo"
    assert shlex.split(command) == ["cargo", "install", "codex-cli", "--locked", "--root", str(root)]


def test_windows_npm_cmd_shim_uses_its_own_prefix(aikit, monkeypatch, tmp_path):
    root = tmp_path / "AppData/Roaming/npm"
    shim = executable(root / "codex.cmd", '"%dp0%node_modules\\@openai\\codex\\bin\\codex.js"\n')
    monkeypatch.setattr(aikit, "_installed_bin_path", lambda _: shim)
    monkeypatch.setattr(aikit, "_CURRENT_PLATFORM", "Windows")
    manager, args, _, _ = aikit._manager_installation("codex")
    assert manager == "npm"
    assert args == ["npm", "install", "-g", "@openai/codex@latest", "--prefix", str(root)]


@pytest.mark.parametrize("key,variable", [("codex", "CODEX_INSTALL_DIR"), ("omp", "PI_INSTALL_DIR")])
def test_standalone_installer_targets_active_directory(aikit, monkeypatch, tmp_path, key, variable):
    binary = executable(tmp_path / "custom bin" / key, "echo 1.0.0\n")
    monkeypatch.setenv("PATH", str(binary.parent))
    plan = aikit._update_plan(key)
    assert plan["env"][variable] == str(binary.parent)
    assert "curl" in plan["commands"][0]
    assert plan["commands"][0] != "codex update"


@pytest.mark.parametrize("native_exit", [0, 3])
def test_native_noop_or_failure_retries_detected_manager(aikit, monkeypatch, tmp_path, native_exit):
    shim = node_install(tmp_path, "@xai/grok", "grok")
    actual = shim.resolve()
    marker = tmp_path / "version"
    marker.write_text("1.0.0")
    actual.write_text(f'''#!/bin/sh
if [ "$1" = "--version" ]; then /bin/cat {shlex.quote(str(marker))}; else exit {native_exit}; fi
''')
    executable(tmp_path / "bin/npm", f'echo 2.0.0 > {shlex.quote(str(marker))}\n')
    monkeypatch.setattr(aikit, "check_update_status", lambda *a, **k: {"available": marker.read_text().strip() != "2.0.0", "latest": "2.0.0"})
    outcome, _, _ = aikit.execute_agent_update("grok")
    assert outcome["status"] == "upgraded"
    assert len(outcome["attempts"]) == 2
    assert outcome["attempts"][0].endswith("grok update")
    assert outcome["attempts"][1].startswith("npm install")


@pytest.mark.parametrize("stdout", ["{}", "[]", '{"updateAvailable": "false"}', "not json"])
def test_grok_malformed_check_is_unknown(aikit, tmp_path, stdout):
    executable(tmp_path / "bin/grok", f"echo {shlex.quote(stdout)}\n")
    assert aikit.check_update_status("grok")["available"] is None


def test_grok_check_cannot_override_actual_old_binary_version(aikit, tmp_path):
    executable(tmp_path / "bin/grok", '''if [ "$1" = "--version" ]; then echo 1.0.0;
else echo '{"updateAvailable": false, "currentVersion": "2.0.0", "latestVersion": "2.0.0"}'; fi
''')
    assert aikit.check_update_status("grok")["available"] is True


def test_removed_binary_is_failure_and_cli_exits_nonzero(aikit, monkeypatch, tmp_path):
    binary = executable(tmp_path / "bin/grok", '''if [ "$1" = "--version" ]; then echo 1.0.0;
else /bin/rm "$0"; fi
''')
    assert aikit.do_update(["grok"], force=True) == 1
    assert not binary.exists()


def test_dashboard_noop_reports_failure(aikit, monkeypatch, tmp_path):
    executable(tmp_path / "bin/grok", "echo 1.0.0\n")
    monkeypatch.setattr(aikit, "check_update_status", lambda *a, **k: {"available": True, "latest": "2.0.0"})
    app = aikit.create_flask_app()
    response = app.test_client().post("/api/update/grok?force=1")
    result = response.get_json()
    assert result["success"] is False
    assert result["status"] == "unchanged_outdated"
    assert result["exit_code"] != 0
    assert "active executable" in result["stderr"]


@pytest.mark.parametrize("key,owner,old,new", [
    ("claude", "native", "2.1.266", "2.1.267"),
    ("cursor", "native", "2026.09.08-6caf4ff", "2026.09.10-fd3934a"),
    ("hermes", "native", "2.23.0", "2.24.0"),
    ("codex", "npm", "0.153.4", "0.154.0"),
    ("grok", "native", "1.0.13", "1.0.25"),
    ("omp", "bun", "18.1.15", "18.1.17"),
    ("crush", "npm", "0.92.0", "0.93.1"),
    ("devin", "installer", "3000.6.14", "3000.10.21"),
    ("opencode", "native", "1.18.29", "1.18.30"),
    ("copilot", "npm", "1.0.82", "1.0.83"),
    ("pi", "native", "0.85.0", "0.85.1"),
    ("gemini", "npm", "0.59.0", "0.59.1"),
])
def test_omarchy_mixed_installations_update_all_reported_agents(aikit, monkeypatch, tmp_path, key, owner, old, new):
    """Real subprocess dry run with disposable binaries/managers; no downloads."""
    marker = tmp_path / "version"
    marker.write_text(old)
    quoted = shlex.quote(str(marker))
    agent = aikit.AGENTS[key]
    write_version = f"echo {shlex.quote(new)} > {quoted}\n"
    native = f'''if [ "$1" = "--version" ]; then /bin/cat {quoted};
elif [ "$2" = "--check" ]; then
  if [ "$(/bin/cat {quoted})" = "{new}" ]; then
    echo '{{"updateAvailable": false, "latestVersion": "{new}"}}'
    echo 'Already up to date.' >&2
  else
    echo '{{"updateAvailable": true, "latestVersion": "{new}"}}'
    echo 'Update available' >&2
  fi
else {write_version}fi
'''
    if key == "grok":
        # JSON needs stdout alone, and an alias must still bind to Grok's tree.
        native = native.replace("echo 'Already up to date.' >&2", ":").replace("echo 'Update available' >&2", ":")
    if owner in ("npm", "bun"):
        package = agent["version_check"].get("package") or {"codex": "@openai/codex", "copilot": "@github/copilot"}[key]
        shim = node_install(tmp_path, package, agent["bin"], bun=owner == "bun")
        executable(shim.resolve(), f"/bin/cat {quoted}\n")
        executable(tmp_path / "bin" / owner, write_version)
    else:
        executable(tmp_path / "bin" / agent["bin"], native if owner == "native" else f"/bin/cat {quoted}\n")
    if owner == "installer":
        (tmp_path / "bin/bash").symlink_to("/bin/bash")
        executable(tmp_path / "bin/curl", f"printf '%s\\n' {shlex.quote(write_version)}\n")
    monkeypatch.setattr(aikit, "fetch_latest_version", lambda _: new)
    outcome, _, _ = aikit.execute_agent_update(key)
    assert outcome["status"] == "upgraded", outcome
    assert aikit.detect_agent_version(key) == new
    assert outcome["new"] == new


def test_native_update_that_replaces_path_is_reresolved(aikit, monkeypatch, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    executable(first / "grok", '''if [ "$1" = "--version" ]; then echo 1.0.0;
else /bin/rm "$0"; fi
''')
    executable(second / "grok", 'echo 2.0.0\n')
    monkeypatch.setenv("PATH", os.pathsep.join(map(str, (first, second))))
    monkeypatch.setattr(aikit, "check_update_status", lambda *a, **k: {"available": False, "latest": "2.0.0"})
    outcome, _, _ = aikit.execute_agent_update("grok")
    assert outcome["status"] == "upgraded"
    assert outcome["path_before"] == str(first / "grok")
    assert outcome["path_after"] == str(second / "grok")


def test_maintenance_environment_preserves_identity_and_network(aikit, monkeypatch):
    for key in ("HOME", "PATH", "HTTPS_PROXY", "SSL_CERT_FILE", "PIPX_HOME"):
        monkeypatch.setenv(key, "preserved")
    for key in ("VIRTUAL_ENV", "PYTHONPATH", "GIT_DIR", "npm_config_prefix", "BASH_ENV"):
        monkeypatch.setenv(key, "removed")
    code, output, _ = aikit.run([sys.executable, "-c", "import os,json; print(json.dumps(dict(os.environ)))"], shell=False, env=aikit._maintenance_env())
    assert code == 0
    env = json.loads(output)
    assert all(env[k] == "preserved" for k in ("HOME", "PATH", "HTTPS_PROXY", "SSL_CERT_FILE", "PIPX_HOME"))
    assert not any(k in env for k in ("VIRTUAL_ENV", "PYTHONPATH", "GIT_DIR", "npm_config_prefix", "BASH_ENV"))


def test_mise_node_runtime_does_not_claim_npm_package(aikit, monkeypatch, tmp_path):
    root = tmp_path / ".local/share/mise/installs/node/22.0.0"
    node_install(root, "@openai/codex", "codex")
    monkeypatch.setenv("PATH", str(root / "bin"))
    assert aikit.detect_install_manager("codex")[0] == "npm"


def test_bun_isolated_linker_uses_global_root_and_package(aikit, monkeypatch, tmp_path):
    root = tmp_path / ".bun/install/global"
    target = executable(root / "node_modules/.bun/@oh-my-pi+pi-coding-agent@18.1.15/node_modules/@oh-my-pi/pi-coding-agent/cli.js", "echo 18.1.15\n")
    link = tmp_path / "bin/omp"
    link.parent.mkdir()
    link.symlink_to(target)
    manager, command = aikit.detect_install_manager("omp")
    assert manager == "bun"
    assert "@oh-my-pi/pi-coding-agent@latest" in shlex.split(command)
    assert aikit._update_plan("omp")["env"]["BUN_INSTALL_GLOBAL_DIR"] == str(root)


def test_paths_with_shell_metacharacters_are_passed_as_argv(aikit, monkeypatch, tmp_path):
    root = tmp_path / "bin with spaces & dollar$"
    marker = tmp_path / "version"
    marker.write_text("1.0.0")
    executable(root / "grok", f'''if [ "$1" = "--version" ]; then /bin/cat {shlex.quote(str(marker))};
else echo 2.0.0 > {shlex.quote(str(marker))}; fi
''')
    monkeypatch.setenv("PATH", str(root))
    monkeypatch.setattr(aikit, "check_update_status", lambda *a, **k: {"available": False})
    assert aikit.execute_agent_update("grok")[0]["status"] == "upgraded"
