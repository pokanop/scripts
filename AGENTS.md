# AGENTS.md — guide for building & editing tools in this repo

This file orients coding agents (and humans) working in `pokanop/scripts`. It is
the source of truth for conventions; `CLAUDE.md` is a symlink to it.

> **Golden rule:** every tool is built on the shared **[`scriptkit`](docs/scriptkit.md)**
> library. Don't re-roll colors, messages, progress, tables, config, or subprocess
> handling — import them. Change the house style in one place, not seven.

---

## TL;DR for an agent

- **New tool?** `cp templates/tool_template.py <name>` → edit → register in `scripts`
  (`TOOLS` + `TOOL_NAMES`) → add `requirements/<name>.txt` → add `docs/<name>.md` →
  add tests. Full steps below.
- **Editing a tool?** Reuse `scriptkit` for all output/config/subprocess. Run the
  test suite before and after. Don't add a dependency you don't list.
- **Always run:** `venv/bin/python -m pytest` (140+ tests must stay green).
- **Tools are extension-less Python files at the repo root** (`medcat`, `pluck`, …),
  run by a venv Python. The repo root holds `scriptkit/`, so `import scriptkit` just works.

---

## Repository layout

```
scripts                      # the installer/lifecycle host (also a tool)
medcat keyferry voxtract     # the tools — extension-less Python scripts at repo root
netsy pluck aikit
scriptkit/                   # shared library every tool imports
  style.py console.py progress.py tables.py
  config.py proc.py text.py cli.py __init__.py
templates/tool_template.py   # the scaffold for a new tool
tests/                       # pytest suite (unit + characterization + template)
  conftest.py                # load_tool() imports extension-less scripts as modules
requirements/<tool>.txt      # per-tool pip deps (base.txt is shared)
docs/<tool>.md               # one user-facing doc per tool
docs/scriptkit.md            # the shared-library reference
install.sh install.ps1       # bootstrap installers
pyproject.toml               # packaging + pytest config
```

---

## How tools run (the runtime model)

Install (`install.sh` / `scripts install`) clones the repo to an **install dir**
(`~/.local/share/scripts` by default, or in-place for a git clone), creates a venv,
installs per-tool requirements, and writes thin **wrapper** scripts to a **bin dir**
(`~/.local/bin`). Each wrapper does:

```bash
exec "<install_dir>/venv/bin/python" "<install_dir>/<tool>" "$@"
```

Because the tool file lives at the install-dir root, `sys.path[0]` is that root —
which contains `scriptkit/`. So **`import scriptkit as sk` resolves with no install
step or vendoring.** The template additionally walks parent dirs to find
`scriptkit/`, making new tools location-independent.

`scriptkit` is **import-safe without `rich`** (it degrades to plain ANSI/text), so
even the bootstrap `scripts` installer can use it under a bare system Python.

---

## The scriptkit library

Full reference: **[docs/scriptkit.md](docs/scriptkit.md)**. The surface you'll use most:

```python
import scriptkit as sk

# messages (success/warning/info/step to stdout; error to stderr)
sk.success("done"); sk.error("nope"); sk.warning("careful"); sk.info("fyi")
sk.step(2, 5, "building"); sk.header("Section"); sk.kv("Host", "router")
sk.elapsed("build", 4.2)                      # ⏱️  build: 4.2s

# prompts
name = sk.ask("Name", default="world"); ok = sk.confirm("Proceed?", default=True)

# progress
for item in sk.track(items, "Processing"): ...
with sk.status("Reading…") as s: s.update("…")
results = sk.parallel_map(fn, items, "Working", max_workers=8)

# tables (rich when available, plain grid otherwise)
sk.table([{"name": "#", "justify": "right"}, "Host"], [[1, "router"]], title="Hosts")

# config: defaults < ~/.tool/config.json < TOOL_* env
cfg = sk.Config(path, defaults={...}, env_prefix="MYTOOL", coerce_env=True).load()
sk.get_nested(cfg, "web.port"); sk.set_nested(cfg, "web.host", "0.0.0.0")

# subprocess: Result(code, out, err); never raises unless check=True
res = sk.run(["git", "status"]); res.ok; bool(res)
sk.which("ffmpeg"); sk.require("ffmpeg", hint="brew install ffmpeg")

# text
sk.human_size(1536); sk.human_duration(185); sk.truncate(s, 40)

# CLI plumbing
raise sk.CliError("clean user-facing message")   # → printed, exit 1
sys.exit(sk.run_cli(main))                        # CliError→1, Ctrl-C→130
return sk.dispatch(args, HANDLERS, parser)        # route args.command

# identity & framing — same first impression for every tool
ICON, TAGLINE = "🚀", "does the thing"
parser = sk.make_parser("mytool", __version__, TAGLINE, icon=ICON,
                        examples=[("mytool go", "run it")])   # banner + -v/--version + epilog
print(sk.banner("mytool", __version__, TAGLINE, ICON))        # runtime banner
sk.header("Section")                                          # ━━━ Section ━━━━━
```

