# Changelog

All notable changes to the toolkit. Each tool (and `scriptkit`) is versioned
**independently** with [Semantic Versioning](https://semver.org). See
[AGENTS.md](AGENTS.md#versioning--changelog) for when to bump and how to record it.

Newest entries on top, within each tool.

---

## scriptkit

### 1.1.1 — 2026-06-27
- Message helpers (`success`, `error`, `warning`, `info`, `detail`, `elapsed`)
  now render inline Rich markup (`[dim]`, `[bold]`, …) when `rich` is available;
  tags are stripped on the plain/no-color fallback so they never leak literally.

### 1.1.0 — 2026-06-26
- **New shared `doctor` renderer** (`scriptkit.doctor`): `sk.doctor(name, version,
  …, sections=…, tips=…)` plus `sk.Check` and `sk.check_binary` / `sk.check_python`.
  One diagnostic look for every tool — auto **System** section, rolled-up **Issues**,
  optional **Tips**, and an exit code that's `1` iff a required check fails.
  `check_binary` truncates long `--version` output to keep reports tidy.
- **Centralized app lifecycle.** `sk.parse_args(parser, default=…)` injects a default
  subcommand on a bare invocation (so its parser defaults populate); `sk.dispatch`
  gains `default=` and `banner=` — it prints the identity banner **to stderr** for
  every command (never polluting piped stdout) and shows banner-led help (exit 0)
  on a bare run with no default; `sk.run_cli` gains `on_interrupt=` for cleanup on
  Ctrl-C. Tools now share one `main`/`__main__` shape.
- `make_parser` renders `--help` with the **identity banner above the usage line**
  (via a `BannerFirstParser`), so help leads with the tool's identity.
- Section headers (`sk.header`, and every `doctor` sub-section) render in **bold
  default** rather than bold cyan — cleaner, less saturated; the `━━━` rule is kept.

### 1.0.0 — 2026-06-26
- Initial release of the shared CLI library: `style` (color/icons), `console`
  (messages/prompts/headers), `progress` (bar/track/status/parallel_map),
  `tables`, `config` (three-tier + scalar coercion), `proc` (`run`/`which`/`require`),
  `text` (human formatting), `cli` (`CliError`/`run_cli`/`dispatch`), and `app`
  (`banner`/`make_parser`/`examples_block`) for unified tool identity.

---

## aikit

### 1.6.1 — 2026-06-27
- **`aikit list` is much faster:** parallel per-agent discovery, no duplicate
  `--version` subprocesses during discovery, and smarter multi-line version parsing.
- OpenHands version detection: 20s timeout, `OPENHANDS_SUPPRESS_BANNER=1`, and
  multi-line `--version` parsing (was timing out at 10s and re-probed every list).
- `list` always runs a full fresh scan — install count drives wall time; more
  installed agents means more version/update probes (parallelized, up to 8 workers).

### 1.6.0 — 2026-06-27
- Added four new agent registry entries: **Goose** (curl/AAIF), **Cline** (npm),
  **OpenHands CLI** (install script), and **Crush** (npm). Roo Code was investigated
  but omitted — it is a VS Code extension only (shut down May 2026; community fork
  Zoo Code is also extension-only).
- Unknown agent keys (e.g. `clien` instead of `cline`) now fail fast with
  did-you-mean suggestions instead of crashing mid-install with `KeyError`.
- npm-based installs (Cline, Crush, and all other npm agents) now use
  `--prefix ~/.local` so binaries land on PATH; also scans npm global bin dirs
  when the active npm prefix is elsewhere (e.g. Hermes).
- Fixed agent detection for curl-installed CLIs whose binaries live under
  `~/.local/bin` (Goose, OpenHands) or as PATH symlinks (Claude Code).
- Added uninstall commands for Goose (`rm` + Homebrew fallback) and OpenHands
  (`uv tool uninstall` + binary removal); Cline/Crush continue via scoped
  `npm uninstall -g`.
- npm uninstall now removes packages from every global prefix where they exist
  (`~/.local`, active `npm prefix`, nvm node prefix), not only `~/.local`.
- npm agent detection no longer treats off-PATH global bins (e.g. Hermes
  `~/.hermes/node/bin`) as installed; `aikit list` and uninstall stay in sync.
- npm uninstall also discovers the active nvm node prefix from `PATH`/`NVM_DIR`
  and removes orphan package copies even when they are not on PATH.
- Kilo updates use `npm install -g @kilocode/cli@latest` instead of `kilo upgrade`,
  which hangs in non-interactive use when the install method is not specified.
- Goose install passes `CONFIGURE=false` so the upstream script does not require
  `/dev/tty` for interactive `goose configure` during `aikit install`.
- Goose uninstall no longer runs a slow `brew list` probe on every removal;
  Homebrew cleanup only runs when the binary lives under Homebrew. Uninstall
  also skips the full `discover_and_persist()` network sweep that added ~30s.

### 1.5.0 — 2026-06-27
- Fixed Rich markup (`[dim]`, `[bold]`, …) showing literally in success/info lines
  after the scriptkit refactor — now rendered via shared message helpers.
- Cursor CLI detection now tracks the agent binary (`cursor-agent`, alias `agent`)
  instead of the IDE launcher (`cursor`); Grok Build documents its `agent` alias;
  both warn when bare `agent` is ambiguous on PATH.
- Fixed update commands for Cursor (`cursor-agent update`), Codex, and Grok; kimi/kiro
  reinstall via their install scripts.
- Proactive upstream version checks (npm, PyPI, GitHub releases, vendor manifests,
  and built-in `--check` where available) with an **Update** column in `list`.
- `doctor` and the web API now surface upgrade availability; results are cached
  (`settings.update_check_ttl`, default 1h).
- `update` now compares versions before/after each command and reports **upgraded**,
  **already up to date**, **unchanged**, **still outdated**, or **failed** — instead of
  labeling every successful exit as "updated". Skips current agents unless `--force`;
  the end summary uses human-readable agent names with counts per outcome.
- Corrected native update commands: `kilo upgrade`, `opencode upgrade`, `qwen upgrade`,
  `pi update --self`, and `blackbox update` (replacing `npm install -g …` that could
  target the wrong prefix). Kiro CLI now detects `kiro-cli` (alias `kiro`); Qwen and
  Blackbox install scripts match upstream docs.

### 1.4.0 — 2026-06-26
- **Bare `aikit` now runs `list`** (the agent table) after the identity banner,
  instead of printing help. First-run discovery still shows a one-time welcome.
- `doctor` rebuilt on the shared `sk.doctor` renderer (System / Prerequisites /
  Agents sections, rolled-up issues, exit code) — replacing the bespoke panels.
- Adopted the centralized lifecycle (`parse_args`/`dispatch`/`run_cli`); the banner
  now shows for every command (to stderr), and Ctrl-C is handled uniformly.
- Lint pass: removed unused imports, a dead `import threading`, a no-op
  `global _serve_process`, an unused local, and a needless f-string prefix.

### 1.3.2 — 2026-06-26
- Refactored output/config/subprocess onto `scriptkit`; removed duplicated helpers.
- Unified `--help` identity banner and section headers via the shared library.

---

## keyferry

### 1.1.0 — 2026-06-26
- `doctor` rebuilt on the shared `sk.doctor` renderer (CLIs / Python / Config
  sections), matching every other tool's diagnostic look.
- Adopted the centralized lifecycle: `KeyferryError` subclasses `sk.CliError`,
  `__main__` is `sk.run_cli(main)`, the identity banner shows for every command
  (to stderr, and only in `--help`/`--version` — no longer reprinted on the
  no-command screen or atop each command), and hand-rolled interrupt/error
  handling was removed.
- Lint pass: removed unused imports (`argparse`, `typing` aliases, unused color
  aliases) and a dead local in `cmd_status`.

### 1.0.1 — 2026-06-26
- Refactored onto `scriptkit`; shared console, messages, config, and `_ansi`.
- Errors now print to **stderr** (was stdout). Unified `--help`/banner identity.

---

## medcat

### 2.3.0 — 2026-06-26
- **Added a `doctor` command** (previously none) on the shared `sk.doctor` renderer:
  media tools (ffmpeg/yt-dlp/ia/wget), Python packages, and config, with tips
  pointing at `config --check` / `config test`.
- Adopted the centralized lifecycle (`parse_args`/`dispatch`/`run_cli`); the banner
  shows for every command (to stderr) and Ctrl-C is now handled gracefully (was an
  unhandled traceback).
- Lint pass: removed unused imports and dead locals, dropped needless f-string
  prefixes, and renamed a loop variable that shadowed the `sk` import.

### 2.2.0 — 2026-06-26
- **Added `-v`/`--version`** flag (previously unavailable).
- Brand identity 📚 and unified `--help` banner; refactored config/console onto `scriptkit`.

---

## netsy

### 1.3.0 — 2026-06-26
- ⚠ **Ctrl-C no longer throws a traceback** — interrupts now exit cleanly (130) via
  the shared `sk.run_cli`. (`__main__` previously called `main()` directly.)
- `doctor` rebuilt on the shared `sk.doctor` renderer (Prerequisites / Network
  sections + tips), replacing the bespoke panel report.
- Adopted the centralized lifecycle; the default `scan` action and banner now flow
  through `parse_args`/`dispatch` (banner to stderr) instead of an argv hack.

### 1.2.1 — 2026-06-26
- Refactored onto `scriptkit`; shared consoles. Added brand emoji 📡 to `--help`.

---

## pluck

### 1.1.0 — 2026-06-26
- Added the brand emoji 🪶 to the identity banner (`ICON` now wired into the parser).
- `doctor` rebuilt on the shared `sk.doctor` renderer (Python / Formats sections).
- Adopted the centralized lifecycle: `PluckError` subclasses `sk.CliError`,
  `__main__` is `sk.run_cli(main)`, the banner shows for every command (to stderr,
  and only in `--help`/`--version` — no longer reprinted on the no-command screen
  or atop `doctor`/`formats`/dry-run output), and hand-rolled interrupt/error
  handling was removed.

### 1.0.1 — 2026-06-26
- Refactored messages/console onto `scriptkit`; unified `--help`/banner identity.

---

## voxtract

### 3.2.0 — 2026-06-26
- **Added a `doctor` command** (previously none) on the shared `sk.doctor` renderer:
  audio tools (ffmpeg/ffprobe) and Python packages (yt-dlp/requests required;
  spotipy/spotdl/demucs/torch optional), with tips for Spotify and `--isolate`.
- Adopted the centralized lifecycle: parser extracted into `build_parser()`,
  `__main__` is `sk.run_cli(main, on_interrupt=…)` (temp-file cleanup on Ctrl-C is
  preserved), and the banner shows for every command (to stderr).
- Lint pass: removed unused imports and dead locals, and dropped needless
  f-string prefixes.

### 3.1.0 — 2026-06-26
- **Added `--version`** flag and unified `--help` identity banner.
- ⚠ **`-v` now means `--version`** (toolkit-wide convention). Use `--verbose`
  for debug output — the long flag is unchanged.
- Refactored color/icons/messages/formatting onto `scriptkit`.

---

## scripts

### 1.2.0 — 2026-06-26
- **Bare `scripts` now lists available tools** (with install status) instead of
  erroring on a missing subcommand.
- `doctor` rebuilt on the shared `sk.doctor` renderer (Install / Tools / System
  dependencies sections + "available to add" tip) when `scriptkit` is present;
  keeps the plain stdlib fallback for bootstrap.
- **`scripts install` now pulls the latest source first** when the install dir is a
  git checkout (previously only `scripts update` did) — so "install" means "install
  the latest". Added `--no-pull` to opt out; `install.sh` now refreshes an existing
  clone by default and hands off to `scripts install --no-pull` to avoid a double pull.
- The identity banner (🛠️) now shows for every command (to stderr), and Ctrl-C
  exits cleanly. All still degrade safely when `scriptkit` is unavailable.

### 1.0.1 — 2026-06-26
- Routes prompts and the main entrypoint through `scriptkit` (guarded import with a
  stdlib fallback so installs never break). Unified `--help` identity banner.
