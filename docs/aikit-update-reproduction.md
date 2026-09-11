# POK-387 update regression dry run

The original report used aikit 1.19.0 on Omarchy. Codex remained at 0.153.4,
Grok at 1.0.13, and Oh My Pi at 18.1.15 after successful updater exits. Hermes
reported current; running native updates outside aikit refreshed Hermes/Grok.

## Findings

| Hypothesis | Evidence and correction |
|---|---|
| Wrong updater or destination | Confirmed in code: npm ownership was deliberately ignored; registry npm commands always used `~/.local`. OMP always reran its installer even for Bun/npm installations. Updates now target the active package's prefix or global directory. |
| Invalid Codex command | The registry used `codex update`. [Codex's CLI enum](https://github.com/openai/codex/blob/dc5527481827bffec04b754bad3d12d2b4f6b5dd/codex-rs/cli/src/main.rs) has no Update subcommand and accepts a positional prompt. Updates now use ownership evidence or the installer. |
| Native update/environment contamination | Hermes/Grok already had native commands, but subprocesses inherited all environment variables. Reproduced a native updater failing under inherited Python/Node injection. Standalone/npm/Bun installs prefer native updates with sanitized overrides, then retry the detected manager; receipt-managed installs use their owner exclusively. |
| False “already current” | Confirmed: every exit-zero Hermes check lacking the exact case-sensitive `Update available` string became `available=False`. Unrecognized text, malformed JSON, and failed checks now remain unknown. Explicit positive/negative verdicts are required. |
| Shadowed executable | Reproduced with two real disposable executables on PATH: the first stays old while a second is newer. Verification now reports both paths and versions and returns failure. |

The original host's binary paths and environment were not supplied. These are
confirmed defects and reproduced failure modes, not a claim that the exact
installation layout on that host was observed. Hermes can also update Git commits
without changing its release version; an explicit successful native check still
counts as current after the update.
If the updater succeeds without a version change and the check is inconclusive,
the result remains `unchanged` with exit 0; it is neither a failure nor a claim
that the installation is current.

The [Codex installer](https://chatgpt.com/codex/install.sh) exposes `CODEX_INSTALL_DIR`
and the [OMP installer](https://omp.sh/install) exposes `PI_INSTALL_DIR` (inspected
2026-09-10). Standalone updates pass the active executable's directory through
these variables. A detected package manager always takes precedence over these
installer fallbacks.

## Reproduction

From a checkout with the development dependencies installed:

```sh
venv/bin/python -m pytest tests/test_aikit_updates.py -v
venv/bin/python -m pytest tests/test_aikit_update_review.py -v
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
| Codex | npm owning prefix |
| Oh My Pi | Bun global directory |
| Crush, Copilot, Gemini | npm owning prefix |
| Devin | Installer |

Additional cases cover npm Codex, native failure/no-op followed by the owning
manager, pacman versus AUR, system-update handoff without mutation, pip interpreter/RECORD ownership,
relocated pipx/uv roots, Cargo receipts, Windows npm `.cmd` layout, standalone
installer targets, PATH replacement, shell metacharacters, environment sanitation,
missing binaries, timeouts, malformed checks, and dashboard/CLI failure status.
Existing characterization tests cover Homebrew and mise; npm inside a mise Node
runtime is explicitly distinguished from a mise-managed CLI.

The first review added regressions for successful unchanged/inconclusive Hermes
updates, negative-check phrasings, real spawn failure versus real timeout,
environment-configured npm prefixes, owner-exclusive managed updates, cached
probes with invalidation, and bounded dashboard errors. The first 13 review
regressions failed at `41073fa` before the fixes. pacman/AUR fixtures now assert
read-only ownership queries and a full-system update instruction instead of
simulating partial package upgrades.

## Bun 1.3.14 invocation correction

Live QA at `c69a106` found that `--global-dir` and `--global-bin-dir` are not
`bun install` flags. The earlier permissive manager stubs accepted those invalid
arguments, so fixture upgrades passed while actual Bun updates failed.

Updates now run `bun install -g <package>@latest` and pass the detected directories
through `BUN_INSTALL_GLOBAL_DIR` and `BUN_INSTALL_BIN`, as documented in
[Bun 1.3.14's configuration reference](https://github.com/oven-sh/bun/blob/bun-v1.3.14/docs/runtime/bunfig.mdx).
The strict regression rejects unknown arguments, checks both destination variables,
and updates the executable's version for default and relocated installations.
Both cases failed before this correction.

Separate live runs with real Bun 1.3.14 installed Oh My Pi 18.1.15 into disposable
default and relocated layouts (including directory names with spaces), then
invoked aikit's update path: both upgraded to 18.1.17, exited 0, and re-resolved
the same executable path. No shared user installation was changed.

## Limits

Tests and live checks were executed on Linux. Independent QA at `c69a106` also
verified real Arch pacman/AUR ownership without package mutation, npm Codex
0.153.4 → 0.154.0, standalone Grok updates, mise ownership, Linuxbrew Cask routing,
and dashboard outcomes. Native Windows/macOS execution and true Omarchy hardware
remain unverified. Package repositories may publish later than upstream releases;
aikit reports that discrepancy instead of claiming success.
Custom Cargo sources and installations whose owner cannot be proved need their
original installation workflow; aikit does not silently migrate them.
pacman/AUR-owned agents also require the full system update workflow outside
aikit; their updates are intentionally not part of the automatic dry run above.
