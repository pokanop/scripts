# 🧰 scriptkit — Shared CLI scaffolding

**The common library every tool in this repo is built on: color, icons, semantic
messages, prompts, progress, tables, three-tier config, subprocess handling,
human-friendly formatting, and CLI dispatch — unified so every tool looks and
behaves like it came from the same author.**

`scriptkit` · Python 3.11+ · `rich` (optional, graceful fallback) · zero other deps

```python
import scriptkit as sk

sk.success("done")                       # ✅ green, stdout
sk.error("nope")                         # ❌ red, stderr
for item in sk.track(items, "Working"):  # spinner + bar + M/N + elapsed
    ...
cfg = sk.Config(path, defaults={...}, env_prefix="MYTOOL").load()
res = sk.run(["git", "status"])          # Result(code, out, err)
sys.exit(sk.run_cli(main))               # CliError → exit 1, Ctrl-C → exit 130
```

---

## Why

Every tool had grown its own copy of the same helpers — ANSI codes, `print_success`,
a `run()` wrapper, dot-path config, a progress bar. `scriptkit` is the single,
tested home for those patterns. Change the house style in one place; every tool
updates. New tools start beautiful for free.

It is **import-safe without `rich`**: messages and tables degrade to plain ANSI /
text, so it is even safe for the bootstrap installer running under a bare system
Python.

---

## How it's wired in

Tools are extension-less scripts that run as `venv/bin/python <repo>/<tool>`, so the
repo root (which holds the `scriptkit/` package) is automatically on `sys.path`.
Each tool simply does `import scriptkit as sk`. No install step, no vendoring.

The new-tool template adds an upward-search bootstrap so a tool works even when run
from a symlink or another directory:

```python
_here = Path(__file__).resolve().parent
for _base in (_here, *_here.parents):
    if (_base / "scriptkit" / "__init__.py").exists():
        sys.path.insert(0, str(_base)); break
import scriptkit as sk
```

---

## API at a glance

### Messages (`scriptkit.console`)
| Call | Output |
|------|--------|
| `sk.success(text)` | `  ✅ text` — bold green, stdout |
| `sk.error(text)` | `  ❌ text` — bold red, **stderr** |
| `sk.warning(text)` | `  ⚠️  text` — bold yellow |
| `sk.info(text)` | `  ℹ️  text` — dim cyan |
| `sk.detail(text)` | dim continuation line, no icon |
| `sk.step(n, total, text)` | `  [2/5] text` |
| `sk.header(text)` | a section rule (rich) or `━━━ text ━━━` |
| `sk.elapsed(label, secs)` | `  ⏱️  label: 4.2s` |
| `sk.kv(label, value)` | aligned `label: value` |
| `sk.ask(prompt, default)` | line input, `default` on empty/EOF |
| `sk.confirm(prompt, default)` | yes/no, returns bool |

### Color & icons (`scriptkit.style`)
- `sk.styled(text, *codes)` — wrap in ANSI, or strip codes when color is off.
- `sk.use_color(stream=None)` / `sk.set_color(True|False|None)` — honors
  `NO_COLOR` and `FORCE_COLOR`; auto-detects TTY otherwise.
- `sk.icon(name)` — semantic emoji lookup (`success`, `warn`, `clock`, `rocket`, …).
- Color constants: `sk.style.RED`, `BOLD`, `DIM`, `CYAN`, …

### Progress (`scriptkit.progress`)
- `sk.track(iterable, "desc")` — iterate with a spinner+bar+M/N+elapsed (rich) or plainly.
- `sk.status("message")` — context manager spinner for indeterminate work.
- `sk.parallel_map(fn, items, "desc", max_workers=8)` — threaded map with combined progress.
- `sk.bar(pct, width=30)` — a pure-string `[████░░░] 50%` for inline `\r` updates.

### Tables (`scriptkit.tables`)
```python
sk.table(
    [{"name": "#", "justify": "right"}, "Host", {"name": "Status"}],
    [[1, "router", "[green]up[/]"]],
    title="Hosts",
)
```
Columns are strings or dicts (`name`, `justify`, `style`, `width`, `max_width`,
`no_wrap`). Falls back to an aligned text grid without `rich`.

### Config (`scriptkit.config`)
```python
cfg = sk.Config(path, defaults={"web": {"port": 8765}},
                env_prefix="MYTOOL", coerce_env=True)
data = cfg.load()                 # defaults < file < MYTOOL_WEB__PORT
sk.get_nested(data, "web.port")   # 8765
sk.set_nested(data, "web.host", "0.0.0.0")
cfg.save(data)                    # pretty JSON, chmod 0600
```
`coerce_env`/`coerce=True` turns scalar strings (`"true"`, `"9000"`, `"3.5"`)
into their natural types — handy for env-var overrides.