Need rich directly (Panel, Syntax, Tree, custom markup)? Use the **shared console**:
`sk.rich_console` / `sk.err_console`. Don't construct your own `Console()` — share
these so styling stays consistent.

---

## Building a new tool

1. **Copy the scaffold** (extension-less name, house style):
   ```bash
   cp templates/tool_template.py mytool
   chmod +x mytool
   ```
   The scaffold is a working CLI demonstrating messages, a tracked loop, a table,
   config, subprocess, `CliError`, and `dispatch`.

2. **Edit `mytool`:** replace `toolname`/`TOOLNAME`, set `__version__`, write your
   subcommands as `cmd_*` functions, and register them in the `HANDLERS` dict and
   `build_parser()`. Keep the upward-search `scriptkit` bootstrap at the top.

3. **Register it in the `scripts` installer** so it can be installed/updated. In the
   `scripts` file add an entry to `TOOLS` and append the name to `TOOL_NAMES`:
   ```python
   "mytool": {
       "description": "One-line description",
       "requirements": "requirements/mytool.txt",
       "system": [("ffmpeg", False, "audio decode — brew install ffmpeg")],  # (binary, required, hint)
   },
   ```

4. **Add `requirements/mytool.txt`** listing only this tool's pip deps (don't repeat
   `base.txt`, which already provides `rich` + `requests`). Mirror it under
   `pyproject.toml`'s `[project.optional-dependencies]` if you want `pip install
   pokanop-scripts[mytool]` to work.

5. **Add `docs/mytool.md`** following the existing tool docs (quick start, commands,
   config, the "Related tools" + scriptkit footer), and add a card in `README.md`.

6. **Add tests** (see Testing). At minimum: a `--help` smoke test and unit tests for
   your pure functions. Characterization tests live in
   `tests/test_tools_characterization.py`.

7. **Verify:** `./mytool --help`, exercise a command, then `venv/bin/python -m pytest`.

---

## Editing an existing tool

- **Reuse `scriptkit`.** If you need output/config/subprocess, import it — don't add
  a local helper that duplicates one. If `scriptkit` is missing something broadly
  useful, add it to the library (with a test) rather than to one tool.
- **Preserve behavior.** Run `venv/bin/python -m pytest` before and after. The
  characterization tests in `tests/test_tools_characterization.py` pin each tool's
  pure helpers and `--help`; keep them passing. If you intentionally change behavior,
  update the test and say so.
- **Match the surrounding code.** These are single-file tools; follow the existing
  structure, naming, and comment density in the file you're editing.
- **Don't introduce undeclared dependencies.** New import → add it to the tool's
  `requirements/<tool>.txt` (and `pyproject.toml`).

---

## Versioning & changelog

Every tool (and `scriptkit`) is versioned **independently** with
[Semantic Versioning](https://semver.org). The "public API" of a tool is its CLI:
its commands, flags, output format, exit codes, and config schema.

**When you change a tool, bump it** — pick the level by the *largest* change:

| Level | Bump | When |
|-------|------|------|
| **MAJOR** `X.0.0` | breaking | Remove/rename a command or flag, **change a flag's meaning**, change output/exit-code/config-schema in a way that could break existing scripts. |
| **MINOR** `x.Y.0` | additive | New command, flag, source, or format; new optional config; a notable backwards-compatible UX addition (e.g. adding `--version` where it was missing). |
| **PATCH** `x.y.Z` | invisible | Bug fix, internal refactor (e.g. moving onto `scriptkit`), dependency bump, help/doc wording, cosmetic styling — **no interface change**. |

Rules of thumb:
- **No interface change ⇒ PATCH.** Refactoring a tool onto `scriptkit` with identical
  observable behavior is a PATCH, even if a lot of code moved.
- A `scriptkit` change that alters a tool's *observable* behavior bumps **that tool too**
  (at the matching level), plus `scriptkit` itself.
- New tools start at **`0.1.0`** (the scaffold default).
- When unsure between two levels, prefer the higher one and say why in the changelog.

**Every bump touches the same places (keep them in sync):**
1. The `__version__ = "X.Y.Z"` constant.
2. The version in the module docstring header (`name — desc  vX.Y.Z`).
3. The docs H1 *if* it pins a version (e.g. `docs/medcat.md`, `docs/netsy.md`).
4. A `CHANGELOG.md` entry under that tool's section (newest on top), dated `YYYY-MM-DD`,
   with a one-line-per-change summary. Flag breaking changes with a leading `⚠`.

> Don't bump for changes that don't touch the tool file (pure test/doc edits elsewhere).

---

## Conventions

**Output & UX**
- Use the `scriptkit` message helpers; don't hand-roll ANSI or `print("✅ …")`.
- Errors go to **stderr** (`sk.error` already does this); normal output to stdout.
- Honor `NO_COLOR` / `FORCE_COLOR` — automatic via `scriptkit`. Never hardcode color
  on; never assume a TTY.
- Exit codes: success `0`, expected failure `1` (raise `sk.CliError`), interrupt
  `130` (automatic via `sk.run_cli`). Don't `sys.exit()` with ad-hoc codes for
  user errors — raise `CliError`.
- **Identity:** build the parser with `sk.make_parser(...)` and define module-level
  `ICON` + `TAGLINE`, so every tool shows the same `{icon} name vX.Y.Z — tagline`
  banner. Pick a distinct brand emoji (current set: 🛠️ scripts · 🤖 aikit ·
  🛳️ keyferry · 📚 medcat · 📡 netsy · 🪶 pluck · 🌊 voxtract).
- **`-v`/`--version` is universal** (added by `make_parser`). Never repurpose `-v`
  for `--verbose` — use `--verbose`. Use `sk.header()` for section rules.
- Every tool has a `--help` and a one-line module docstring header (`name — desc  vX.Y.Z`).

**Configuration**
- Per-tool state lives in `~/.<tool>/` (e.g. `~/.medcat/config.json`), **never** in
  the repo. Honor a `<TOOL>_CONFIG` env override for the dir.
- Use `sk.Config` for three-tier loading (defaults < file < `TOOL_*` env). Use
  `coerce_env=True` so env scalars (`"9000"`, `"true"`) become natural types.
- Save with `0600` (`sk.Config.save` does this) for anything that may hold secrets.

**Code**
- Tools are extension-less Python at the repo root, `#!/usr/bin/env python3`,
  `from __future__ import annotations`.
