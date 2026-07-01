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
aikit gateway off                             # unwrap: restore runtimes pristine (creds kept)
aikit gateway purge                           # forget the saved virtual key entirely
```

`on`/`off` is a **fast, zero-input toggle**: `off` returns your agent runtimes to
pristine but keeps aikit's own `0600` credential store, so flipping back `on` needs no
input. `purge` is the explicit **forget** that removes the saved credentials.

---

## How it works

`on` does five things and records them in a manifest:

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
4. **Writes native per-tool config + portable files** — see
   [Native per-tool config](#native-per-tool-config) below. Portable `gateway.env`
   (`0600`) and `gateway.json` land in `~/.aikit/gateway/`, and each wrapped tool gets a
   config in its own schema, staged under `tools/` and installed only when the tool is
   detected and has no config yet.
5. **Records a manifest** at `~/.aikit/gateway/state.json` (`0600`) — gateway URL,
   shell + rc path, markers, the backup path, model count, a checksum of the block, and
   every config file it wrote (with whether aikit created it) — so `off` and `status`
   know exactly what was applied.

> **Support for each provider ships as data.** A provider is a row in the
> `GATEWAY_PROVIDERS` table (prefix, key env vars, base env vars, route, detection),
> not a special case in the code. Adding a provider is adding a row.

---

## Native per-tool config

The env block covers every tool that reads `OPENAI_*` (or a provider's own) env vars.
Some tools, though, read **their own config file** instead — so `on` also generates a
config in each tool's native schema, populated with the models the gateway exposed.
Where a tool supports it, the file **references the key via an env var** (read from
`gateway.env` / your shell) rather than inlining the secret.

| Tool | Native config target | Key handling |
|------|----------------------|--------------|
| **opencode** | `~/.config/opencode/opencode.json` | `{env:OPENAI_API_KEY}` |
| **codex** | `~/.codex/config.toml` | `env_key = "OPENAI_API_KEY"` |
| **crush** | `~/.config/crush/crush.json` | `$OPENAI_API_KEY` |
| **goose** | `~/.config/goose/config.yaml` | `OPENAI_API_KEY` (env / keyring) |
| **pi** | `~/.pi/agent/models.json` | `!printf %s "$OPENAI_API_KEY"` (shell) |
| **hermes** | `~/.hermes/config.yaml` | `${OPENAI_API_KEY}` |
| **aider** | `~/.aider.conf.yml` | `$OPENAI_API_KEY` |
| **llm** | *staged only* (path varies) | env (`extra-openai-models.yaml`) |
| **continue** | *staged only* (path varies) | env (`gateway.env`) |
| **kilo** | `~/.config/kilo/kilo.json` | `{env:OPENAI_API_KEY}` |
| **qwen** | `~/.qwen/settings.json` | `envKey: OPENAI_API_KEY` |
| **cline** | `~/.cline/data/settings/providers.json` | *keyless* — `cline -k "$OPENAI_API_KEY"` at runtime |
| *every other OpenAI-compatible tool/SDK* | — | env layer only (no file) |

> The virtual key is **never** written into a native tool config — only into
> `gateway.env` (`0600`) and the managed rc block, which are the things that actually
> export it.

### Never clobber

Every rendered config is first **staged** under `~/.aikit/gateway/tools/`. It is
installed to the tool's real path **only when both** hold:

1. the tool is **detected** (via aikit's own agent registry — the same detection
   `aikit list` / `aikit doctor` use), and
2. **no config already exists** at that path.

If a config is already there, aikit **keeps it** and leaves the staged copy for you to
merge by hand — it never overwrites a file you own. `llm` and `continue` are always
staged-only because their real config path varies by install. `aikit gateway status`
shows, per tool, whether its config is *installed by aikit*, *user-owned (kept)*, or
*staged only*, and `aikit gateway on --dry-run` previews the whole plan without writing.

---

## Tool coverage

aikit knows 25 agents, but not all of them can be pointed at a third-party gateway.
Rather than silently route the ones it can and ignore the rest, aikit tracks a
**coverage state** for *every* agent and reports it — so you always know what's
wrapped, what isn't yet, and what never will be. `aikit gateway coverage` prints the
full matrix; `on` and `status` call out anything detected-but-not-routed inline.

| State | Meaning | Reaches the gateway? |
|-------|---------|----------------------|
| **renderer** | aikit writes the tool's native config (the 12 tools above) | ✅ yes |
| **env** | routed by a standard/provider env var the env block already sets | ✅ yes |
| **passthrough** | routed through a native-protocol passthrough route (`/anthropic`, `/gemini`, a custom route…), resolved at runtime from live discovery or a declared mapping | ✅ yes |
| **pending** | detected but not reliably routed yet — no renderer and no standard env var; a tracked gap | ❌ not yet |
| **unsupported** | no usable native passthrough route **and** no OpenAI-compatible / base-URL override path — with the real reason | 🚫 by design |

- **env-routed (5):** `claude` (`ANTHROPIC_BASE_URL`+`ANTHROPIC_AUTH_TOKEN`),
  `gemini` (`GEMINI_API_BASE`/`GOOGLE_GEMINI_BASE_URL`), `openclaw`, `sgpt` (via
  `OPENAI_BASE_URL`), and `openhands`. OpenHands reads `LLM_*` (not `OPENAI_*`) and only
  with `openhands --override-with-envs`, so `on` exports `LLM_BASE_URL`+`LLM_API_KEY` and
  the coverage row states that caveat (its on-disk `agent_settings.json`, if present,
  takes precedence). These need no native config — the env layer carries them.
- **passthrough:** any tool wired through a native-protocol route (base URL + auth var
  aimed at the route). Empty by default — the vendor CLIs below have a real route but no
  base-URL override — but a **declared custom mapping** (or a future tool that honours a
  base-URL override) lands here, showing its route + credential mode.
- **pending (3):** `grok`, `kimi`, `blackbox`. aikit detects them but has no route wired
  yet; each row's *How / why* records the config path a future renderer must write (e.g.
  grok needs `~/.grok/config.toml [model.*] base_url`) so the gap stays tracked, never
  hidden. (`kilo`, `cline`, `qwen` graduated to `renderer` and `openhands` to `env` in
  1.14.0.)
- **unsupported (5):** `antigravity`, `cursor`, `copilot`, `kiro`, `amp`. Routability
  is a *runtime* property, so these are re-examined against the live gateway:
  - `cursor` — LiteLLM **does** mount a `/cursor` (Cursor Cloud Agents) passthrough, and
    `antigravity`'s Gemini backend has a `/gemini` route — but `cursor-agent` / `agy`
    expose **no base-URL override** env var, so the tool can't be pointed at the route
    yet. The reason now names that tool-side gap (not the gateway), and a native renderer
    (Stage 8) or a custom mapping flips them to `passthrough`.
  - `copilot`, `kiro`, `amp` — LiteLLM mounts **no** native route for GitHub Copilot,
    Kiro, or Sourcegraph, so these stay `unsupported` unless you declare a custom route.

### Passthrough discovery + `verify`

A LiteLLM passthrough route is *always mounted* whenever the proxy runs — its presence
proves nothing about whether the upstream credential forwards. So aikit **discovers**
usable routes rather than assuming them:

```
usable routes = known built-in routes ∩ (provider-tag inference ∪ a live probe)
                ∪ any user-declared custom routes
