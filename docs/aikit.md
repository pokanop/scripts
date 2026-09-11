# 🤖 aikit — AI Coding Agent CLI Installer & Manager

**Install, update, authenticate, and manage 38 AI coding agent CLIs from one tool.**

`aikit` · Python 3 · `rich` · `flask` · `requests`

```
aikit install             # Multi-select interactive picker (Space=toggle, Enter=done)
aikit install claude codex cursor   # Install specific agents
aikit list                # See everything at a glance
aikit serve               # Web dashboard at http://localhost:8765
```

---

## Quick start

```bash
# Install (adds aikit to PATH)
curl -fsSL https://raw.githubusercontent.com/pokanop/scripts/main/install.sh | bash -s -- --tools aikit
# …or from a clone: ./install.sh --in-place --tools aikit

aikit setup
```

---

## Agents (38)

| # | Agent | Install | Auth |
|---|-------|---------|------|
| 1 | 🧠 **Claude Code** | `curl` script | OAuth (browser) or `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` |
| 2 | 🛸 **Antigravity** | `curl` script | OAuth (Google account via `agy`) |
| 3 | 🖱️ **Cursor CLI** | `curl` script | `agent login` OAuth or `CURSOR_API_KEY` |
| 4 | ☤ **Hermes Agent** | `curl` script | `hermes setup --portal` (Nous Portal OAuth) or `hermes model` for API keys |
| 5 | 📟 **Codex CLI** | `curl` script | `codex login` (ChatGPT OAuth) or `OPENAI_API_KEY` |
| 6 | ⚡ **Kilo CLI** | `npm` | `kilo auth login` (Kilo account) or `/connect` for BYOK |
| 7 | 🔓 **OpenCode** | `npm` | `opencode auth login` for provider API keys |
| 8 | 🐉 **Qwen Code** | `npm` | `/auth` inside `qwen` (OAuth, Coding Plan, or API keys) |
| 9 | 🎯 **Qodo Gen CLI** | `npm` | `qodo login` (Qodo account) or `QODO_API_KEY` / provider keys for BYOK |
| 10 | 🐙 **GitHub Copilot CLI** | `curl` script | `copilot login` OAuth or `COPILOT_GITHUB_TOKEN` / fine-grained PAT |
| 11 | 🚀 **Grok Build** | `curl` script | `grok login` OAuth or `XAI_API_KEY` |
| 12 | 🤝 **Aider** | `pip`/`curl` | Provider API keys |
| 13 | 🌙 **Kimi Code** | `curl` script | `/login` in `kimi` (membership OAuth) or Kimi Code Console API key |
| 14 | 🦅 **Kiro CLI** | `curl` script | `kiro-cli login` OAuth or `KIRO_API_KEY` (Pro+) |
| 15 | π **Pi Coding Agent** | `npm` | `/login` in `pi` (subscription OAuth) or provider API keys |
| 16 | 📐 **Plandex** | `curl` script | Provider API keys (`OPENROUTER_API_KEY` recommended); `plandex new` to start |
| 17 | 🦞 **OpenClaw** | `curl` script | `openclaw onboard` guided setup |
| 18 | ⬛ **Blackbox AI** | `npm` | API key from dashboard → `blackbox configure` |
| 19 | 🪿 **Goose** | `curl` script | `goose configure` or provider API keys |
| 20 | 🌀 **Cline** | `npm` | `cline auth` OAuth (Cline, ChatGPT) or BYOK |
| 21 | 🙌 **OpenHands CLI** | `curl` script | First-run LLM settings; `openhands login` for Cloud only |
| 22 | 💘 **Crush** | `npm` | `crush login` OAuth or provider env vars |
| 23 | 🔊 **Amp** | `curl` script | `amp login` (browser sign-in) or `AMP_API_KEY` |
| 24 | ✨ **Gemini CLI** | `npm` | Google OAuth in `gemini`, or `GEMINI_API_KEY` / `GOOGLE_API_KEY` |
| 25 | 🔮 **LLM** | `pip` | `llm keys set <provider>` or provider env vars |
| 26 | ▶️ **Continue CLI** | `curl` script | `cn login` (Continue account) or `ANTHROPIC_API_KEY` |
| 27 | 🐚 **Shell GPT** | `pip` | `sgpt` first-run key prompt or `OPENAI_API_KEY` |
| 28 | 🧩 **Devin CLI** | `curl` script | `devin auth login` OAuth (Cognition AI account) |
| 29 | 🔋 **Auggie** | `npm` | `auggie login` (Augment account OAuth) |
| 30 | 🏭 **Droid** | `curl` script | `droid` on first use (Factory AI OAuth), or `FACTORY_API_KEY` |
| 31 | 🖥️ **Open Interpreter** | `pip` | Provider API keys (`OPENAI_API_KEY`, etc.) or first-run prompt; `--local` for Ollama |
| 32 | 🧬 **MiMo Code** | `curl` script / `npm` | First-run wizard in `mimo` (MiMo Auto free, Xiaomi OAuth, Claude Code import, or any OpenAI-compatible API) |
| 33 | 🥧 **Oh My Pi** | `curl` script / `npm` | `/login` in `omp` (subscription OAuth) or provider env vars (Anthropic/OpenAI/Gemini/Groq/xAI/OpenRouter) |
| 34 | 🌊 **Mistral Vibe** | `curl` script / `pip` | `vibe` first-run wizard (browser OAuth to a Mistral account) or `MISTRAL_API_KEY` |
| 35 | 🪐 **Jules** | `npm` | `jules login` (Google account OAuth; async cloud-VM agent) |
| 36 | 🦘 **Roo Code CLI** | `curl` script (Linux x64 / macOS arm64) | BYOK — `OPENROUTER_API_KEY` (default) or another provider key / `--provider --api-key` |
| 37 | 🐃 **Codebuff** | `npm` | First launch of `codebuff` opens a browser sign-in; `CODEBUFF_API_KEY` for CI |
| 38 | 🧿 **Qoder CLI** | `curl` script / PowerShell | `/login` inside `qoder` (browser OAuth) or `QODER_PERSONAL_ACCESS_TOKEN` for CI |

