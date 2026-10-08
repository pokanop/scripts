# External runtime: install, verify, repair and roll back

`pokanop/scripts` consumes **pokanop-scriptkit 1.3.0** from
[pokanop/scriptkit](https://github.com/pokanop/scriptkit). Only that distribution
owns `scriptkit/*`; consumer package `pokanop-scripts` **1.1.0** is a dependency
metapackage with no Python modules. Tools, wrappers and user config locations are
unchanged. No new optional framework UX defaults are enabled.

## Pin and provenance

The supported compatibility interval is **`>=1.3.0,<1.4`**, independently enforced
by `pyproject.toml` and `requirements/base.txt`. The exact tested release is pinned
in package metadata and `requirements/runtime-constraints.txt`. Tests enforce
agreement between them. All per-tool requirement files include base requirements.

- [Durable release](https://github.com/pokanop/scriptkit/releases/tag/runtime-1.3.0-7c17061)
- Reviewed source commit: `7c17061dfaae1290e975ac28c4e75d7bb28eeb4d`
- [Successful signed Release run](https://github.com/pokanop/scriptkit/actions/runs/37731967290)
- Wheel: `pokanop_scriptkit-1.3.0-py3-none-any.whl`
- SHA-256: `9943818c01ac5f0017c389a2c1baba08843bc59aee5374ababb992dff7aa8e7a`

This is the reviewed compatibility release artifact, **not a PyPI publication**.
Naming/trusted-publisher setup remains separate. GitHub release assets are durable
rather than Actions-retention downloads. Every install/update needs access to
github.com because pip re-fetches the direct-URL runtime wheel, even if already
installed. Content identity is immutable through the
SHA-256 pin: replacement bytes fail pip installation. This does not claim that an
administrator cannot delete a GitHub release; availability still depends on GitHub.
Never replace these assets; publish a new version/tag/hash for a new release.

Verify downloaded assets before changing pins:

```sh
gh release download runtime-1.3.0-7c17061 --repo pokanop/scriptkit
sha256sum --check SHA256SUMS
gh attestation verify pokanop_scriptkit-1.3.0-py3-none-any.whl \
  --repo pokanop/scriptkit \
  --signer-workflow pokanop/scriptkit/.github/workflows/release.yml \
  --source-digest 7c17061dfaae1290e975ac28c4e75d7bb28eeb4d \
  --signer-digest 7c17061dfaae1290e975ac28c4e75d7bb28eeb4d \
  --source-ref refs/heads/main --deny-self-hosted-runners
```

The expected `main` ref above binds the **historical signed build**, with its exact
commit; it is not a mutable-main dependency. Installation uses the release URL
plus hash. The runtime workflow tested Linux/macOS/Windows and Python 3.11–3.14.

## Fresh installs and ordinary updates

Existing `install.sh`, `install.ps1`, `scripts install`, `scripts update`, per-tool
requirements and editable/package installs all resolve the pinned wheel. Harness-
only installs include it too. A bare-Python installer needs no runtime to bootstrap.
For a new development environment:

```sh
python3 -m venv venv
venv/bin/python -m pip install -e '.[dev,keyferry,aikit,pluck]'
venv/bin/python -m pytest
```

On Windows use `venv\Scripts\python.exe`. The direct URL precedes the compatibility
range in package metadata so pip discovers the unpublished artifact before trying
the package index. Keep both requirements and their order.

## Existing 1.0.0 wheel ownership and repair

**Do not upgrade the old consumer wheel with plain `pip install -U .`.** Pip may
install the framework dependency before uninstalling the old consumer, which owns
the same files. Use the lifecycle installer first, from the updated checkout:

```sh
python3 scripts install --no-pull --no-path --dir /path/to/install --bin-dir /path/to/bin
# If you use the optional consumer metapackage, install its new metadata afterward:
/path/to/install/venv/bin/python -m pip install -e /path/to/install
```

Use your existing install and bin directories (or omit overrides to use recorded
ones). The installer queries **the target venv's** distribution metadata, removes
legacy `pokanop-scripts` ownership, installs base requirements normally, then
force-reinstalls only the pinned runtime with `--no-deps`. A plain install preserves
already-satisfied base dependency versions; only `--upgrade`/update upgrades them.
This also repairs a previously overlapping or interrupted install whose runtime metadata
survived but files did not. Modern dependency-only consumer metadata is retained.
Used git clones can retain ignored `scriptkit/__pycache__` after the source update.
The bootstrap treats that empty namespace package as unavailable and removes the
orphaned directory after repair only if it contains bytecode alone (no sources,
symlinks or user files). It never deletes user configs. Wrappers and the marker are only rewritten after
successful dependency installation; repair does not change their target paths.

A network failure or interruption can leave that venv temporarily unable to run
tools. This is **recoverable, not transactional**: rerun the same command with a
bare system Python once connectivity returns. Do not depend on a broken wrapper to
repair its own interpreter. No source runtime is retained as a shadow fallback.

## Rollback

Record the old source commit and keep/rebuild its wheel before upgrading. The
verified pre-extraction baseline is `458104a52bafe619a259ed2b83ecd7a3b29c82c1`.
To roll back, stop tool processes, uninstall **both** runtime and consumer metadata
from the same venv, restore that source revision in the same install directory,
then install its wheel/requirements. For example, with a clean checkout:

```sh
venv/bin/python -m pip uninstall -y pokanop-scriptkit pokanop-scripts
git switch --detach 458104a52bafe619a259ed2b83ecd7a3b29c82c1
venv/bin/python -m pip install . -r requirements/base.txt
```

Do not uninstall one overlapping distribution after reinstalling the other. Do not
remove the venv, wrapper directory, `.scripts-install.json`, or `~/.<tool>` configs.
Existing wrappers continue pointing at the same interpreter and script paths.
Restore the migration revision and run bare-Python `scripts install` to roll forward.

## Executable evidence

- `python -m pytest`: full existing compatibility suite plus pin/ownership,
  outside-CWD imports/help, install failure and KeyboardInterrupt regressions.
- `python tests/rehearse_runtime_migration.py`: disposable clean venv, real old and
  new wheels, fresh/harness install, platform shell bootstrap, per-tool install,
  update, metadata-only wheel, overlapping ownership migration, interrupted-uninstall
  repair and rollback; configs, marker and wrapper preservation asserted. Also
  upgrades a used legacy git clone (real ignored bytecode) through bare-Python and
  platform shell installers, and checks non-upgrade base-version preservation.
- CI runs that rehearsal and external-runtime tests on Linux/macOS/Windows,
  Python 3.11 and 3.14. The existing complete Linux suite remains mandatory;
  `required-quality` rejects any failed/cancelled/skipped prerequisite job.

Windows CLI tests use UTF-8 (`PYTHONUTF8=1`, or `-X utf8` with isolated Python).
The existing emoji banners can fail with redirected cp1252 streams; this is a
pre-existing compatibility limitation, not a runtime migration behavior change.
The existing POSIX-only `voxtract` imports `fcntl`, so its Windows help smoke is
explicitly skipped; the other seven help cases and the complete migration/rollback
rehearsal still run there. This migration does not port voxtract to Windows.