```

`aikit gateway verify` runs the probe — a cheap, safe models-list `GET` per candidate
route (no tokens) — and reports each route's usability, **flagging any mounted-but-401
route** so a mis-forwarding upstream key is surfaced, not silently broken:

```bash
aikit gateway verify          # probe passthrough routes; flag mounted-but-401
```

### Custom passthrough routes (the escape hatch)

For a tool with no auto-discoverable native route (`amp`, `kiro`, `copilot`…), declare a
mapping in the gateway config (`~/.aikit/gateway/config.json`):

```json
{
  "base_url": "https://gw.example.com",
  "key": "sk-…",
  "credential_mode": "virtual_key",
  "passthroughs": {
    "amp": { "route": "/sourcegraph", "auth_var": "AMP_API_KEY", "base_url_var": "AMP_URL" }
  }
}
```

`route` is the gateway passthrough path; `base_url_var` is the tool's base-URL override
env var (wired through the managed block); `auth_var` is set to the virtual key. A
declared tool resolves to `passthrough` and is honoured by `coverage`/`status`/`verify`.
`on` merge-saves the config, so hand-added `passthroughs` survive a re-`on`.

### Credential modes

- **`virtual_key`** (default) — the caller sends the gateway virtual key; LiteLLM injects
  the shared upstream provider key. aikit sets the tool's auth var to the virtual key.
- **`forwarded_token`** — the gateway endpoint has `forward_headers: true` and forwards
  the caller's **own** token upstream (a personal subscription — this is what makes
  **Claude Code Max** work). Set `"credential_mode": "forwarded_token"`; aikit then sets
  base URLs but **leaves your auth token untouched** (so `/anthropic` keeps your OAuth
  token). Set per-passthrough with a `credential_mode` in the mapping.

```bash
aikit gateway coverage        # the full 25-row matrix: agent, detected?, state, how/why
```

> The guarantee: **no detected agent is silently omitted.** If aikit ever gains an
> agent that nobody has classified, it surfaces as `unclassified` in `coverage`
> (with a note to fix it) rather than disappearing from the report.

---

## The pristine-restore guarantee

The whole point of the gateway being an *aikit* feature (rather than a copy of a
setup script) is that it is **idempotent in both directions**:

| You run | Result |
|---------|--------|
| `on` then `on` (same args) | No net change — the managed block is replaced with identical content, the prior run's config files are reversed and rewritten, the manifest is refreshed. |
| `on` then `off` | Your **agent runtimes** return to **exactly** what they were before `on`: the managed block is gone, the backup is consumed, every file aikit wrote (`gateway.env`, `gateway.json`, staged copies, installed configs) is deleted along with any directory aikit created for them, and the manifest is cleared. aikit's own `config.json` credential store is **kept**, so re-`on` is input-free. |
| `off` then `on` (no flags) | Fast, zero-input re-toggle — the saved URL + key are reused (no prompt, just a quick model-list refresh), reproducing the same runtime surface. |
| `purge` | The explicit **forget**: deactivates first if active, then removes `config.json` and prunes `~/.aikit/gateway/`. After `purge`, re-enabling needs `-u`/`-k` again. |
| `off` / `purge` with nothing active/saved | Friendly no-op, exit 0. |
| Interrupted `on` (crash / Ctrl-C mid-write) | `off` still fully cleans up — including the secret-bearing `gateway.env`. |

`on` records its manifest **write-ahead**: the full set of files it's about to write is
committed to `state.json` *before* the first byte is written. So if `on` is interrupted
after files land but before it finishes, `off` still has the complete record and reverses
everything — no orphaned configs, and never an orphaned key file.

**"Pristine" means your agent runtimes** — your shell rc and your tool configs — not
aikit's private `~/.aikit/` state dir. `off` removes **only** aikit's managed block (a
precise splice that leaves the rest of your rc byte-for-byte intact) and **only** the
files aikit itself created (each recorded `created_by_aikit` in the manifest) — it never
touches a line you added to your rc or a tool config you owned. It also prunes the
now-empty directories it made (including `~/.aikit/gateway/tools/`). The one thing `off`
intentionally keeps is `~/.aikit/gateway/config.json` — aikit's own `0600` credential
store (your saved URL + key), like `~/.aws/credentials` or a `gh` token — so the next
`on` is a fast, input-free toggle. To forget the saved credentials entirely, run
**`aikit gateway purge`** (below); while OFF the key lives **only** in that `0600` store,
never in an agent-runtime file.

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
| `--dry-run` | Print the env block (key masked), the targeted providers, and the per-tool config plan (what each tool would get); write nothing locally. |
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
aikit gateway off [--dry-run] [--shell zsh] [--purge [-y]]
```