### Not managed

- **ZCode** (Z.ai / Zhipu) — no public CLI installer; distributed only as a signed desktop app, with no `curl|bash`, npm, or pip distribution channel. aikit's install/update/uninstall contract has no clean target for it. Filed as a known gap so searches land here; revisit if Z.ai ships a public CLI.

---

## Commands

| Command | Description |
|---------|-------------|
| `aikit setup` | Interactive first-run wizard |
| `aikit install [agents...]` | Install agents (multi-select picker if none) |
| `aikit update [agents...]` | Update agents (all installed if none) |
| `aikit uninstall [agent...]` | Remove agents |
| `aikit list` | Status table of all 38 agents |
| `aikit auth [agent] [--force]` | Guided authentication setup; `--force` replaces cached auth status and signs in again |
| `aikit doctor` | Diagnose environment and agent health |
| `aikit serve` | Start web dashboard |
| `aikit config get/set/list` | Manage `~/.aikit/config.json` |
| `aikit gateway on/off/status/coverage/models` | Route AI tools through a LiteLLM gateway — see **[gateway docs](aikit-gateway.md)** |
| `aikit usage [providers...] [--json] [--all]` | Unified plan / credits / spend / rate-limit snapshot across providers — see below |

### Updating existing installations

`aikit update` inspects the executable you actually run. It prefers the agent's
native updater when registered, then falls back to the detected package manager.
It preserves npm/Bun install locations, pip interpreter ownership, and relocated
pipx/uv roots. Homebrew, mise, Cargo, and pacman/AUR ownership comes from paths or
installation metadata, not the OS name. Codex uses its manager or official installer;
`codex update` is not a Codex subcommand.

Maintenance commands clear inherited Python/Node injection, shell startup hooks,
Git repository overrides, and package destination overrides while retaining HOME,
PATH, manager roots, proxy settings, and certificates. Native and manager commands
use argument lists so executable paths are not interpreted as shell syntax.

Every update re-resolves the executable and checks its version. A failed updater,
missing version, or unverified no-op exits **1** and reports the command, manager,
active path, and other copies on PATH. An explicit “already up to date” check is
successful; an ambiguous or failed check is unknown and does not skip the update.
`--force` bypasses the initial current-version check, but still verifies the result.

For AUR packages, aikit uses an available `paru` or `yay`; without either, it
reports the owning package and asks you to use your AUR build workflow. It does
not refresh system databases or perform a whole-system upgrade. If package
repositories lag upstream, run your normal system update workflow and retry.
Unknown npm/pip ownership and custom Cargo sources produce an actionable failure
instead of guessing another installation destination.

See [the mixed-installation regression dry run](aikit-update-reproduction.md) for
the Omarchy reproduction and verification limits.

### Usage snapshot (`aikit usage`)

