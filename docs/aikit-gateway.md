# 🤖 aikit gateway — one virtual key for every AI tool

**Route every OpenAI-compatible CLI and SDK on your machine through a single
LiteLLM-style gateway with one virtual key — then switch back, leaving everything
pristine.**

The gateway itself is stood up server-side (providers, models, base URLs, budgets
all live on the gateway). `aikit gateway` configures *your machine* to use it, and —
unlike a one-shot setup script — records exactly what it changed so it can undo it
**completely**.

```bash
aikit gateway on -u https://gw.example.com   # wrap: point every tool at the gateway
aikit gateway status                          # what's active right now
aikit gateway off                             # unwrap: restore your machine pristine
```

---

## How it works

`on` does four things and records them in a manifest:

1. **Discovers models** — `GET {gateway}/v1/models` (any valid key), plus the richer
   `GET {gateway}/model/info` when your key is allowed to see it.
2. **Builds the env block** — a universal OpenAI-compatible block
   (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_API_BASE`, `LITELLM_PROXY_*`) plus,
   for each of the 65 known providers, every key env var set to your virtual key and
   every base-URL env var pointed at the gateway (`{gateway}{route}` — e.g.
   `/anthropic`, `/gemini`, `/bedrock` native pass-throughs, or the OpenAI-compatible
   `/v1`).
3. **Writes a managed block** to your shell rc (`zsh` / `bash` / `fish`) between
   aikit-owned markers:
   ```
   # >>> aikit gateway (managed — run 'aikit gateway off' to remove) >>>
   …exports…
   # <<< aikit gateway <<<
   ```
   The rc file is backed up once (`<rc>.aikit-gateway.bak`) before the first write.
4. **Records a manifest** at `~/.aikit/gateway/state.json` (`0600`) — gateway URL,
   shell + rc path, markers, the backup path, model count, and a checksum of the
   block — so `off` and `status` know exactly what was applied.

> **Support for each provider ships as data.** A provider is a row in the
> `GATEWAY_PROVIDERS` table (prefix, key env vars, base env vars, route, detection),
> not a special case in the code. Adding a provider is adding a row.

---

## The pristine-restore guarantee

The whole point of the gateway being an *aikit* feature (rather than a copy of a
setup script) is that it is **idempotent in both directions**:

| You run | Result |
|---------|--------|
| `on` then `on` (same args) | No net change — the managed block is replaced with identical content, the manifest is refreshed. |
| `on` then `off` | The rc file and environment-affecting state return to **exactly** what they were before `on`: the managed block is gone, the backup is consumed, the manifest is cleared. |
| `off` with nothing active | Friendly no-op, exit 0. |
| Interrupted `on` | `off` still fully cleans up from whatever the manifest captured. |

`off` removes **only** aikit's managed block (a precise splice that leaves the rest of
your rc byte-for-byte intact) and clears aikit's own state — it never touches lines you
added yourself.

---

## Commands

### `aikit gateway on`

```bash
aikit gateway on -u https://gw.example.com [-k sk-…]
```

| Flag | Effect |
|------|--------|
| `-u, --url` | Gateway base URL. Prompted if omitted and not saved. |
| `-k, --key` | Virtual key (`sk-…`). **Hidden prompt** if omitted and not saved. |
| `--dry-run` | Print the env block (key masked) and the targeted providers; write nothing locally. |
| `-y, --yes` | Skip the confirmation prompt. |
| `--only-discovered` | Only set env vars for providers actually backing the discovered models. |
| `--shell {zsh,bash,fish}` | Override shell detection. |

> **`--dry-run` is not offline-safe.** It still validates the key by calling the
> gateway's `/v1/models` first (matching the reference's validate-then-preview), so it
> needs a reachable gateway and a valid key — it just doesn't write any local files.

The URL and virtual key are saved to `~/.aikit/gateway/config.json` (`0600`), so later
runs don't need the flags again.

### `aikit gateway off`

```bash
aikit gateway off [--dry-run] [--shell zsh]
```

Removes the managed block, restores the rc file, and clears the manifest. A no-op
(exit 0) when the gateway isn't active.

### `aikit gateway status`

Shows whether the gateway is active, the URL, the **masked** key, the model count,
the shell + rc path, and **drift warnings** — if the managed block was hand-edited or
removed from the rc, `status` tells you (and `on` will restore it). The default for a
bare `aikit gateway`.

### `aikit gateway models`

Read-only listing of the models your key can see, tagged with their provider when the
gateway reports it. Handy for sanity-checking a URL + key before `on`.

---

## Security

- The virtual key is persisted at `~/.aikit/gateway/config.json` with `0600`
  permissions, **masked** in `status` / `models` / `doctor`, and never written to logs.
- Only **inference-scoped** environment variables are set. General-purpose
  credentials other tooling relies on — `AWS_ACCESS_KEY_ID`, `GITHUB_TOKEN` /
  `GH_TOKEN`, `GOOGLE_APPLICATION_CREDENTIALS`, `HF_TOKEN`, `DATABRICKS_TOKEN`, … —
  are deliberately left untouched, so routing through the gateway never clobbers your
  git / cloud / hub auth.
- The env block in your rc contains the virtual key in plaintext (that *is* the
  mechanism — it's your file, and `off` removes it cleanly).

---

## Doctor

`aikit doctor` includes a **Gateway** section: whether a gateway is configured,
whether it's reachable (`/v1/models`), and whether it's currently active.

---

## Files

| Path | Purpose |
|------|---------|
| `~/.aikit/gateway/config.json` | Gateway URL + virtual key (`0600`). |
| `~/.aikit/gateway/state.json` | Manifest of what `on` changed (`0600`). |
| `<rc>.aikit-gateway.bak` | One-time backup of your rc before the first write. |

All paths honor the `AIKIT_CONFIG` override (consistent with the rest of aikit).

---

## Related tools

Part of **[aikit](aikit.md)**. The reversible env block is built on **[scriptkit](scriptkit.md)**'s
`ManagedBlock`. Building or editing a tool? See **[AGENTS.md](../AGENTS.md)**.

---

## License

MIT — see [LICENSE](../LICENSE).
