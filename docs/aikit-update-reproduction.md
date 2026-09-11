# POK-387 update regression dry run

The original report used aikit 1.19.0 on Omarchy. Codex remained at 0.153.4,
Grok at 1.0.13, and Oh My Pi at 18.1.15 after successful updater exits. Hermes
reported current; running native updates outside aikit refreshed Hermes/Grok.

## Findings

| Hypothesis | Evidence and correction |
|---|---|
| Wrong updater or destination | Confirmed in code: npm ownership was deliberately ignored; registry npm commands always used `~/.local`. OMP always reran its installer even for Bun/npm installations. Updates now target the active package's prefix or global directory. |
| Invalid Codex command | The registry used `codex update`. [Codex's CLI enum](https://github.com/openai/codex/blob/dc5527481827bffec04b754bad3d12d2b4f6b5dd/codex-rs/cli/src/main.rs) has no Update subcommand and accepts a positional prompt. Updates now use ownership evidence or the installer. |
| Native update bypass/environment contamination | Hermes/Grok already had native commands, but manager detection took precedence and subprocesses inherited all environment variables. Reproduced with a native updater diverted by manager ownership, and a native updater failing under inherited Python/Node injection. Native updates now run first with sanitized overrides, then retry the detected manager if needed. |
| False “already current” | Confirmed: every exit-zero Hermes check lacking the exact case-sensitive `Update available` string became `available=False`. Unrecognized text, malformed JSON, and failed checks now remain unknown. Explicit positive/negative verdicts are required. |
| Shadowed executable | Reproduced with two real disposable executables on PATH: the first stays old while a second is newer. Verification now reports both paths and versions and returns failure. |

The original host's binary paths and environment were not supplied. These are
confirmed defects and reproduced failure modes, not a claim that the exact
installation layout on that host was observed. Hermes can also update Git commits
without changing its release version; an explicit successful native check still
counts as current after the update.

The [Codex installer](https://chatgpt.com/codex/install.sh) exposes `CODEX_INSTALL_DIR`
and the [OMP installer](https://omp.sh/install) exposes `PI_INSTALL_DIR` (inspected
2026-09-10). Standalone updates pass the active executable's directory through
these variables. A detected package manager always takes precedence over these
installer fallbacks.

## Reproduction

From a checkout with the development dependencies installed:

```sh
venv/bin/python -m pytest tests/test_aikit_updates.py -v
venv/bin/python -m pytest
```

The tests create disposable executables, package trees, symlinks, a Python venv
with distribution RECORD metadata, and manager stubs. They execute real local
subprocesses; no agent downloads, user installations, or system packages change.
The first five regression tests were run against the original code and all failed;
they pass with the fix.

The mixed-installation dry run verifies version changes for all 12 reported agents:

| Agent | Fixture update route |
|---|---|
| Claude, Cursor, Hermes, Grok, OpenCode, Pi | Native command bound to active executable |
| Codex | pacman package owner |
| Oh My Pi | Bun global directory |
| Crush, Copilot, Gemini | npm owning prefix |
| Devin | Installer |

Additional cases cover npm Codex, native failure/no-op followed by the owning
manager, pacman versus AUR, missing AUR helpers, pip interpreter/RECORD ownership,
relocated pipx/uv roots, Cargo receipts, Windows npm `.cmd` layout, standalone
installer targets, PATH replacement, shell metacharacters, environment sanitation,
missing binaries, timeouts, malformed checks, and dashboard/CLI failure status.
Existing characterization tests cover Homebrew and mise; npm inside a mise Node
runtime is explicitly distinguished from a mise-managed CLI.

## Limits

The dry run was executed on Linux. Windows shim/argument construction and macOS
Homebrew layouts have fixture coverage, but native Windows/macOS execution and a
live Omarchy upgrade were not performed. Package repositories may publish later
than upstream releases; aikit reports that discrepancy instead of claiming success.
Custom Cargo sources and installations whose owner cannot be proved need their
original installation workflow; aikit does not silently migrate them.
