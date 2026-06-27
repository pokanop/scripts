# 🤖 aikit — AI Coding Agent CLI Installer & Manager

**Install, update, authenticate, and manage 16 AI coding agent CLIs from one tool.**

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

## Agents (16)

| # | Agent | Install | Auth |
|---|-------|---------|------|
| 1 | 🧠 **Claude Code** | `curl` script | OAuth (browser) or `ANTHROPIC_API_KEY` |
| 2 | 🛸 **Antigravity** | `curl` script | OAuth (Google account) |
| 3 | 🖱️ **Cursor CLI** | `curl` script | OAuth (`agent` or `cursor-agent`) |
| 4 | ☤ **Hermes Agent** | `curl` script | OAuth (Nous Portal) or API keys |
| 5 | 📟 **Codex CLI** | `curl` script | OAuth (ChatGPT) or `OPENAI_API_KEY` |
| 6 | ⚡ **Kilo CLI** | `npm` | Kilo account or BYOK |
| 7 | 🔓 **OpenCode** | `npm` | Provider API keys |
| 8 | 🐉 **Qwen Code** | `npm` | Alibaba Coding Plan or API keys |
| 9 | 🐙 **GitHub Copilot CLI** | `curl` script | `GH_TOKEN` PAT or OAuth |
| 10 | 🚀 **Grok Build** | `curl` script | OAuth (`grok` or `agent`) or `XAI_API_KEY` |
| 11 | 🤝 **Aider** | `pip`/`curl` | Provider API keys |
| 12 | 🌙 **Kimi Code** | `curl` script | Kimi membership subscription |
| 13 | 🦅 **Kiro CLI** | `curl` script | Kiro account subscription |
| 14 | π **Pi Coding Agent** | `npm` | Provider API keys |
| 15 | 🦞 **OpenClaw** | `curl` script | OAuth onboard flow |
| 16 | ⬛ **Blackbox AI** | `npm` | API key from dashboard |

---

## Commands

| Command | Description |
|---------|-------------|
| `aikit setup` | Interactive first-run wizard |
| `aikit install [agents...]` | Install agents (multi-select picker if none) |
| `aikit update [agents...]` | Update agents (all installed if none) |
| `aikit uninstall [agent...]` | Remove agents |
| `aikit list` | Status table of all 16 agents |
| `aikit auth [agent]` | Guided authentication setup |
| `aikit doctor` | Diagnose environment and agent health |
| `aikit serve` | Start web dashboard |
| `aikit config get/set/list` | Manage `~/.aikit/config.json` |

### Multi-Select Picker

When no agents are specified, aikit shows an interactive multi-select menu:

```
Select agents to install
  Space = toggle  |  Enter = confirm  |  a = select all  |  n = deselect all  |  q = cancel

   1. [ ] 🧠 Claude Code
   2. [ ] 🛸 Antigravity
   3. [X] 🖱️ Cursor CLI
  ...
  Selected: 1/16  cursor
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

## Architecture

```
aikit                          # Single-file Python script (~1,600 lines)
├── Agent registry             # 16 agents, each with platform-aware install commands
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
