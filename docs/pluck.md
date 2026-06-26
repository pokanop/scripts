# 🪶 pluck — Config Key-Path Tool

**Pluck values from config files by dot path — copy, merge, read, set, and diff across YAML, JSON, TOML, and .env with cross-format support.**

`pluck` · Python 3.11+ · `ruamel.yaml` · `rich` · `tomli-w`

```bash
pluck get config.yaml model                         # Read a key
pluck set config.yaml model gpt-4o                  # Set a key
pluck copy source.yaml dest.yaml model,providers    # Copy paths across files
pluck diff a.yaml b.yaml model providers            # Compare keys
```

---

## Quick start

```bash
pluck copy source.yaml dest.yaml model,providers,fallback_providers
pluck merge source.yaml dest.yaml providers
pluck get config.yaml model
pluck set config.yaml model gpt-4o
pluck diff a.yaml b.yaml model providers

# Cross-format: YAML → JSON
pluck copy settings.yaml config.json model providers

# .env support
pluck get .env API_KEY
pluck set .env API_KEY sk-xxx --backup
pluck copy app.yaml .env.local database redis
```

---

## Supported Formats

| Format | Extensions | Notes |
|--------|------------|-------|
| YAML | `.yaml`, `.yml` | Round-trip comments via ruamel.yaml |
| JSON | `.json` | Pretty-printed output |
| TOML | `.toml` | stdlib read + tomli-w write |
| ENV | `.env`, `.env.*` | Flat keys; comments preserved on round-trip |

Format is **auto-detected** from the file extension. Override with `--format`, `--src-format`, or `--dest-format`.

---

## Key Paths

Paths use dot notation. List indices use brackets:

| Path | Meaning |
|------|---------|
| `model` | Top-level key |
| `providers.openai` | Nested mapping |
| `servers[0].host` | First list item, then nested key |

Keys accept comma- or space-separated lists (positional or `-k`):

```bash
pluck copy src.yaml dst.yaml model,providers,fallback_providers
pluck copy src.yaml dst.yaml -k model,providers
pluck copy src.yaml dst.yaml model providers fallback_providers
```

Put many keys in a file (one per line, `#` comments allowed) and pass `--keys-file paths.txt`.

### .env flat keys

`.env` files are flat `KEY=value` pairs. Nested paths map to conventional env names:

| Path | .env key |
|------|----------|
| `API_KEY` | `API_KEY` |
| `providers.openai` | `PROVIDERS_OPENAI` |
| `database.host` | `DATABASE_HOST` |

Dict/list values are JSON-encoded in the env value. Comments and blank lines are preserved when updating existing files.

---

## Commands

| Command | Description |
|---------|-------------|
| `pluck copy SRC DEST` | Overwrite key paths in `DEST` with values from `SRC` |
| `pluck merge SRC DEST` | Deep-merge dicts at each path; replace scalars and lists |
| `pluck get FILE PATH` | Print the value at `PATH` (`--json` for JSON output) |
| `pluck set FILE PATH VALUE` | Set `PATH` to `VALUE` (parsed per format) |
| `pluck diff A B` | Compare keys between two files (cross-format OK) |
| `pluck formats` | List supported formats and detection rules |
| `pluck doctor` | Check dependencies |

### Transfer flags (`copy` / `merge`)

| Flag | Meaning |
|------|---------|
| `KEY ...` | Positional key paths (comma/space-separated groups OK) |
| `-k`, `--keys KEYS` | Key paths (comma/space-separated; repeatable) |
| `--keys-file FILE` | File listing key paths |
| `--src-format FMT` | Force source format (cross-format transfers) |
| `--dest-format FMT` | Force destination format |
| `--create-missing` | Create dest file or missing intermediate keys |
| `-n`, `--dry-run` | Show result without writing |
| `--backup` | Save `.bak` before overwriting |

---

## Examples

```bash
# Sync model + provider blocks between configs (any format mix)
pluck copy ~/.config/opencode/opencode.json.yaml ~/.config/opencode/local.yaml \
  model,providers,fallback_providers --backup

# Pull database settings from TOML into .env for local dev
pluck copy pyproject.toml .env.local database --create-missing

# Preview cross-format copy
pluck copy upstream.yaml my.json providers --dry-run

# Compare env vs yaml for the same logical keys
pluck diff .env.example config.yaml API_KEY DATABASE_URL

# Set structured JSON value in a YAML file
pluck set config.yaml retry '{"max": 3, "delay": 1}'
```

---

## How It Works

1. **Detect format** from extension (or `--format` override).
2. **Load** into a shared tree structure (dict/list for hierarchical formats; flat dict for `.env`).
3. **Navigate** dot paths through nested mappings and list indices.
4. **`copy`** replaces each destination subtree with a deep clone from source.
5. **`merge`** recursively merges mappings at each path; non-dict values from source replace destination values.
6. **Save** back in the destination format (YAML comments preserved via ruamel.yaml; env comments preserved line-by-line).

---

## Development

```bash
git clone https://github.com/pokanop/scripts.git && cd scripts
./install.sh --in-place --tools pluck
pluck doctor
pluck formats
pluck copy test-src.yaml test-dst.json model --dry-run
```

---

## Related tools

Part of the [scripts](../README.md) toolkit — [keyferry](keyferry.md) · [medcat](medcat.md) · [voxtract](voxtract.md) · [netsy](netsy.md) · [aikit](aikit.md)

---

## License

MIT — see [LICENSE](../LICENSE).