`aikit usage` reads the credentials the CLIs already store on disk (OAuth tokens,
session cookies, API keys — nothing is ever written back) and queries each
provider's own usage endpoint — the same endpoints the open-source trackers
[CodexBar](https://github.com/steipete/CodexBar),
[ai-usagebar](https://github.com/akitaonrails/ai-usagebar), MeterBar, UsageOwl
and OpenUsage use, cross-checked against each other so parsers key on semantic
fields (window durations, quota types) rather than array positions. Every
provider is normalised into one record — `account`, `plan`, rate-limit
`windows` (label / used % / used / limit / resets_at), `credits`
(remaining / total / used), `spend` (amount / currency / period / limit) and a
`status` of `ok`, `unauthenticated`, `error` or `unsupported` — and rendered as
one table. Probes run in parallel and never raise: a provider that is not
signed in shows the exact command or env var to fix it, an API failure shows the
HTTP status, and secrets never appear in any output (including `--json`).

```bash
aikit usage                      # every provider with a usage API that is signed in
aikit usage claude codex --json  # machine-readable snapshot for scripting
aikit usage --all                # also list not-signed-in / unsupported providers
```

| Provider | Credential source (read-only) | What is reported |
|----------|-------------------------------|------------------|
| Codex | `~/.codex/auth.json` (`$CODEX_HOME`) | plan, email, windows labelled by duration (5h/weekly/daily), code-review + per-model extra limits, credit balance, banked reset credits |
| Claude Code | `~/.claude/.credentials.json` (`$CLAUDE_CONFIG_DIR`), macOS Keychain | plan, 5h / weekly / per-model windows, extra-usage spend |
| GitHub Copilot | `$GITHUB_COPILOT_TOKEN` / `$COPILOT_GITHUB_TOKEN` / `$GH_TOKEN` / `$GITHUB_TOKEN`, `~/.config/github-copilot/{apps,hosts}.json`, `~/.config/gh/hosts.yml`, `gh auth token` (keyring) | plan, premium-request quota, entitlements, reset date, login |
| Gemini CLI | `~/.gemini/oauth_creds.json` | tier, per-model remaining quota + reset, project |
| Grok CLI | `~/.grok/auth.json` | tier, credit usage %, on-demand spend/cap, period end |
| Kiro CLI | `kiro-cli/data.sqlite3` (Linux/macOS) | plan, credit usage vs limit, overage, reset |
| Cursor | `$CURSOR_SESSION_TOKEN`, Cursor desktop `state.vscdb`, headless `cursor-agent` `~/.config/cursor/auth.json` | membership, included-usage % (total / Cursor models / other models), included $ used, on-demand enabled, billing cycle end |
| Amp | `$AMP_API_KEY`, `~/.config/amp/secrets.json` | plan, free quota, credit balance, email |
| Droid (Factory) | `$FACTORY_API_KEY`, `~/.factory/.env` | plan, standard/premium token allowance, overage, period end |
| Kilo Code | `$KILO_API_KEY`, `~/.local/share/kilo/auth.json` (+ `$KILO_ORGANIZATION_ID`) | credit balance (USD) via `/api/profile/balance` |
| OpenCode Go | `~/.local/share/opencode/auth.json` | rolling / weekly / monthly windows |
| OpenRouter | `$OPENROUTER_API_KEY` (+ `$OPENROUTER_MANAGEMENT_API_KEY`) | key label, key spend vs limit, credits purchased / used / remaining |
| Synthetic | `$SYNTHETIC_API_KEY` | per-quota usage with resets |
| z.ai | `$Z_AI_API_KEY` | GLM Coding plan level, 5h session + weekly token quota, monthly MCP-tool calls |
| Kimi Code | `$KIMI_API_KEY`, `~/.kimi-code/credentials/kimi-code.json` (+ `region` → `.ai`/`.com`) | membership level, weekly + 5h windows, token expiry |
| Codebuff | `$CODEBUFF_API_KEY` (balance only), `~/.config/manicode/credentials.json` (+ plan, weekly limit) | credits used / quota, remaining balance, plan, weekly limit |
| Devin | `$DEVIN_BEARER_TOKEN` + `$DEVIN_ORG_ID` | ACU usage vs plan limit |

API-key billing sources that are not installable agents (probed automatically
when the env var is set; e.g. `aikit usage deepseek openai-api`):

| Provider | Credential | What is reported |
|----------|------------|------------------|
| DeepSeek API (`deepseek`) | `$DEEPSEEK_API_KEY` | balance (USD preferred), granted / topped-up split |
| Moonshot API (`moonshot`) | `$MOONSHOT_API_KEY` (+ `$MOONSHOT_BASE_URL` for `.cn`) | available / voucher / cash balance |
| MiniMax Coding Plan (`minimax`) | `$MINIMAX_API_KEY` (+ `$MINIMAX_BASE_URL`) | per-model rolling + weekly request windows |
| Novita AI (`novita`) | `$NOVITA_API_KEY` | available / cash balance, credit limit, pending charges |
| Anthropic API (`anthropic-api`) | `$ANTHROPIC_ADMIN_KEY` (org admin key) | month-to-date org spend (paginated `cost_report`; refuses partial totals) |
| OpenAI API (`openai-api`) | `$OPENAI_ADMIN_KEY` (org admin key) | month-to-date org spend (`/v1/organization/costs`) |

All other agents report `unsupported` (their vendors expose no usage API).
Trackers that rely on browser-only HttpOnly cookies (Windsurf, Warp, Zed) or
local-transcript cost estimates were reviewed and deliberately not replicated.

### Multi-Select Picker

When no agents are specified, aikit shows an interactive multi-select menu:

```
Select agents to install
  Space = toggle  |  Enter = confirm  |  a = select all  |  n = deselect all  |  q = cancel

   1. [ ] 🧠 Claude Code
   2. [ ] 🛸 Antigravity
   3. [X] 🖱️ Cursor CLI
  ...
  Selected: 1/38  cursor
```

Press `Space` or enter numbers to toggle. Press `Enter` to confirm. Press `q` to cancel.

---

## Web Dashboard

```bash
aikit serve                  # http://localhost:8765
aikit serve --host 0.0.0.0   # LAN accessible
aikit serve --port 9000       # Custom port
aikit serve --detach          # Run in background
aikit serve --stop            # Stop background server
```

Dashboard features:
- Agent status grid with install/update buttons
- Live install/update with log output
- Doctor diagnostics
- REST API at `/api/*`

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents` | GET | List all agents with status |
| `/api/agents/<key>` | GET | Agent detail |
| `/api/install/<key>` | POST | Install an agent |
| `/api/update/<key>` | POST | Update an agent |
| `/api/doctor` | GET | Environment diagnostics |
| `/api/config` | GET/POST | Read config (GET) or deep-merge a partial update (POST) |

---

## Configuration

Config lives at `~/.aikit/config.json` (permissions: `0600`).

Three-tier loading:
1. Default config (built-in)
2. `~/.aikit/config.json`
3. Environment variables (`AIKIT_*`)

```bash
aikit config list                    # Show all (secrets masked)
aikit config get settings.web_port   # Get a specific value
aikit config set settings.web_port 9000  # Set a value
```

`POST /api/config` accepts a partial JSON object and **deep-merges** it into the
loaded config (same semantics as `aikit config set` for nested keys). Only known
top-level keys (`version`, `agents`, `settings`) are accepted; unknown keys or
wrong types return HTTP 400. An empty nested object (e.g. `"agents": {}`) does
not wipe sibling keys under that section.

---

## Gateway

Route every OpenAI-compatible tool/SDK through a single LiteLLM-style gateway with
one virtual key — and switch back, leaving your machine **pristine**. Full guide:
**[aikit-gateway.md](aikit-gateway.md)**.

```bash
aikit gateway on --dry-run -u https://gw.example.com   # preview env block + per-tool plan, write nothing
aikit gateway on -u https://gw.example.com             # write the env block, native tool configs + manifest
aikit gateway status                                   # active? URL, masked key, models, wrapped tools, drift
aikit gateway coverage                                 # per-agent: routed via renderer/env, pending, or unsupported
aikit gateway off                                      # remove everything aikit wrote, restore pristine
```

`on` wraps tools at two layers: the **env block** (for everything that reads `OPENAI_*`
or a provider's own env vars) **and native per-tool config files** for tools that read
their own config — opencode, codex, crush, goose, pi, hermes, aider, plus staged-only
llm/continue — each populated with the gateway's models and **never** clobbering a
config you already have. It's idempotent both ways: `on` then `on` is a no-op; `on` then
`off` returns the rc file, environment-affecting state, **and every file aikit wrote** to
exactly where they were. The gateway URL and virtual key live at
`~/.aikit/gateway/config.json` (`0600`); the key is always masked in output and never
logged.

---

## Architecture

```
aikit                          # Single-file Python script (~1,600 lines)
├── Agent registry             # 38 agents, each with platform-aware install commands
├── Subprocess runner          # Install/update/uninstall execution
├── Config system              # JSON-based, three-tier loading, env var overrides
├── Rich TUI                   # Tables, panels, interactive multi-select picker
├── Authentication helpers     # Per-agent auth flow guidance and env var management
└── Flask web dashboard        # REST API + single-page HTML dashboard
```

All interactive paths are KeyboardInterrupt-safe — Ctrl-C at any prompt exits cleanly with a cancellation message.

---

## Development

```bash
git clone https://github.com/pokanop/scripts.git && cd scripts
./install.sh --in-place --tools aikit
aikit doctor
aikit list
```

---

## Related tools

Built on **[scriptkit](scriptkit.md)** — the shared CLI library (color, messages, progress, tables, config, subprocess). Building or editing a tool? See **[AGENTS.md](../AGENTS.md)**.

Part of the [scripts](../README.md) toolkit — [keyferry](keyferry.md) · [medcat](medcat.md) · [voxtract](voxtract.md) · [netsy](netsy.md) · [pluck](pluck.md)

---

## License

MIT — see [LICENSE](../LICENSE).