Removes the managed block, restores the rc file, deletes every config file aikit wrote
(portable files, staged copies, and configs aikit installed) along with any directory it
created for them, and clears the manifest. **Keeps** the saved credential store
(`config.json`) so the next `on` needs no input. A no-op (exit 0) when the gateway isn't
active. Pass `--purge` to also forget the saved credentials in one shot (equivalent to
`off` then `purge`; `-y` skips the confirmation).

### `aikit gateway purge`

```bash
aikit gateway purge [-y] [--dry-run] [--shell zsh]
```

The explicit **forget**. Removes aikit's saved credential store
(`~/.aikit/gateway/config.json`) and prunes `~/.aikit/gateway/`, so re-enabling the
gateway needs the URL + key again. If the gateway is currently **active**, `purge` first
runs the full `off` teardown (agent runtimes → pristine) and *then* removes the
credentials. Destructive, so it **confirms first** (`-y` to skip); `--dry-run` previews
without writing. A friendly no-op (exit 0) when nothing is saved. After `purge`, the
virtual key is absent from your machine entirely.

### `aikit gateway status`

Shows whether the gateway is active, the URL, the **masked** key, the model count, the
shell + rc path, a **wrapped-tools** table (per tool: detected?, and whether its config
is *installed by aikit*, *user-owned (kept)*, or *staged only*, with the path), and
**drift warnings** — if the managed block was hand-edited or removed from the rc,
`status` tells you (and `on` will restore it). Below the wrapped-tools table it also
accounts for **other detected agents** — the env-routed ones by name, and anything
detected-but-not-routed (`pending` / `unsupported`) with a pointer to `coverage` — so
nothing installed is left unmentioned. When **inactive but credentials are saved**, it
reports *inactive (credentials saved)* with the URL + masked key and points you at
`on` / `purge`; after `purge` it shows plain *inactive*. The default for a bare
`aikit gateway`.

