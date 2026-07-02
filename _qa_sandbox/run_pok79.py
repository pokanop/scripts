#!/usr/bin/env python3
"""E2E sandbox harness for POK-79: verifies `aikit uninstall -y <key>` for all 11
curl-installed agents against the actual acceptance criteria:
  AC1: removes the binary from PATH (detect_agent_bin(key) is False + files gone)
  AC2: removes the agent entry from ~/.aikit/config.json
Each agent runs in an isolated HOME/PATH so the shared `agent` shim collisions
(cursor+grok) don't bleed between cases.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = REPO / "venv" / "bin" / "python"
AIOIT = REPO / "aikit"

# Binaries each real installer lays down (per registry + reviewed install scripts).
# key -> list of paths relative to HOME that the installer creates.
INSTALL_LAYOUT = {
    "claude":       [".local/bin/claude"],
    "antigravity":  [".local/bin/agy"],
    "cursor":       [".local/bin/cursor-agent", ".local/bin/agent"],
    "hermes":       [".local/bin/hermes"],
    "codex":        [".local/bin/codex"],
    "copilot":      [".local/bin/copilot"],
    # grok default layout: its own dir on PATH + shared agent shim in ~/.local/bin
    "grok":         [".grok/bin/grok", ".grok/bin/agent", ".local/bin/agent"],
    "kiro":         [".local/bin/kiro-cli", ".local/bin/kiro",
                     ".local/bin/kiro-cli-chat", ".local/bin/q"],
    "openclaw":     [".local/bin/openclaw"],
    "devin":        [".local/bin/devin"],
    "droid":        [".local/bin/droid"],
}

# dirs the installer adds to PATH (so shutil.which finds the binaries)
EXTRA_PATH_DIRS = [".local/bin", ".grok/bin"]


def write_binary(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\necho mock\n")
    path.chmod(0o755)


def run_case(home: Path, key: str):
    home.mkdir(parents=True, exist_ok=True)
    for rel in INSTALL_LAYOUT[key]:
        write_binary(home / rel)

    config = {"agents": {key: {"installed": True}}, "version": 1}
    (home / ".aikit").mkdir(exist_ok=True)
    (home / ".aikit" / "config.json").write_text(json.dumps(config))

    env = dict(os.environ)
    env["HOME"] = str(home)
    path_dirs = [str(home / d) for d in EXTRA_PATH_DIRS]
    # Fully isolated PATH: temp bins + only the core system dirs needed for
    # `rm`/`sh`. The runtime host has real agent binaries under ~/.local/bin
    # (agy, cursor-agent, agent, grok, droid) that must NOT leak into detection.
    env["PATH"] = os.pathsep.join(path_dirs + ["/usr/bin", "/bin"])
    env["NO_COLOR"] = "1"

    # sanity: agent is detected as installed BEFORE uninstall
    pre = probe(env, f"detect_agent_bin({key!r})")
    if not pre:
        return {"key": key, "passed": False, "reason": "setup failed: not detected before uninstall"}

    proc = subprocess.run(
        [str(PY), str(AIOIT), "uninstall", "-y", key],
        env=env, capture_output=True, text=True, timeout=60,
    )

    post = probe(env, f"detect_agent_bin({key!r})")
    leftover = [rel for rel in INSTALL_LAYOUT[key] if (home / rel).exists()]

    cfg_path = home / ".aikit" / "config.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    pruned = key not in cfg.get("agents", {})

    passed = (not post) and pruned and (not leftover) and proc.returncode == 0
    return {
        "key": key,
        "passed": passed,
        "exit_code": proc.returncode,
        "detected_after": post,
        "config_pruned": pruned,
        "leftover_files": leftover,
        "stderr_tail": (proc.stderr or "").strip().splitlines()[-1:] if proc.returncode else [],
    }


def probe(env, expr):
    code = (
        "import importlib.util,importlib.machinery as m;"
        "l=m.SourceFileLoader('aikit','aikit');"
        "s=importlib.util.spec_from_loader('aikit',l);"
        "mod=importlib.util.module_from_spec(s);l.exec_module(mod);"
        f"print('1' if mod.{expr} else '0')"
    )
    proc = subprocess.run([str(PY), "-c", code], env=env, capture_output=True, text=True, cwd=str(REPO))
    return proc.stdout.strip() == "1"


def run_combined_cursor_grok(home: Path):
    """Adversarial case: cursor + grok both installed, sharing the ~/.local/bin/agent
    shim. Uninstalling one must not break the other's detection, and each must prune
    its own config entry. This is the collision the PR review flagged."""
    home.mkdir(parents=True, exist_ok=True)
    for rel in INSTALL_LAYOUT["cursor"] + INSTALL_LAYOUT["grok"]:
        write_binary(home / rel)
    (home / ".aikit").mkdir(exist_ok=True)
    (home / ".aikit" / "config.json").write_text(
        json.dumps({"agents": {"cursor": {"installed": True}, "grok": {"installed": True}}, "version": 1}))

    env = dict(os.environ)
    env["HOME"] = str(home)
    env["PATH"] = os.pathsep.join([str(home / d) for d in EXTRA_PATH_DIRS] + ["/usr/bin", "/bin"])
    env["NO_COLOR"] = "1"

    out = {"scenario": "cursor+grok combined", "steps": []}
    # sanity: both detected before
    out["pre_cursor"] = probe(env, "detect_agent_bin('cursor')")
    out["pre_grok"] = probe(env, "detect_agent_bin('grok')")

    # 1) uninstall cursor only — grok must remain detected + still in config
    subprocess.run([str(PY), str(AIOIT), "uninstall", "-y", "cursor"],
                   env=env, capture_output=True, text=True, timeout=60)
    cfg = json.loads((home / ".aikit" / "config.json").read_text())
    out["steps"].append({
        "uninstalled": "cursor",
        "cursor_detected_after": probe(env, "detect_agent_bin('cursor')"),
        "cursor_pruned": "cursor" not in cfg["agents"],
        "grok_still_detected": probe(env, "detect_agent_bin('grok')"),
        "grok_still_in_config": "grok" in cfg["agents"],
    })

    # 2) uninstall grok — now both gone
    subprocess.run([str(PY), str(AIOIT), "uninstall", "-y", "grok"],
                   env=env, capture_output=True, text=True, timeout=60)
    cfg = json.loads((home / ".aikit" / "config.json").read_text())
    out["steps"].append({
        "uninstalled": "grok",
        "grok_detected_after": probe(env, "detect_agent_bin('grok')"),
        "grok_pruned": "grok" not in cfg["agents"],
    })

    s1, s2 = out["steps"]
    out["passed"] = (
        not s1["cursor_detected_after"] and s1["cursor_pruned"]
        and s1["grok_still_detected"] and s1["grok_still_in_config"]
        and not s2["grok_detected_after"] and s2["grok_pruned"]
    )
    return out


def main():
    import tempfile, shutil
    results = []
    for key in INSTALL_LAYOUT:
        tmp = Path(tempfile.mkdtemp(prefix=f"qa_{key}_"))
        try:
            results.append(run_case(tmp, key))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # adversarial combined scenario
    tmp = Path(tempfile.mkdtemp(prefix="qa_combined_"))
    combined = {}
    try:
        combined = run_combined_cursor_grok(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for r in results if r["passed"])
    print(f"\n=== POK-79 uninstall sandbox: {passed}/{len(results)} agents passed ===\n")
    print(f"{'AGENT':<14}{'AC1(detected_after)':<22}{'AC2(pruned)':<12}{'leftover_files':<28}RESULT")
    for r in results:
        print(f"{r['key']:<14}{str(r.get('detected_after')):<22}"
              f"{str(r.get('config_pruned')):<12}{str(r.get('leftover_files')):<28}"
              f"{'PASS' if r['passed'] else 'FAIL'}")
        if not r["passed"] and r.get("stderr_tail"):
            print(f"            stderr: {r['stderr_tail']}")

    print(f"\n=== combined cursor+grok: {'PASS' if combined.get('passed') else 'FAIL'} ===")
    for st in combined.get("steps", []):
        print("   ", st)

    out = REPO / "_qa_sandbox" / "results.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"results": results, "combined": combined,
                               "passed": passed, "total": len(results)}, indent=2))
    print(f"\nresults -> {out}")
    all_ok = passed == len(results) and combined.get("passed")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
