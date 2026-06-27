# 🛳️ keyferry — 1Password ⇄ Bitwarden/Vaultwarden Credential Ferry

**Intelligently migrate and sync passwords between 1Password and Bitwarden/Vaultwarden — with vault→collection mapping, content-aware deduplication, and timestamp-aware delta syncing that only updates when the source is newer.**

`keyferry` · Python 3 · `op` + `bw` · `rich` · `requests` · `readchar`

```bash
keyferry doctor                                       # Check op/bw CLIs and auth
keyferry status --from export.1pux                    # Compare both sides at a glance
keyferry plan  --from export.1pux  --to bitwarden     # Dry-run: what would be created / skipped
keyferry sync  --from export.1pux  --to bitwarden     # Ferry 1Password → Bitwarden
keyferry sync  --from bitwarden    --to 1password     # …or the other direction
```

One symmetric verb — **`sync --from <src> --to <dst>`** — moves credentials either way. `--from` accepts `1password`, `bitwarden`, or a `.1pux` file; `--to` accepts `1password` or `bitwarden`.

---

## Quick start

```bash
# Install (adds keyferry to PATH)
curl -fsSL https://raw.githubusercontent.com/pokanop/scripts/main/install.sh | bash -s -- --tools keyferry
# …or from a clone: ./install.sh --in-place --tools keyferry

# Vendor CLIs (installed separately):
#   op  — https://1password.com/downloads/command-line   (op signin)
#   bw  — native binary (not npm):
#         macOS:   brew install bitwarden-cli
#         Windows: choco install bitwarden-cli
#         Linux:   https://github.com/bitwarden/clients/releases  |  sudo snap install bw
#         Details: https://bitwarden.com/help/cli/   (bw login && bw unlock)

keyferry doctor
```

keyferry never writes anything until you run `sync` — and even then it only **creates** new items or **updates** matched items when the source is newer. `plan` (same flags as `sync`) is always safe.

### Vendor CLIs

keyferry shells out to the **native** Bitwarden CLI (`bw`) — not the npm package. Install separately:

