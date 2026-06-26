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

### 🔑 [keyferry](docs/keyferry.md)

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

### 🎙️ [voxtract](docs/voxtract.md)

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

Install, update, authenticate, and manage 16 AI coding agent CLIs from one tool — interactive picker, status dashboard, and web UI.

`aikit` · Python 3 · `rich` · `flask` · `requests`

</td>
</tr>
</table>

---

## Conventions

| Principle | What it means |
|-----------|---------------|
| **Self-contained** | One script, one job — no framework sprawl |
| **No hidden deps** | Everything beyond the runtime is listed above |
| **Clean repo** | Config and cache live in `~/.<tool>/`, never in the repo |

---

## Adding a new tool

1. Keep it to one file unless it genuinely needs a package.
2. Add `--help` and a short docstring.
3. If it has non-standard deps, list them in the toolkit section.
4. Add a card above and link to `docs/<tool>.md`.
5. If it's substantial, make it a subdirectory with its own `SKILL.md`.

---

## License

MIT — see [LICENSE](LICENSE).