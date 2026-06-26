# Changelog

All notable changes to the toolkit. Each tool (and `scriptkit`) is versioned
**independently** with [Semantic Versioning](https://semver.org). See
[AGENTS.md](AGENTS.md#versioning--changelog) for when to bump and how to record it.

Newest entries on top, within each tool.

---

## scriptkit

### 1.0.0 — 2026-06-26
- Initial release of the shared CLI library: `style` (color/icons), `console`
  (messages/prompts/headers), `progress` (bar/track/status/parallel_map),
  `tables`, `config` (three-tier + scalar coercion), `proc` (`run`/`which`/`require`),
  `text` (human formatting), `cli` (`CliError`/`run_cli`/`dispatch`), and `app`
  (`banner`/`make_parser`/`examples_block`) for unified tool identity.

---

## aikit

### 1.3.2 — 2026-06-26
- Refactored output/config/subprocess onto `scriptkit`; removed duplicated helpers.
- Unified `--help` identity banner and section headers via the shared library.

---

## keyferry

### 1.0.1 — 2026-06-26
- Refactored onto `scriptkit`; shared console, messages, config, and `_ansi`.
- Errors now print to **stderr** (was stdout). Unified `--help`/banner identity.

---

## medcat

### 2.2.0 — 2026-06-26
- **Added `-v`/`--version`** flag (previously unavailable).
- Brand identity 📚 and unified `--help` banner; refactored config/console onto `scriptkit`.

---

## netsy

### 1.2.1 — 2026-06-26
- Refactored onto `scriptkit`; shared consoles. Added brand emoji 📡 to `--help`.

---

## pluck

### 1.0.1 — 2026-06-26
- Refactored messages/console onto `scriptkit`; unified `--help`/banner identity.

---

## voxtract

### 3.1.0 — 2026-06-26
- **Added `--version`** flag and unified `--help` identity banner.
- ⚠ **`-v` now means `--version`** (toolkit-wide convention). Use `--verbose`
  for debug output — the long flag is unchanged.
- Refactored color/icons/messages/formatting onto `scriptkit`.

---

## scripts

### 1.0.1 — 2026-06-26
- Routes prompts and the main entrypoint through `scriptkit` (guarded import with a
  stdlib fallback so installs never break). Unified `--help` identity banner.
