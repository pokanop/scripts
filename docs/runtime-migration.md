# External runtime dependency and repair

`pokanop/scripts` consumes **pokanop-scriptkit 1.5.0**; it owns no `scriptkit/`
package. The supported interval `>=1.5.0,<1.6` is enforced by both package metadata
and `requirements/base.txt`. `requirements/runtime-constraints.txt` selects the
exact verified wheel, not PyPI discovery or a mutable branch.

- [Release v1.5.0](https://github.com/pokanop/scriptkit/releases/tag/v1.5.0)
- Source/tag commit: `96714be2479b4b4b1b6207a4d8db66c3aa07ceea`
- Wheel: `pokanop_scriptkit-1.5.0-py3-none-any.whl`
- SHA-256: `89307e39af78f0c92d7002e60b30cf10e5015c35aaa5bc67b57b547822bdc75b`
- URL: `https://github.com/pokanop/scriptkit/releases/download/v1.5.0/pokanop_scriptkit-1.5.0-py3-none-any.whl`

```sh
gh release download v1.5.0 --repo pokanop/scriptkit
gh attestation verify pokanop_scriptkit-1.5.0-py3-none-any.whl \
  --repo pokanop/scriptkit \
  --signer-workflow pokanop/scriptkit/.github/workflows/release.yml \
  --source-digest 96714be2479b4b4b1b6207a4d8db66c3aa07ceea \
  --signer-digest 96714be2479b4b4b1b6207a4d8db66c3aa07ceea \
  --source-ref refs/tags/v1.5.0 --deny-self-hosted-runners
```

The original runtime extraction used runtime-only 1.3.0; that artifact cannot
provide manager/scaffold services. 1.5.0 additionally supplies the bounded policy
needed for Torch-class wheels. This interim GitHub release is not final branding
or public PyPI launch approval.

## Bare-Python and old wheel ownership

The installer guards its runtime import. If the manager API is absent or broken,
mutating CLI operations bootstrap the exact dependency in `.scripts-harness/` and
reinvoke the host there, without importing the broken runtime first. Discovery,
help and migration dry-run need only stdlib and the collection's catalog adapter.

Harness-only repair (`scripts install --no-pull`) maintains the legacy `venv/`
host. It probes old `pokanop-scripts` distribution ownership in that target venv,
uninstalls an old overlapping runtime owner **before** reinstalling framework
files, then force-reinstalls only the exact runtime without gratuitously upgrading
other base requirements. Interrupted repair is rerunnable. Only known orphaned
`scriptkit/__pycache__/*.pyc` files are pruned; unknown files/sources are retained.
Tool configuration and existing wrappers are preserved if dependency repair fails.

Selected-tool installation, update and explicit v1 migration now use isolated
immutable generations. See [manager migration](manager-migration.md) for the atomic
multi-tool handoff, failure recovery, per-tool/full uninstall and rollback.

## Rehearsals

`python tests/rehearse_runtime_migration.py` builds the real old distribution from
pinned commit `458104a52bafe619a259ed2b83ecd7a3b29c82c1`, rehearses fresh install,
bare-Python recovery, selective install/update, old wheel/editable ownership,
source-cache cleanup and rollback in disposable environments. CI runs it on
Linux/macOS/Windows and Python 3.11/3.14, alongside external-import and installed
wrapper tests. No runtime directory is vendored in this consumer.
