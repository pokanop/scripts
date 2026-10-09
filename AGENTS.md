# Pokanop scripts — contributor and agent guide

## Boundaries

This repository is a **consumer** of external `pokanop-scriptkit`, not a second
framework or package manager. Never vendor a `scriptkit/` package. Runtime,
registry, archive validation, wheel-lock verification, environment creation and
per-tool receipts belong in the external framework. The exact release URL and
SHA-256 live in `requirements/runtime-constraints.txt`; the supported range is
`>=1.5.0,<1.6`. Update both with independent release evidence.

`pokanop_manager/` contains only this collection's catalog, a pip wheel-preparation
adapter, and coordination of the legacy marker/public-wrapper transition. Do not
copy framework resolvers or installers into it. Pip resolves/builds wheels;
ScriptKit installs the complete verified lock offline.

## Layout and lifecycle

- Six existing tools are extension-less Python files at the repository root.
- `pokanop_manager/catalog.json` is the single discovery catalog. `TOOLS` and
  `TOOL_NAMES` in the host are compatibility views derived from it, never lists
  to edit independently.
- `requirements/<tool>.txt` declares each built-in tool's dependencies.
- `scripts` is the CLI/bootstrap host; shell and PowerShell installers delegate
  to it. Keep bare-Python repair and dependency-free discovery/help functional.
- `venv/` is the legacy shared environment/harness. Migration never deletes it.
  Missing framework services can be bootstrapped in `.scripts-harness/` without
  mutating the old shared environment.
- `.scripts-state/transactions/` retains immutable tool bundles, wheel locks,
  private ScriptKit generations, receipts and previous routing snapshots.
- `.scripts-install.json` is the single atomic routing commit for a migration
  batch. Stage and smoke **all** selected tools before switching this marker.
- Public wrappers handle both v1 and v2 routing. Never overwrite foreign/edited
  tool wrappers. Per-tool uninstall retains environments; full uninstall removes
  toolkit environments and honors PATH/source-retention flags. User config is
  always retained. Garbage collection between installs is not automatic.

See [manager migration](docs/manager-migration.md) for dry-run, rollback, source
trust, lock preparation, platform limits and interruption semantics.

## New tools: use the external repository-layout scaffold

1. Install the pinned framework release in your authoring environment. Create a
   validated `ToolSpec` JSON (the framework ships an example resource).
2. Generate into a **new disposable project directory**, not this repository root:

   ```sh
   mkdir /path/to/new-project
   python -m scriptkit new-tool /path/to/new-project --spec /path/to/tool.json --layout repository --apply
   ```

   Consult `python -m scriptkit new-tool --help` for the installed release's CLI.
   This generates an extension-less `bin/<name>` launcher, importable `src/`
   modules, tests, docs, requirements and a tool spec. Implement user-owned
   `_handlers.py`; preserve generated ownership markers and manifests.
3. Register and install explicitly (registration trusts local executable code):

   ```sh
   python scripts register /path/to/new-project
   python scripts install mytool --no-pull --no-path
   ```

   Framework requirements in the generated project are pinned to its generating
   version. The collection constrains that version to its verified GitHub wheel,
   so public PyPI availability is not needed.
4. Verify `mytool --help`, `mytool doctor`, and a real implemented command.
   Unimplemented scaffold handlers must fail clearly; bare invocation must not
   mutate state. Add tests for pure functions and installed wrappers.
5. Remove without touching unrelated tools or project sources:

   ```sh
   python scripts uninstall mytool --keep-path
   python scripts unregister mytool
   ```

For a new **built-in legacy tool**, add one catalog entry, its root script,
`requirements/<name>.txt`, optional packaging extra, docs and tests. Do not edit
host code or a separate list. `templates/tool_template.py` remains a compatibility
example for existing single-file tools, not the recommended new-project generator.

## Editing existing tools

- Import `scriptkit as sk` normally; no ancestor-search or sys.path runtime hacks.
- Reuse `sk.Config`, output/style, tables, progress and subprocess helpers.
  Don't create another Rich Console or hand-code ANSI. Honor NO_COLOR/FORCE_COLOR.
- Keep heavyweight imports lazy so help/discovery do not load Torch or other tools.
- Use `sk.make_parser`, `sk.parse_args`, `sk.dispatch` and `sk.run_cli`.
  Banner goes to stderr; normal/machine data stays on stdout. `-v` is version,
  never verbose. Every tool has help, version and `sk.doctor`.
- Tool errors subclass `sk.CliError`; expected failures return 1 and interrupts
  return 130. Use `run_cli(on_interrupt=...)` for cleanup, not ad-hoc handlers.
- Choose a read-only default or help for potentially destructive tools.
- Config/state lives in `~/.<tool>/`, honors `<TOOL>_CONFIG`, never in the repo.
  Use the framework's layered config and secret-safe file modes. Preserve state
  during migration, rollback and uninstall.
- Declare every imported dependency in the per-tool requirements and appropriate
  packaging extra. Never silently install all tools' heavy dependencies.
- Keep functions small and typed; isolate platform and provider adapters. Test
  success, failure, interruption and backward compatibility for lifecycle changes.

## Versions and changelog

Tools version independently. Every changed tool gets one bump per PR: MAJOR for
breaking CLI/config changes; MINOR for additive commands/flags/UX; PATCH for an
invisible fix/refactor. Keep `__version__`, docstring version, versioned docs H1 and
`CHANGELOG.md` synchronized. Extend an existing unmerged PR bump rather than bumping
again for each fix. Preserve user Git identity. Rebase feature branches; never
merge main into them.

## Verification

```sh
python -m pip install -e '.[dev,keyferry,aikit,pluck]'
python -m pytest
python tests/rehearse_runtime_migration.py
python tests/rehearse_generated_tool.py
# Optional heavyweight Linux rehearsal; downloads PyPI CUDA Torch dependencies:
python tests/rehearse_manager.py /path/to/new-empty-install
```

Unit/characterization tests use `tests/conftest.py`'s `tool_loader` for root tools.
Keep existing characterization behavior unless an intentional change is documented.
The required CI migration matrix runs on Linux/macOS/Windows and Python 3.11/3.14.
The existing Voxtract implementation is POSIX-only (`fcntl`); do not claim Windows
support or end-to-end media processing based solely on help/install smoke evidence.

`CLAUDE.md` is a symlink to this guide. The external framework's authoring and
conformance rules apply to generated projects; do not duplicate its implementation.