### `aikit gateway coverage`

Read-only. Prints the full **25-row coverage matrix** — for every agent aikit knows:
`detected?`, its coverage **state** (`renderer` / `env` / `passthrough` / `pending` /
`unsupported`), and *how / why* (the routing var or config path, or the reason it isn't
routed) — plus a per-state tally. This is the honest, one-look answer to "does the
gateway cover tool X, and if not, why?" Custom passthroughs resolve here offline; run
`verify` to probe live built-in routes. See [Tool coverage](#tool-coverage) for what the
states mean.

### `aikit gateway verify`

Read-only, safe. Probes each candidate **passthrough route** (a cheap models-list `GET`,
no tokens) and reports its usability — and **flags any mounted-but-401 route**, where the
route exists but the gateway's upstream credential isn't forwarding (the POK-62 failure
mode). Run it after `on` to confirm the native routes you rely on actually work, or to
debug why a passthrough tool isn't reaching a provider. `on` also warns inline if a route
it's wiring probes 401.

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
- `gateway.env` (`0600`) also holds the key; its values are `shlex.quote`d, so a key
  containing a quote, `$`, or a backtick can't break `source gateway.env` or expand.
- **While OFF, the key lives only in aikit's `0600` `config.json`** — no agent-runtime
  file (rc, `gateway.env`, tool config) retains it. `off` keeps `config.json` for the
  fast toggle; **`aikit gateway purge`** removes it (and prunes the gateway dir), wiping
  the virtual key from your machine entirely.

---

## Doctor

`aikit doctor` includes a **Gateway** section: whether a gateway is configured,
whether it's reachable (`/v1/models`), and whether it's currently active.

---

## Files

| Path | Purpose | Removed by `off`? |
|------|---------|-------------------|
| `~/.aikit/gateway/config.json` | Gateway URL + virtual key (`0600`). | No by `off` (kept for fast re-toggle) — removed by `purge` |
| `~/.aikit/gateway/state.json` | Manifest of what `on` changed (`0600`). | Yes |
| `~/.aikit/gateway/gateway.env` | Portable, source-able export block (`0600` — holds the key). | Yes |
| `~/.aikit/gateway/gateway.json` | Machine-readable summary: URL, OpenAI base, providers, models. | Yes |
| `~/.aikit/gateway/tools/*` | Staged native per-tool configs (one per wrapped tool). | Yes |
| each tool's native path (e.g. `~/.config/opencode/opencode.json`) | Installed config — **only** when the tool was detected and had none. | Yes, **if aikit created it** |
| `<rc>.aikit-gateway.bak` | One-time backup of your rc before the first write. | Yes |

All paths honor the `AIKIT_CONFIG` override (consistent with the rest of aikit).

---

## Related tools

Part of **[aikit](aikit.md)**. The reversible env block is built on **[scriptkit](scriptkit.md)**'s
`ManagedBlock`. Building or editing a tool? See **[AGENTS.md](../AGENTS.md)**.

---

## License

MIT — see [LICENSE](../LICENSE).
