# Changelog

All notable changes to the toolkit. Each tool (and `scriptkit`) is versioned
**independently** with [Semantic Versioning](https://semver.org). See
[AGENTS.md](AGENTS.md#versioning--changelog) for when to bump and how to record it.

Newest entries on top, within each tool.

---

## scriptkit

### 1.2.0 — 2026-06-30
- **New `blocks` module** (`scriptkit.blocks`): `sk.ManagedBlock(begin, end)` plus
  the pure helpers `render_block` / `find_block` / `has_block` / `upsert_block` /
  `remove_block`. A reversible, idempotent managed-text-region primitive — insert
  or replace a marker-fenced block, then remove it leaving the surrounding file
  intact (the inverse of the insert). `ManagedBlock.apply` snapshots a `.bak` once
  before the first write; `clear` takes it back out. Built for shell rc env blocks
  and any managed config stanza a tool must add and later remove cleanly.
  `upsert`→`remove` round-trips **byte-for-byte**, preserving the file's original
  trailing-newline state (files with or without a final newline both restore exactly).

### 1.1.3 — 2026-06-29
- Message helpers emit ANSI color on non-TTY streams when color is forced
  (`FORCE_COLOR`, `set_color(True)`); Rich rendering stays on real TTYs.

### 1.1.2 — 2026-06-27
- Fix `doctor` verdict line f-string syntax error on Python 3.9–3.11 (PEP 701
  nested quotes are 3.12+ only).

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

### 1.15.0 — 2026-07-01
- **Auggie (Augment Code CLI).** New agent entry for Augment's terminal CLI (`auggie`),
  installed via npm (`@augmentcode/auggie`). Auth is browser OAuth via `auggie login`.
  Classified as gateway `unsupported` — Augment's backend is proprietary with no
  OpenAI-compatible passthrough route. Agent count 25 → 26. (POK-70)

### 1.14.0 — 2026-07-01
- **Native config renderers for config-driven agents (close coverage gaps).** Three new
  Stage-3 renderers wrap tools that were detected but not reliably routed, plus env
  wiring for OpenHands — shrinking the "detected but not routed" set to the declared
  gaps. Renderer count 9 → 12; each follows the same never-clobber + manifest-restore
  pattern (staged under `~/.aikit/gateway/tools/`, installed only when the tool is
  detected and has no config, reversed pristine on `off`). No renderer receives or writes
  the virtual key. (POK-67)
- **kilo** → `~/.config/kilo/kilo.json`. Kilo is an OpenCode fork, so the same `provider`
  schema — but its own `$schema` (`https://app.kilo.ai/config.json`) and config dir; the
  key is referenced via `{env:OPENAI_API_KEY}` (single-brace), never inlined.
- **qwen** → `~/.qwen/settings.json`. Explicit OpenAI-compatible provider pinned to
  `SETTINGS_VERSION` 4 — the shipping schema; the published-docs v5 shape crashes the
  CLI ("models is not iterable"). The key is read from the env via each provider entry's
  `envKey` (`OPENAI_API_KEY`), so the secret stays out of the file. qwen was already
  env-routable; the renderer makes the routing explicit and reportable.
- **cline** → `~/.cline/data/settings/providers.json`. Pre-registers the gateway as a
  custom `openai-compatible` provider (v1 schema, non-reserved id `litellm-gw`; the
  legacy `globalState.json` path is no longer read). Cline dropped provider-config env
  vars and stores the key in-file, so the rendered entry is **keyless** — supply the key
  at runtime with `cline -k "$OPENAI_API_KEY"`, which reuses the pre-registered base URL
  + model.
- **openhands** → routed via **env**, not a renderer. The standalone OpenHands CLI reads
  `LLM_*` (not `OPENAI_*`), and only with `--override-with-envs`; its on-disk
  `agent_settings.json` needs a literal key aikit won't write to a shared-readable file.
  So `on` now also exports `LLM_BASE_URL` + `LLM_API_KEY`, and coverage classifies
  openhands as `env` with the `--override-with-envs` caveat stated in its *How / why*.
- **Coverage reclassification.** `kilo`/`cline`/`qwen` → `renderer`, `openhands` → `env`.
  The static baseline is now `12 renderer · 5 env · 3 pending · 5 unsupported`
  (was `9 · 5 · 6 · 5`). `grok`, `kimi`, `blackbox` stay `pending` (no confirmed base-URL
  override); `cursor`, `antigravity`, `copilot`, `kiro`, `amp` stay `unsupported`. (POK-67)

### 1.13.0 — 2026-07-01
- **Passthrough-endpoint discovery + native-protocol tool linking.** Routability
  through a native passthrough route (claude → `/anthropic`) is now treated as a
  **runtime, gateway-dependent** property, discovered from the live gateway — not a
  static "unroutable" table. aikit stays a pure client: it discovers what the gateway
  already exposes and links tools to it, never configuring LiteLLM.
- **Composite discovery** (`discover_passthrough_routes`) — usable routes =
  known built-in routes (`/anthropic`, `/gemini`, `/vertex_ai`, `/bedrock`, `/cohere`,
  `/mistral`, `/openai`, `/vllm`, `/azure`, `/cursor`, verified against LiteLLM source)
  ∩ (provider-tag inference ∪ a cheap, safe probe), **plus** any user-declared custom
  routes. A route is always mounted, so **presence ≠ works**: a mounted-but-401 route is
  reported **unusable** (cf. POK-62), never inferred usable. Degrades gracefully — no
  admin key or a probe failure is "unknown", never a crash.
- **New `aikit gateway verify`** — probes each candidate passthrough route (a models-list
  GET, no tokens) and reports usability, **flagging any mounted-but-401 route** so a
  mis-forwarding upstream credential is surfaced, not silently broken. `on` also warns
  when a route it's wiring probes 401.
- **New `passthrough` coverage state + reclassification.** The 5 vendor-locked tools
  POK-66 marked `unsupported` are re-examined against the live route set: `cursor`
  (`/cursor` Cursor Cloud Agents route **exists**) and `antigravity` (`/gemini` route
  exists) now carry route-aware reasons — the blocker is the missing tool-side base-URL
  override, not the gateway; `copilot`/`kiro`/`amp` stay `unsupported` (no native LiteLLM
  route) with accurate reasons. Any of them **flips to `passthrough`** the moment a route
  is usable and a base-URL override exists (or a custom mapping is declared).
- **User-declared custom passthroughs** — the escape hatch for tools with no
  auto-discoverable native route: `passthroughs: {tool: {route, auth_var, base_url_var,
  credential_mode}}` in the gateway config. Env-wired through the managed block and
  honoured by `coverage`/`status`/`verify`. `on` now **merge-saves** the config so
  hand-added `passthroughs`/`credential_mode` survive a re-`on`.
- **Credential modes** — default `virtual_key` (the gateway injects the upstream key);
  opt into `forwarded_token` (the caller's own subscription token is forwarded upstream,
  the mode that makes Claude Code Max work) via `credential_mode` — aikit then sets base
  URLs but leaves the tool's auth token untouched. Per-passthrough override supported.
- `on`/`status`/`coverage` account for passthrough-routed tools by name (route + auth
  mode); nothing detected is silently omitted. (POK-68)

### 1.12.0 — 2026-07-01
- **New `aikit gateway coverage`** — a read-only, per-agent coverage matrix for the
  gateway. For every one of the 25 agents it shows `detected?`, a **coverage state**
  (`renderer` / `env` / `pending` / `unsupported`), and *how / why* (the routing var or
  native config path, or the reason it can't be routed), plus a per-state tally. Answers
  "does the gateway cover tool X, and if not, why?" in one look.
- **Coverage capability model** — a single source of truth for how each agent reaches
  the gateway. `renderer` state derives from the native-config renderers (no drift);
  the other 16 agents are declared explicitly: **env-routed (5)** — `claude`, `gemini`,
  `qwen`, `openclaw`, `sgpt` (already carried by the env layer, no native config needed);
  **pending (6)** — `openhands`, `kilo`, `cline`, `grok`, `kimi`, `blackbox` (detected but
  not routed yet, each with the known route recorded); **unsupported (5)** — `antigravity`,
  `cursor`, `copilot`, `kiro`, `amp` (first-party backends that can't target a third-party
  gateway, with the reason).
- **Honest reporting — nothing silent.** `aikit gateway status` and `on` (incl.
  `--dry-run`) now account for **every detected agent**, not just the 9 wrapped tools:
  env-routed ones are named, and any detected-but-not-routed (`pending`/`unsupported`)
  agent is called out inline with a pointer to `coverage`. A newly-registered agent that
  nobody classified surfaces as `unclassified` rather than vanishing from the report.
- **Removed dead `OPENAI_COMPATIBLE_TOOLS` table** — an unused list that looked like the
  tool-coverage source but did nothing; its intent now lives in the coverage model. The
  env layer still sets `OPENAI_*` for every activation, so any OpenAI-compatible tool is
  routed without a per-tool table. Docs gain a **Tool coverage** section. (POK-66)

### 1.11.0 — 2026-06-30
- **Added `aikit gateway purge`** — the explicit "forget" for the saved gateway
  credentials. `on`/`off` is a **fast, zero-input toggle**: `off` returns your agent
  runtimes to pristine (rc block, tool configs, `gateway.env`/`gateway.json`, manifest)
  but **keeps** aikit's own `0600` credential store (`~/.aikit/gateway/config.json`), so
  flipping back `on` needs no input. `purge` removes that store (deactivating first if
  active) and prunes `~/.aikit/gateway/`, so re-enabling needs `-u`/`-k` again. Confirms
  before acting (`-y` to skip); `--dry-run` previews; friendly no-op when nothing is
  saved. `aikit gateway off --purge` does both in one shot.
- **Clarified the toggle model** — "pristine" refers to your **agent runtimes** (shell rc
  + tool configs), not aikit's private `~/.aikit/` state dir; the `0600` credential store
  persists across `off` (like `~/.aws/credentials`) and is removed only by `purge`.
  `status` now reads *inactive (credentials saved)* while OFF-but-configured, with a hint
  to `on`/`purge`. Security invariant: while OFF the virtual key lives **only** in the
  `0600` store — never in an agent-runtime file — and is absent from the machine entirely
  after `purge`. (POK-63)

### 1.10.0 — 2026-06-30
- **Native per-tool gateway config (`aikit gateway on`)** — beyond the env layer,
  `on` now generates each tool's config in its own native schema (populated with the
  models the gateway exposed) so tools that don't read env vars also route through the
  gateway. Nine renderers ship: **opencode** (`~/.config/opencode/opencode.json`),
  **codex** (`~/.codex/config.toml`), **crush** (`~/.config/crush/crush.json`),
  **goose** (`~/.config/goose/config.yaml`), **pi** (`~/.pi/agent/models.json`),
  **hermes** (`~/.hermes/config.yaml`), **aider** (`~/.aider.conf.yml`), plus
  **llm** and **continue** (staged only — their real path varies). Each references the
  key via env var (`{env:OPENAI_API_KEY}`, `$OPENAI_API_KEY`, …) — the secret is never
  inlined into a tool config.
- **Portable files** under `~/.aikit/gateway/`: `gateway.env` (source-able export
  block, `0600` — it holds the key) and `gateway.json` (machine-readable summary:
  gateway URL, OpenAI-compatible base, all providers, discovered models).
- **Never-clobber install** — every rendered config is staged under
  `~/.aikit/gateway/tools/`, and installed to the real path **only when the tool is
  detected (via aikit's agent registry) AND no config exists there**. An existing user
  config is kept and the staged copy left for manual merge.
- **Manifest-tracked, pristine restore** — every file `on` writes is recorded
  (`created_by_aikit`, plus the directories it had to create) in a **write-ahead manifest
  committed before any file is written**, so even an *interrupted* `on` (crash / Ctrl-C
  after files land but before the final manifest write) is fully reversible — including
  the secret-bearing `gateway.env`. `gateway off` deletes exactly that set (portable
  files + staged copies + aikit-installed configs), prunes the now-empty directories it
  created (including `~/.aikit/gateway/tools/`), and never touches a user config aikit
  didn't create. Re-running `on` first reverses the prior run's files, so a single `off`
  always fully unwinds; a second `off` is a clean no-op. **Pristine.**
- **`gateway status`** now lists wrapped tools — detected?, and whether each config is
  installed-by-aikit, user-owned (kept), or staged-only — with the path. **`gateway on
  --dry-run`** previews the per-tool plan without writing.
- `gateway.env` values are emitted through `shlex.quote`, so a key containing a quote,
  `$`, or a backtick can't break `source gateway.env` or trigger shell expansion.
- Renderers are pure functions, unit-tested for valid JSON/TOML/YAML + no inlined
  secret; an `on`→`off` round-trip proves created files are removed and pre-existing
  user configs are untouched, and an interrupted-`on`→`off` test proves crash-safety.
  `docs/aikit-gateway.md` completed (per-tool matrix, never-clobber policy,
  pristine-restore guarantee).

### 1.9.0 — 2026-06-30
- **New `aikit gateway` command group** — wrap every OpenAI-compatible tool/SDK to
  route through a single LiteLLM-style gateway with one virtual key, and unwrap again
  leaving the machine **pristine** (idempotent both directions):
  - `gateway on` — discover models, write a managed shell env block (zsh/bash/fish)
    between aikit-owned markers, and record a `~/.aikit/gateway/state.json` manifest.
    Confirms before applying (`--yes` to skip); `--dry-run` previews and writes nothing;
    `--only-discovered` restricts to providers backing visible models; `--shell` override.
  - `gateway off` — remove the env block, restore the rc file pristine, clear the
    manifest. Friendly no-op (exit 0) when nothing is active. `--dry-run`.
  - `gateway status` — active/inactive, gateway URL, **masked** key, model count,
    shell + rc path, and drift detection (managed block hand-edited or removed).
  - `gateway models` — read-only listing of the models the key can see.
  - `aikit doctor` gains a **Gateway** section (configured? reachable? active?).
- **Table-driven provider registry** — all 65 LiteLLM providers ship as data
  (`GATEWAY_PROVIDERS`: prefix, key/base env vars, route, detection) plus
  `OPENAI_COMPATIBLE_TOOLS`. Routing is data, not per-provider branches. Native
  per-tool config files are a follow-up (Stage 3).
- Gateway URL + virtual key persist at `~/.aikit/gateway/config.json` (`0600`,
  honoring `AIKIT_CONFIG`); the key is masked in all output and never logged.
- **Safety:** only inference-scoped vars are set — `AWS_ACCESS_KEY_ID`,
  `GITHUB_TOKEN`, `GOOGLE_APPLICATION_CREDENTIALS`, `HF_TOKEN`, … are left untouched
  so gateway routing never clobbers your git / cloud / hub auth.
- Reversible env block built on scriptkit's new `ManagedBlock`; no new dependencies
  (`requests` already shipped). New doc: `docs/aikit-gateway.md`.

### 1.8.0 — 2026-06-30
- Added four new agent registry entries for gateway tooling coverage: **Gemini CLI**
  (`@google/gemini-cli`), **LLM** (Simon Willison's `llm`), **Continue CLI** (`cn`),
  and **Shell GPT** (`sgpt`). Evaluated **mods** (Charm) and **chatblade** but skipped
  both — `mods` archived; `chatblade` stale/unmaintained.
- Agent count updated to 25 across docs and README.

### 1.7.2 — 2026-06-29
- **Kimi Code:** fix install detection — official installer ships the `kimi`
  binary under `~/.kimi-code/bin/` (not `kimi-code`); detect that path before
  shell PATH is refreshed; add automated uninstall.

### 1.7.1 — 2026-06-29
- **`aikit uninstall`:** prune stale config entries when the binary is already
  gone (fixes "not fully removed" on ghost records).

### 1.7.0 — 2026-06-28
- Added a new agent registry entry: **Amp** (Sourcegraph) — the agentic coding
  tool from `ampcode.com`. Installs via the official `curl` script (PowerShell on
  Windows), updates with `amp update`, tracks releases through the `@ampcode/cli`
  npm package, and authenticates with `amp login` (browser sign-in) or `AMP_API_KEY`
  for scripts/CI. Auth discovery recognizes `~/.config/amp/settings.json`.

### 1.6.2 — 2026-06-27
- **`aikit serve` dashboard:** moved the output log above the agent table so
  install/update feedback is visible without scrolling past 20 rows.

### 1.6.1 — 2026-06-27
- **`aikit list` is much faster:** parallel per-agent discovery, no duplicate
  `--version` subprocesses during discovery, and smarter multi-line version parsing.
- OpenHands version detection: 20s timeout, `OPENHANDS_SUPPRESS_BANNER=1`, and
  multi-line `--version` parsing (was timing out at 10s and re-probed every list).
- `list` always runs a full fresh scan — install count drives wall time; more
  installed agents means more version/update probes (parallelized, up to 8 workers).
- **Auth audit:** corrected per-agent auth notes and env vars against official docs
  (e.g. `agent login`, `codex login`, `COPILOT_GITHUB_TOKEN`, `opencode auth login`);
  improved credential discovery paths; setup wizard now guides OAuth agents too;
  `aikit auth` no longer marks auth complete when credentials are still missing.
- **`aikit auth` picker:** single-select over installed agents only; Enter accepts
  `\r`/`\n` on macOS terminals (was ignored and left the menu stuck).
- Kilo auth discovery no longer treats OpenCode's `~/.config/opencode/` config as
  Kilo credentials (false positive when both tools are installed).
- Stale `auth_configured` cache in `~/.aikit/config.json` no longer overrides
  filesystem checks for API-key / provider-key agents.
- Uninstall now prunes `~/.aikit/config.json` entries when the binary is gone;
  `discover_and_persist` no longer re-adds ghost records for uninstalled agents.
- GitHub Copilot auth now launches `copilot login` (OAuth) instead of prompting for PAT keys.

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

### 1.1.1 — 2026-06-27
- Doctor, errors, and docs now recommend the **native Bitwarden CLI binary**
  (GitHub releases, Homebrew, Chocolatey, snap) instead of `npm i -g @bitwarden/cli`.

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

### 2.3.1 — 2026-06-28
- **Fixed `search` download menu doing nothing on selection.** Internet Archive
  results were tagged with the source name `archive.org` while the dispatch table
  (`SEARCH_SOURCES`) and every comparison key on `archive`, so picking a result hit
  `SEARCH_SOURCES.get(...) is None` and was silently skipped (and the results table
  showed a `?` icon). Archive results now use the canonical `archive` source name,
  so selections download and the 🏛️ icon renders.
- **Fixed `EOFError` traceback at the download menu.** Ctrl-D / closed stdin now
  exits the menu cleanly, matching the EOF handling in the other prompts. (Ctrl-C
  continues to exit gracefully via `sk.run_cli` — the single termination point.)
- The menu now warns instead of silently skipping a result whose source has no
  registered handler, so a future name mismatch can't fail silently.

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

### 1.3.1 — 2026-06-29
- Fix a blank trailing column that appeared after **Vendor** in single-pass scans
  (and any table without the `Seen` stability column). `print_table` always passed
  a fifth empty row value, so rich auto-created a headerless extra column; the value
  is now only added when stability tracking is on.

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

### 1.2.1 — 2026-06-27
- `doctor` Bitwarden CLI hint now recommends the native binary (GitHub releases,
  Homebrew, Chocolatey, snap) instead of npm.

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