### Subprocess (`scriptkit.proc`)
```python
res = sk.run(["git", "rev-parse", "HEAD"])   # Result(code, out, err); res.ok / bool(res)
res = sk.run(cmd, check=True)                 # non-zero → CliError
sk.which("ffmpeg")                            # bool
sk.require("ffmpeg", hint="brew install ffmpeg")  # missing → CliError
```
Timeouts return code `-1`; a missing binary returns `-127`. Never raises for a
non-zero exit unless `check=True`.

### Text (`scriptkit.text`)
`sk.human_size(1536) → "1.5 KB"` · `sk.human_duration(185) → "3m 5s"` ·
`sk.format_timecode(75.5) → "1:15.50"` · `sk.human_count(2, "host") → "2 hosts"` ·
`sk.truncate("hello world", 8) → "hello w…"`

### CLI (`scriptkit.cli`)
- `sk.CliError(msg)` — raise for expected failures; printed cleanly, exit 1.
- `sk.run_cli(main)` — wraps `main`: `CliError` → 1, `KeyboardInterrupt` → 130,
  int return → exit code.
- `sk.dispatch(args, handlers, parser)` — route `args.command` to a handler dict.

### Identity & CLI framing (`scriptkit.app`)

Every tool presents the **same first impression** — one identity line, a
`-v/--version` flag, and an aligned `Examples:` epilog — by building its parser
through `sk.make_parser` instead of `argparse.ArgumentParser`.

```python
ICON = "🚀"                        # one distinct brand emoji per tool
TAGLINE = "does the thing"          # short; shown after the em-dash

parser = sk.make_parser(
    "mytool", __version__, TAGLINE, icon=ICON,
    examples=[("mytool go", "run it"), ("mytool doctor", "check env")],
)
sub = parser.add_subparsers(dest="command")
```

- **`sk.banner(name, version, tagline, icon)`** → the identity line
  `🚀 mytool v1.2.3 — does the thing` (name bold-cyan, version dim, NO_COLOR-aware).
  Use it for `--help` (automatic via `make_parser`) *and* at runtime: `print(banner())`.
- **`sk.make_parser(prog, version, tagline, *, icon, examples=None, epilog=None, …)`**
  — sets the banner description, a `RawDescription` formatter, and a `-v/--version`
  flag. Pass `examples=[(cmd, desc), …]` for an aligned epilog, or your own `epilog=`.
- **`sk.examples_block(items)`** → the aligned `Examples:` block, if you want it standalone.

> **`-v` means `--version` across the whole toolkit.** Don't reuse `-v` for
> `--verbose` (use `--verbose`); a conflicting `-v` will fail to register.

Define `ICON`/`TAGLINE` as module constants so the help banner, `--version`, and any
runtime banner all read from one source of truth.

The current brand emojis: 🛠️ scripts · 🤖 aikit · 🛳️ keyferry · 📚 medcat ·
📡 netsy · 🪶 pluck · 🌊 voxtract. Use `sk.header("Section")` for in-tool section
rules (`━━━ Section ━━━━━`) so sections look identical everywhere.

---

## Building a new tool

> See **[AGENTS.md](../AGENTS.md)** for the complete recipe (registering in the
> installer, requirements, docs, tests) and the conventions agents should follow.

```bash
cp templates/tool_template.py mytool     # extension-less, house style
chmod +x mytool
$EDITOR mytool                            # rename toolname/TOOLNAME, add subcommands
./mytool --help
```

The template is a working CLI demonstrating every primitive (messages, a tracked
loop, a table, config, subprocess, `CliError`, dispatch). It is covered by
`tests/test_template.py` so it can't rot.

Then register it in the `scripts` installer (`TOOLS` dict + `TOOL_NAMES`), add a
`requirements/mytool.txt`, and a `docs/mytool.md` card.

---

## Tests

```bash
venv/bin/python -m pytest          # whole suite
```

- `tests/test_*.py` — scriptkit unit tests (color, config, proc, console, progress,
  tables, cli) — all mockable, no network/subprocess side effects beyond local echo.
- `tests/test_tools_characterization.py` — pins each tool's pure helpers and `--help`
  so the shared-library refactor is provably non-breaking.
- `tests/test_template.py` — keeps the new-tool scaffold healthy.

---

## License

MIT — see [LICENSE](../LICENSE).
