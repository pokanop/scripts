# External runtime dependency and repair

`pokanop/scripts` consumes **scripteer==2.0.0 from PyPI**. Package metadata,
`requirements/base.txt` and `requirements/runtime-constraints.txt` agree on this
exact version. No framework package is vendored. The pre-rename GitHub releases
were deleted; do not use old asset URLs or mechanically rename their hashes.

## Upgrade a collection install

Update this checkout, then use the same install and bin directories as before:

```sh
python scripts install --dir /path/to/scripts --bin-dir /path/to/bin --no-pull --no-path
python scripts migrate --dir /path/to/scripts --bin-dir /path/to/bin --dry-run
python scripts migrate --dir /path/to/scripts --bin-dir /path/to/bin
```

The first command repairs the shared harness; the last stages selected tools with
Scripteer in new isolated environments. Pass explicit tool names for a partial
migration. Old environments, routing snapshots and tool configuration are retained.
See [manager migration](manager-migration.md) for rollback boundaries.

The installer guards its runtime import. Mutating operations bootstrap missing
manager services in `.scripts-harness/` and reinvoke the host. Help, discovery and
migration dry-run need only stdlib. Harness repair removes an old overlapping
`pokanop-scripts` wheel owner before installing the new framework, then force
reinstalls only the pinned runtime without gratuitous base-dependency upgrades.
Only known orphaned `scriptkit/__pycache__/*.pyc` files are pruned; unknown files
and sources are retained. That historical name is intentional cleanup logic,
not a dependency or import alias. Interrupted repair is rerunnable.

Legacy uninstall remains offline. Full uninstall also removes the harness, but
never user configuration. Existing pre-rename external packages need not be
uninstalled from shared environments used by other applications.

## Standalone framework state is a separate migration

Scripteer deliberately has no compatibility aliases. Its root precedence is
`--root`, `SCRIPTEER_ROOT`, then `~/.scripteer`; interpreter selection uses
`SCRIPTEER_PYTHON`. Old environment variables and default directories are ignored.
Adopt an old root explicitly with `--root /path/to/old-root`, or move it yourself.
Re-bootstrap that root with the independently verified **new** standalone
bootstrap. Keep old installations side by side if needed; do not edit receipts.
Standalone manager receipts must contain `module: scripteer`: dispatch and
self-rollback reject module-less/pre-rename receipts. Rollback across that boundary
requires your retained old bootstrap and artifacts, not the deleted releases.

New wire identifiers are `.scripteer-lock`, `.scripteer-generator`,
`# >>> scripteer:...` regions and `urn:scripteer:contracts:*:1` schema IDs.
Re-apply managed regions instead of renaming ownership metadata. Optional keyring
credentials use service `scripteer.ai` and account `openai`; manually save credentials
under the new service if desired. No secrets or state are copied automatically.

Pre-rename generated projects must be regenerated with `python -m scripteer
new-tool` in a fresh directory. Copy user-owned handlers, initializers, README,
configuration examples, tests and CI, and reconcile handwritten imports/settings.
Do not rename old ownership manifests or overwrite user edits. Register the new
project directory and reinstall it in the collection. See the framework's
[migration guide](https://github.com/pokanop/scripteer/blob/main/docs/scripteer-launch.md).

## Verification

`python tests/rehearse_runtime_migration.py` builds the real old distribution from
pinned commit `458104a52bafe619a259ed2b83ecd7a3b29c82c1` and rehearses clean PyPI
installation, repair, selective install/update, wheel/editable ownership cleanup,
used-clone bytecode cleanup and an explicit old-source rollback in disposable
environments. `tests/rehearse_generated_tool.py` exercises current scaffolds.
CI runs these on Linux/macOS/Windows and Python 3.11/3.14.
