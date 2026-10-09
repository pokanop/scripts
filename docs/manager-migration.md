# Isolated tools and legacy migration

The `scripts` host consumes ScriptKit 1.5.0's typed contracts, bounded archive
policy and transactional installer. Discovery reads `pokanop_manager/catalog.json`
without importing any tool. Installing the harness alone installs no media stack.

## Commands

```sh
scripts install                         # harness only, preserves installed set
scripts install pluck netsy --no-pull    # selected tools only
scripts migrate --dry-run                # explain migration of the v1 marker's set
scripts migrate pluck                    # explicit subset; other v1 tools keep working
scripts migrate                          # stage all registered tools, then commit
scripts update pluck                     # fresh source/dependencies for one tool
scripts rollback                         # restore previous migration routing
scripts uninstall pluck --keep-path      # deactivate one tool, keep other tools/state
```

Use `--dir` and `--bin-dir` to select the same private install/bin roots throughout.
`install --dry-run` and `update --dry-run` do not pull Git, resolve packages, create
venvs, change wrappers, or write state. The plan lists requested requirements,
paths, preserved environments/tools and activation/failure semantics. Dependencies
are unresolved at this read-only step; it does not pretend to know the final
transitive versions without performing resolution.

## Resolve, freeze, stage, commit

1. Under the collection's kernel-held lock, check selected wrapper ownership and
   snapshot the old marker. Existing edited/foreign wrappers fail before downloads.
2. For each selected tool, snapshot its Python source into a deterministic legacy
   bundle. Pip (`--isolated`, explicit `https://pypi.org/simple`) resolves/builds
   **only its requirements** and the exact hash-pinned framework wheel. This is
   trusted executable package preparation, including sdist build hooks when needed;
   neither a venv nor a wheel is a sandbox. Do not register untrusted projects.
3. Freeze the complete wheel set into local content-addressed files. The canonical
   framework `CatalogRelease` includes exact versions, SHA-256 and byte lengths;
   `requirements.lock` is the human-readable hashed pip equivalent. This is a
   snapshot of the actual selected host/interpreter resolution, not a purported
   universal cross-platform lock. Updates create new snapshots, never rewrite old
   ones. Keep the transaction's catalog and digest-addressed files for audit/replay.
4. ScriptKit's installer revalidates strict contracts, copies artifacts in chunks,
   checks hashes/CRC/archives/lock identity, creates an isolated venv with offline
   `--no-deps` wheel installation, checks dependencies and smokes the entrypoint.
   Each tool is activated only in a **private staging bin**, invisible to users.
5. Only after **every selected tool passes** are public compatibility dispatchers
   installed and `.scripts-install.json` atomically replaced with version 2 routing.
   That single marker is the batch commit. Unselected tools retain their previous
   interpreter/source, including v1 tools that still use the shared venv.

Pip is the dependency resolver, and the external manager owns environments and
receipts. The collection does not implement a second package resolver or vendor
ScriptKit. The small local `Snapshot` adapter authorizes exactly its pinned catalog
and exposes the framework's streaming installation-source interface.

### Torch policy and index choice

Linux uses **PyPI's CUDA Torch wheels**, not the separate CPU wheel index. This
preserves the original requirements' index behavior; each actual version/hash is
recorded in the lock. No fallback between CPU/CUDA indexes occurs. Only Voxtract's
environment receives that dependency tree. Plan for substantial disk use: source
wheel snapshots, the manager's verified copies, installed payloads and failed/old
generations are retained. Model weights downloaded by the tool are separate user
state, not Python dependency locks.

The explicit per-artifact policy is 2 GiB compressed, 8 GiB expanded, 100,000
entries, a 3,600-second backend timeout, and the framework's bounded
`permissive-wheel` member grammar (needed by setuptools). Framework hard ceilings,
CRC/path/mode/collision/metadata checks remain enforced. The compatibility expansion
ratio ceiling is unchanged. Artifacts stay disk-backed; registry HTTP limits are
not bypassed because this adapter consumes locally prepared, pinned artifacts.

## Failure, interruption and rollback

Before the marker commit, the old routing remains selected even if a tool fails
halfway through staging. Ordinary failures restore original wrapper bytes. A hard
process exit during wrapper replacement can leave a compatibility dispatcher in
place; it reads the **old marker** and still invokes the old tool. Kernel locks
release on process death. Retry with a fresh transaction; failed stages are retained.

A failure/interrupt immediately after the atomic marker replacement may mean the
batch committed. The adapter reads back the marker and never restores legacy
wrappers over a committed batch. Inspect the marker/list and use `scripts rollback`
if the committed migration should be undone. There is no directory power-loss or
network-filesystem durability guarantee beyond the framework's process-interruption
contract. Windows locked files fail closed; no delete-then-rename fallback.

Rollback checks the previous marker's recorded digest and verifies retained managed
generation inventories before restoring routing. It does not redownload dependencies.
Legacy venvs and user configuration are never deleted. A v1 snapshot relies on the
preserved legacy environment, which was never managed as an immutable generation.

For v2 installs, per-tool uninstall removes only owned selected tool wrappers/routing
and retains the harness, snapshots, generation environments and configuration.
It invalidates the prior install's rollback pointer rather than restoring a snapshot
whose wrappers have since been removed. Reinstall a removed tool to activate it again.
Full `scripts uninstall -y` additionally removes the host wrapper, marker, PATH block
(unless `--keep-path`), legacy venv, managed generations and harness. The default
non-clone install directory is also removed unless `--keep-dir`; custom directories
and Git clones retain their sources. User configuration is never removed. If a
running interpreter or permissions prevent deletion, retained paths and explicit
shell cleanup commands are printed. No automatic pruning between installs is provided. Private state directories/ACLs and the base Python must remain stable.
Windows `.cmd` launchers are interactive shims, not safe transports for untrusted
shell metacharacters; programmatic callers should invoke the recorded interpreter
and runner as an argument list with `shell=False`.

## Generated repository-layout tools

Follow [AGENTS.md](../AGENTS.md): generate an offline repository-layout project,
register its directory with `scripts register PATH`, then explicitly install it.
The local overlay `.scripts-catalog.json` cannot replace built-in names. The bundle
contains generated `src/**/*.py`, not unrelated project files. Requirements resolve
against the collection's exact framework constraint, even before PyPI publication.
After uninstall, `scripts unregister NAME` removes only that catalog entry; the
project directory and other tool installs are untouched.

## Verification and limits

`tests/test_manager_migration.py` exercises real tiny-tool environments and wrappers,
partial batches, failures/interrupts, foreign wrappers, lock tampering and rollback.
The cross-platform CI additionally generates/registers/installs/doctors/removes a
real disposable repo-layout tool and runs the legacy-runtime repair rehearsal.
`tests/rehearse_manager.py` is the opt-in real six-tool dependency rehearsal; it
checks six separate environments, help entrypoints and preservation of old state.

The six-tool rehearsal is Linux evidence, not a claim that ffmpeg/nmap/credential
providers/model inference were exercised. Existing Voxtract code requires POSIX
`fcntl` and is not supported on Windows. Other existing tool prerequisites still
appear in `scripts doctor`; the manager never installs system packages.
