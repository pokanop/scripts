# Changelog

All notable changes to the toolkit. Each tool (and `scriptkit`) is versioned
**independently** with [Semantic Versioning](https://semver.org). See
[AGENTS.md](AGENTS.md#versioning--changelog) for when to bump and how to record it.

Newest entries on top, within each tool.

---

## scriptkit

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
