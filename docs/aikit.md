# 🤖 aikit — AI Coding Agent CLI Installer & Manager

**Install, update, authenticate, and manage 26 AI coding agent CLIs from one tool.**

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

## Agents (26)

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
| 9 | 🐙 **GitHub Copilot CLI** | `curl` script | `copilot login` OAuth or `COPILOT_GITHUB_TOKEN` / fine-grained PAT |
| 10 | 🚀 **Grok Build** | `curl` script | `grok login` OAuth or `XAI_API_KEY` |
| 11 | 🤝 **Aider** | `pip`/`curl` | Provider API keys |
| 12 | 🌙 **Kimi Code** | `curl` script | `/login` in `kimi` (membership OAuth) or Kimi Code Console API key |
| 13 | 🦅 **Kiro CLI** | `curl` script | `kiro-cli login` OAuth or `KIRO_API_KEY` (Pro+) |
| 14 | π **Pi Coding Agent** | `npm` | `/login` in `pi` (subscription OAuth) or provider API keys |
| 15 | 🦞 **OpenClaw** | `curl` script | `openclaw onboard` guided setup |
| 16 | ⬛ **Blackbox AI** | `npm` | API key from dashboard → `blackbox configure` |
| 17 | 🪿 **Goose** | `curl` script | `goose configure` or provider API keys |
| 18 | 🌀 **Cline** | `npm` | `cline auth` OAuth (Cline, ChatGPT) or BYOK |
| 19 | 🙌 **OpenHands CLI** | `curl` script | First-run LLM settings; `openhands login` for Cloud only |
| 20 | 💘 **Crush** | `npm` | `crush login` OAuth or provider env vars |
| 21 | 🔊 **Amp** | `curl` script | `amp login` (browser sign-in) or `AMP_API_KEY` |
| 22 | ✨ **Gemini CLI** | `npm` | Google OAuth in `gemini`, or `GEMINI_API_KEY` / `GOOGLE_API_KEY` |
| 23 | 🔮 **LLM** | `pip` | `llm keys set <provider>` or provider env vars |
| 24 | ▶️ **Continue CLI** | `curl` script | `cn login` (Continue account) or `ANTHROPIC_API_KEY` |
| 25 | 🐚 **Shell GPT** | `pip` | `sgpt` first-run key prompt or `OPENAI_API_KEY` |
| 26 | 🏭 **Droid** | `curl` script | `droid` on first use (Factory AI OAuth) |

---

## Commands

| Command | Description |
|---------|-------------|
| `aikit setup` | Interactive first-run wizard |
| `aikit install [agents...]` | Install agents (multi-select picker if none) |
| `aikit update [agents...]` | Update agents (all installed if none) |
| `aikit uninstall [agent...]` | Remove agents |
| `aikit list` | Status table of all 26 agents |
| `aikit auth [agent]` | Guided authentication setup |
| `aikit doctor` | Diagnose environment and agent health |
| `aikit serve` | Start web dashboard |
| `aikit config get/set/list` | Manage `~/.aikit/config.json` |
| `aikit gateway on/off/status/coverage/models` | Route AI tools through a LiteLLM gateway — see **[gateway docs](aikit-gateway.md)** |

### Multi-Select Picker

When no agents are specified, aikit shows an interactive multi-select menu:

```
Select agents to install
  Space = toggle  |  Enter = confirm  |  a = select all  |  n = deselect all  |  q = cancel

   1. [ ] 🧠 Claude Code
   2. [ ] 🛸 Antigravity
   3. [X] 🖱️ Cursor CLI
  ...
  Selected: 1/26  cursor
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
| `/api/config` | GET/POST | Read/update configuration |

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
├── Agent registry             # 26 agents, each with platform-aware install commands
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
