# 🛠️ scripts

**Daily-use CLI utilities.** One tool, one job, zero ceremony.

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-blue?style=flat-square" alt="Cross-platform">
  <img src="https://img.shields.io/badge/tools-6-orange?style=flat-square" alt="6 tools">
</p>

---

## Quick start

**One-liner (macOS / Linux):**

```bash
curl -fsSL https://raw.githubusercontent.com/pokanop/scripts/main/install.sh | bash
```

**Windows (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/pokanop/scripts/main/install.ps1 | iex
```

**Git clone (contributors / forks):**

```bash
git clone https://github.com/pokanop/scripts.git
cd scripts
./install.sh --in-place
```

**Update an existing install:**

```bash
scripts update
# or re-run the installer:
curl -fsSL https://raw.githubusercontent.com/pokanop/scripts/main/install.sh | bash -s -- --update
```

**Uninstall:**

```bash
scripts uninstall -y          # full remove (wrappers, venv, PATH block)
scripts uninstall medcat pluck  # remove specific tools only
```

For git clones, `scripts uninstall` removes wrappers and `venv/` but keeps the repo. A curl install to `~/.local/share/scripts` removes the entire install directory. Tool config in `~/.medcat/`, `~/.keyferry/`, etc. is left intact.

The one-liner installs the `scripts` harness (venv, `scripts` CLI, PATH). Add tools afterward — only what you need:

```bash
scripts install medcat pluck      # add selected tools
scripts install all               # install every tool
./install.sh --tools medcat,pluck # same, via installer flags
```

**Manual / package-manager path:**

```bash
git clone https://github.com/pokanop/scripts.git ~/.local/share/scripts
cd ~/.local/share/scripts
python3 -m venv venv
./venv/bin/pip install -r requirements/medcat.txt   # per-tool
./venv/bin/pip install -r requirements.txt          # all tools
./scripts install --no-path                         # create wrappers only
export PATH="$HOME/.local/bin:$PATH"
```

Or install deps via `pyproject.toml` extras from a clone:

```bash
pip install -e ".[medcat,pluck]"
pip install -e ".[all]"
```

Run `scripts doctor` to verify PATH, Python deps, and system tools (`ffmpeg`, `nmap`, `op`, `bw`).

---

## Toolkit

<table>
<tr>
<td width="50%" valign="top">

### 🛳️ [keyferry](docs/keyferry.md)

**1Password ⇄ Bitwarden credential ferry**

Migrate and sync passwords between 1Password and Bitwarden/Vaultwarden — vault→collection mapping, content-aware deduplication, timestamp-aware delta syncing, attachments, and a `bw serve` fast-path.

`keyferry` · Python 3 · `op` + `bw`

</td>
<td width="50%" valign="top">

### 📚 [medcat](docs/medcat.md)

**Media stack ingest tool**

Ingest books, comics, movies, shows, and music into your media stack with metadata extraction from Google Books, Open Library, and MusicBrainz.

`medcat` · Python 3

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🌊 [voxtract](docs/voxtract.md)

**Voice extract tool**

Download audio from YouTube, Spotify, Jellyfin, Plex, podcasts, URLs, or local files — clip by timestamp and isolate speech with Demucs neural separation.

`voxtract` · Python 3 · `ffmpeg`

</td>
<td width="50%" valign="top">

### 📡 [netsy](docs/netsy.md)

**LAN discovery tool**

Ping-scan the local subnet and list live hosts with hostname, IP, MAC address, and vendor. Multi-pass scans, host search, and watch mode for intermittent devices.

`netsy` · Python 3 · `nmap` · `rich`

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🪶 [pluck](docs/pluck.md)

**Config key-path tool**

Pluck values from config files by dot path — copy, merge, read, set, and diff across YAML, JSON, TOML, and `.env` with cross-format support.

`pluck` · Python 3.11+ · `ruamel.yaml` · `rich` · `tomli-w`

</td>
<td width="50%" valign="top">

### 🤖 [aikit](docs/aikit.md)

**AI coding agent CLI manager**

Install, update, authenticate, and manage 31 AI coding agent CLIs from one tool — interactive picker, status dashboard, and web UI.

**Gateway:** `aikit gateway on` routes every OpenAI-compatible tool/SDK through one LiteLLM-style gateway with a single virtual key — env block **plus** native per-tool config (opencode, codex, crush, goose, pi, hermes, aider, …), never clobbering an existing config — then `aikit gateway off` restores everything **pristine**. See **[gateway docs](docs/aikit-gateway.md)**.

`aikit` · Python 3 · `rich` · `flask` · `requests`

</td>
</tr>
</table>

---

## Shared library: [scriptkit](docs/scriptkit.md)

Every tool is built on **[`scriptkit`](docs/scriptkit.md)** — one tested home for
color, icons, semantic messages, prompts, progress bars, tables, three-tier config,
subprocess handling, and CLI dispatch. Change the house style once; every tool
updates. It degrades gracefully without `rich`, so it's safe even in the installer.

```python
import scriptkit as sk
sk.success("done"); sk.error("nope")          # ✅ stdout / ❌ stderr
for x in sk.track(items, "Working"): ...       # spinner + bar + M/N + elapsed
cfg = sk.Config(path, defaults={...}, env_prefix="MYTOOL").load()
sys.exit(sk.run_cli(main))                      # CliError → 1, Ctrl-C → 130
```

---

## Conventions

| Principle | What it means |
|-----------|---------------|
| **Self-contained** | One script, one job — no framework sprawl |
| **Shared scaffolding** | UX/structure comes from [`scriptkit`](docs/scriptkit.md), not copy-paste |
| **No hidden deps** | Everything beyond the runtime is listed above |
| **Clean repo** | Config and cache live in `~/.<tool>/`, never in the repo |
| **Tested** | `venv/bin/python -m pytest` — unit + characterization + template smoke |

---

## Adding a new tool

1. `cp templates/tool_template.py mytool` — a working CLI on `scriptkit`.
2. Rename `toolname`/`TOOLNAME`, add your subcommands, keep `--help`.
3. Register it in the `scripts` installer (`TOOLS` + `TOOL_NAMES`) and add
   `requirements/mytool.txt`.
4. Add a card above and link to `docs/<tool>.md`.
5. Reuse `scriptkit` for all output/config/subprocess — don't re-roll helpers.

> **Contributing or using an AI agent?** Read **[AGENTS.md](AGENTS.md)** — the full
> guide to the runtime model, `scriptkit`, conventions, [versioning](AGENTS.md#versioning--changelog),
> testing, and step-by-step recipes for building a new tool or editing an existing one.
> (`CLAUDE.md` is a symlink to it.) Each tool is versioned independently; changes are
> recorded in **[CHANGELOG.md](CHANGELOG.md)**.

---

## License

MIT — see [LICENSE](LICENSE).# self-hosted runner