- Prefer one file per tool unless it genuinely needs a package.

---

## Testing

Run everything:

```bash
venv/bin/python -m pytest          # or: -p no:cacheprovider for a clean run
```

The suite has three layers:
- **`tests/test_*.py`** — `scriptkit` unit tests (mockable; no network, no real
  subprocess beyond a local `echo`/`python -c`).
- **`tests/test_tools_characterization.py`** — pins each tool's pure helpers and
  `--help`. This is what makes refactors provably non-breaking. Add cases here for
  new pure functions.
- **`tests/test_template.py`** — keeps the new-tool scaffold healthy.

**Importing an extension-less tool in a test:** use the `tool_loader` fixture
(`tests/conftest.py`), which loads the script via `SourceFileLoader` and registers
it in `sys.modules` (required so `@dataclass` forward-refs resolve):

```python
def test_my_pure_fn(tool_loader):
    m = tool_loader("mytool")
    assert m.parse_thing("a.b") == ["a", "b"]
```

For end-to-end CLI behavior, prefer a subprocess smoke test:
`subprocess.run([sys.executable, str(REPO_ROOT / "mytool"), "--help"])`.

If your tool imports heavy/optional deps at module load, keep `--help` cheap (don't
import torch/yt-dlp at top level if you can defer it) so smoke tests stay fast.

---

## Gotchas

- **`scriptkit` resolves via `sys.path[0]`** (the tool's directory). When you run a
  tool from elsewhere it still works because Python puts the *script's* dir on the
  path, not the cwd. Tests insert the repo root explicitly (see `conftest.py`).
- **`bool` is an `int`.** Handlers/`main` should return `None` or a real int exit
  code, not a bool. `scriptkit.dispatch`/`run_cli` guard against this, but don't rely
  on it.
- **Config coercion** turns `"3.5"`→`3.5` and `"true"`→`True`. If a config value must
  stay a string that looks numeric/boolean, don't pass `coerce=True` for that path.
- **The `scripts` installer must stay robust.** Its `scriptkit` import is guarded
  (`try/except`) so a broken library can't brick installs — keep it that way.
- **Don't construct a new `rich.Console()`** in a tool — use `sk.rich_console` /
  `sk.err_console`.

---

## Checklists

**New tool**
- [ ] `cp templates/tool_template.py <name>`, edit, keep the `scriptkit` bootstrap
- [ ] `ICON` + `TAGLINE` set; parser via `sk.make_parser`; `__version__ = "0.1.0"`
- [ ] Subcommands wired into `build_parser()` + `HANDLERS`
- [ ] Registered in `scripts` (`TOOLS` + `TOOL_NAMES`)
- [ ] `requirements/<name>.txt` (+ `pyproject.toml` extra)
- [ ] `docs/<name>.md` + README card + `CHANGELOG.md` section
- [ ] Tests: `--help` smoke + pure-function unit tests
- [ ] `venv/bin/python -m pytest` green

**Editing a tool**
- [ ] Output/config/subprocess go through `scriptkit`
- [ ] New deps declared in `requirements/<tool>.txt`
- [ ] **Version bumped** (MAJOR/MINOR/PATCH) in `__version__` **and** the docstring
      header (and docs H1 if pinned) — see [Versioning](#versioning--changelog)
- [ ] `CHANGELOG.md` entry added under the tool's section
- [ ] Characterization tests still pass (or updated intentionally)
- [ ] `venv/bin/python -m pytest` green