| Platform | Install |
|----------|---------|
| **macOS** | `brew install bitwarden-cli` — or download from [GitHub releases](https://github.com/bitwarden/clients/releases) |
| **Windows** | `choco install bitwarden-cli` — or download from [GitHub releases](https://github.com/bitwarden/clients/releases) |
| **Linux** | Download from [GitHub releases](https://github.com/bitwarden/clients/releases), or `sudo snap install bw` |

Full options: [bitwarden.com/help/cli](https://bitwarden.com/help/cli/). After install: `bw login && bw unlock`.

The 1Password CLI (`op`) is separate: [1password.com/downloads/command-line](https://1password.com/downloads/command-line) → `op signin`.

---

## How it works

```
source adapter            normalize              route + dedup            sink
─────────────────         ─────────────          ─────────────────        ──────────────
1Password .1pux file  ┐                       ┌ private → My Vault
1Password live (op)   ┼─►  Item model  ──►  ──┼ shared  → org collection ──►  bw serve (fast)
Bitwarden live (bw)   ┘    + signature         └ archived→ Archived coll      op item create
```

1. **Read** items from a `.1pux` export, live `op`, or live `bw`.
2. **Normalize** every item to a source-agnostic model and compute a content **signature**.
3. **Route** each item to its destination via the mapping (private vs shared vs archived).
4. **Dedup** against what's already in the target — already-present items are skipped.
5. **Write** the deltas: Bitwarden via the `bw serve` REST fast-path (parallel), 1Password via `op item create`.

### Deduplication

Each item gets an identity signature from `title + username + URL-host` (configurable). The URL is reduced to its **host** so transient OAuth/SAML login URLs still match the same account. When a signature already exists at the destination, keyferry compares **visible content** and **last-modified timestamps** (`updatedAt` / `revisionDate`):

| Situation | Action |
|-----------|--------|
| Same visible content, source not newer | **Duplicate** — skip |
| Same visible content, source newer | **Update** — catches password/secret rotations |
| Different visible content, source newer | **Update** — pushes field/note changes |
| Different visible content, destination newer | **Duplicate** — skip (respects local edits) |

Pass `--overwrite` to force-update every match regardless of timestamps. Already-archived items are included in the dedup index, so re-runs won't re-create them. No extra API calls are made — timestamps come from data already loaded during `plan`/`sync`.

### Archived items

Bitwarden has a native **Archive** that works for both personal *and* organization items. keyferry uses it: an item that was archived in 1Password is created in its **normal destination** (Private → My Vault, shared → its collection) and then **natively archived in place** — exactly mirroring 1Password, where archived items keep their vault. There's no separate "Archived" collection to manage; the Archive view simply shows archived items across vaults/collections.

Control it with `mapping.archived_policy` (or per-run flags):

| Policy | Behavior |
|--------|----------|
| `native` *(default)* | Import to normal destination, then natively archive |
| `active` | Import to normal destination, leave active (`--archived-active`) |
| `skip` | Don't import archived items (`--skip-archived`) |
| `collection:<name>` | Divert all archived items into one collection (no native archive) |

---

## Commands

| Command | Description |
|---------|-------------|
| `keyferry doctor` | Check `op`/`bw` install, auth, versions, Python deps |
| `keyferry status` | Show both sides: 1P vaults & counts vs BW orgs/collections/counts |
| `keyferry plan` | Dry-run — preview create/update/skip per destination (no writes) |
| `keyferry sync` | Ferry credentials `--from` one side `--to` the other (either direction) |
| `keyferry map` | Interactively edit the vault→collection mapping |
| `keyferry tidy-folders` | Delete personal folders (e.g. tag→folder junk left by a native `bw import`) |
| `keyferry config get/set/list` | Manage configuration |

### Endpoints (`--from` / `--to`)

| Value | Meaning |
|-------|---------|
| `1password` (`1p`, `op`) | 1Password live via the `op` CLI |
| `bitwarden` (`bw`) | Bitwarden/Vaultwarden live via the `bw` CLI |
| `path/to/export.1pux` | A 1Password `.1pux` export — richest source (archived state + attachments). `--from` only |

`--from` and `--to` must be two different platforms. The richest path is `--from <.1pux> --to bitwarden`.

### sync / plan flags

| Flag | Meaning |
|------|---------|
| `--from SRC` / `--to DST` | Source and target endpoints (see above) |
| `--account SHORT` | `op` account shorthand (live 1Password, multi-account) |
| `--org NAME\|ID` | Target Bitwarden organization (auto-detected if you have one) |
| `--overwrite` | Force-update all matches, even when the destination is newer |
| `--skip-archived` | Don't transfer archived items |
| `--archived-active` | Transfer archived items but leave them active (don't native-archive) |
| `--keep-tags` | Preserve 1Password tags as a custom field (default: drop) |
| `--no-attachments` | Skip uploading file attachments |
| `-y, --yes` | Skip the confirmation prompt |

---

## Mapping

1Password has **vaults**; Bitwarden has a personal **My Vault** plus **collections** inside an organization. keyferry maps between them:

| 1Password | → | Bitwarden |
|-----------|---|-----------|
| `Private` / `Personal` vaults | → | **My Vault** (personal) |
| Any other (shared) vault | → | Org **collection** of the same name |
| Archived items | → | their normal destination, then **natively archived** |

Edit any of this with `keyferry map`, or directly via config:

```bash
keyferry config set mapping.private_destination personal
keyferry config set mapping.archived_policy native      # native | active | skip | collection:<name>
keyferry config set mapping.organization "My Organization"
keyferry config list
```

Per-vault collection name overrides live under `mapping.vault_to_collection` (default: same name). Missing collections are created automatically at sync time.

### Tags & folders

Bitwarden has **no tags/labels** — only folders (personal) and collections (org). 1Password tags therefore have no native home. keyferry **drops them by default** and **never creates folders** for them. Pass `--keep-tags` (or set `settings.tags = "field"`) to preserve them as a `1Password Tags` custom field instead.

> Note: Bitwarden's *native* `bw import 1password1pux` maps tags → folders, which produces a pile of (often duplicated) junk folders. If you've run a native import, clean it up with `keyferry tidy-folders` (`--empty-only` to remove just the empties). Deleting a folder only un-assigns its items — no items are lost.

---

## Examples

```bash
# First full migration from a 1Password export
keyferry sync --from 1PasswordExport.1pux --to bitwarden

# A second 1Password account that shares the Family/Everyone vaults:
# only its private vault + brand-new shared items come across — the rest dedup away.
keyferry sync --from 1password --to bitwarden --account work

# Refresh existing items in place (overwrite matches)
keyferry sync --from export.1pux --to bitwarden --overwrite

# Reverse direction: push Bitwarden into 1Password (dry-run first)
keyferry plan --from bitwarden --to 1password
keyferry sync --from bitwarden --to 1password
```

---

## Configuration

Config lives at `~/.keyferry/config.json` (permissions `0600`). Override the location with `KEYFERRY_CONFIG`.

Three-tier loading: built-in defaults → `~/.keyferry/config.json`.

```jsonc
{
  "settings": {
    "serve_port": 8087,        // local port for the bw serve fast-path
    "concurrency": 8,          // parallel writes against bw serve
    "match_keys": ["title", "username", "uri"]   // dedup signature components
  },
  "mapping": {
    "private_vaults": ["Private", "Personal"],
    "private_destination": "personal",
    "archived_policy": "native",     // native | active | skip | collection:<name>
    "vault_to_collection": {},
    "organization": null
  }
}
```

---

## Architecture

```
keyferry                       # Single-file Python script (~1,000 lines)
├── OpClient                   # 1Password CLI wrapper (vaults, items, documents, create)
├── BwClient                   # Bitwarden: bw CLI + bw serve REST fast-path (parallel writes)
├── Item + signature           # Source-agnostic credential model + dedup hash
├── Source adapters            # read_1pux · read_op_live · read_bw_live
├── Renderers                  # item_to_bw · item_to_op (category-aware)
├── Mapping resolver           # vault + archived-state → destination
└── Engine                     # build_plan / dedup / execute (create · overwrite · attachments)
```

**Notes & guarantees**
- Bitwarden field values over 10,000 chars (its hard limit) are diverted to a text **attachment** with a pointer left in the notes — nothing is silently truncated.
- Writes go through `bw serve` (a single local process) so parallel item creation can't corrupt the local cache; attachments upload via the `bw` CLI after the serve session closes.
- The `.1pux` source preserves archived state and attachments faithfully; live `op` mode derives archived state by diffing the archived listing.

---

## Development

```bash
git clone https://github.com/pokanop/scripts.git && cd scripts
./install.sh --in-place --tools keyferry
keyferry doctor
keyferry plan --from some-export.1pux --to bitwarden   # safe, read-only
```

---

## Related tools

Built on **[scriptkit](scriptkit.md)** — the shared CLI library (color, messages, progress, tables, config, subprocess). Building or editing a tool? See **[AGENTS.md](../AGENTS.md)**.

Part of the [scripts](../README.md) toolkit — [medcat](medcat.md) · [voxtract](voxtract.md) · [netsy](netsy.md) · [pluck](pluck.md) · [aikit](aikit.md)

---

## License

MIT — see [LICENSE](../LICENSE).
