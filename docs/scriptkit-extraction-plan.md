# ScriptKit extraction: architecture and delivery plan

## Recommendation and scope

**Extract the existing Python library, then build a small tool-authoring and
installation platform around it.** This is feasible without rewriting the six
tools. The reusable UI/runtime already exists; the registry, packaging,
transactional installer and generators do not yet exist as reusable products.

Proposed repository: `pokanop/scriptkit`, MIT, Python 3.11+. Preserve the Python
import `scriptkit` and its existing API. Use `pokanop-scriptkit` as the proposed
PyPI distribution name and `scriptkit` as the proposed executable. **Names are
provisional:** check PyPI, executable collisions, and the existing public “Script
Kit” ecosystem before launch; do not imply affiliation. Package and repository
availability have not been verified. No new repository or release is created by
this investigation.

Deliver one repository and one distribution initially, with dependency extras
and internal boundaries rather than several independently released packages.
Keep the Pokanop tools, their domain logic, and their catalog in `scripts`.
This document specifies proposed behavior, not features already shipped.

## Evidence from the current repository

Inspected revision: `458104a52bafe619a259ed2b83ecd7a3b29c82c1`.

| Surface | Current implementation | Extraction treatment |
| --- | --- | --- |
| Public API | `scriptkit/__init__.py`, version 1.3.0; 13 modules, about 1,660 lines | Copy with tests and copyright; retain exports and signatures |
| Identity and CLI | `app.py`, `cli.py`: argparse, banners, dispatch, default commands, expected errors, interrupt cleanup | Keep; no replacement CLI framework needed |
| Visual language | `style.py`, `console.py`, `tables.py`: semantic colors/icons, shared Rich consoles, plain fallback, tables, prompts | Keep default look; add explicit output policy later |
| Progress | `progress.py`: status, iterable/byte progress, ordered parallel map, inline bars | Keep APIs; provide controlled custom Rich progress extension |
| Foundation | `config.py`, `proc.py`, `text.py`, `blocks.py`, `doctor.py` | Keep config precedence, process results, formatting, managed blocks and diagnostics |
| Tool catalog | `scripts:49–94`: `TOOL_NAMES` and `TOOLS`, six tools and system-dependency hints | Move catalog data to a validated manifest; keep branding/content here |
| Installation | `scripts:183–304,496–580`: marker, one shared venv, pip requirements, wrappers, install/update | Extract primitives, not hard-coded paths/catalog or unsafe assumptions |
| Bootstrap | `install.sh`, `install.ps1`: clone repository, invoke Python installer | Replace framework bootstrap with pinned package installation; retain compatibility launchers here |
| Scaffolding | `templates/tool_template.py`, `tests/test_template.py`, `AGENTS.md` | Turn copy/rename recipe into deterministic templates, schemas and conformance rules |
| Packaging | `pyproject.toml` declares `pokanop-scripts` 1.0.0 but packages only `scriptkit`, no CLI entry points | Separate framework ownership explicitly; current wheel is not a packaged tool collection |

All six tools import `scriptkit`. Import resolution currently relies on the
adjacent source directory, not an installed dependency; the template searches
ancestors. The `scripts` host catches a missing/broken library to remain usable
under bare Python. These details make deletion of the local package a migration,
not just a requirements edit.

Important limits to preserve or address deliberately:

- The library uses optional Rich, but the current distribution requires Rich
  and requests. The core modules do not need requests.
- Banners/errors go to stderr; success/info/warnings and current progress use
  stdout. “Clean stdout” is not a universal guarantee today.
- Rich consoles are shared module globals. Progress is tied to color policy;
  monochrome interactive progress and JSON output need a new explicit policy.
- Color environment handling uses truthy values in `style.py`, despite its
  docstring describing presence semantics. Characterize empty variables before
  changing this; do not silently change behavior during extraction.
- Custom Rich progress still exists in `medcat`, `keyferry`, and `aikit`.
  Extracting the library alone does not standardize every screen.
- Config saves write then chmod; invalid config loads fall back silently.
  This is not a credential vault or atomic durable state storage.
- The installer mutates a shared venv and writes wrappers/markers directly;
  it is not an isolated, rollback-capable package manager. Shell and PowerShell
  bootstrap behavior are not identical.
- CI currently tests Ubuntu/Python 3.11, not the promised cross-platform matrix.

## Target architecture

```text
bootstrap (sh / PowerShell; no ScriptKit import required)
    -> dedicated manager venv -> scriptkit CLI
                                 |-- catalog + resolver
                                 |-- install planner + platform adapters
                                 |-- deterministic generator + validator
                                 `-- optional AI proposal adapter
all components -> scriptkit runtime/UI -> stdlib (+ optional Rich)
installed tool -> its own venv -> compatible scriptkit runtime
scripts repository -> external scriptkit dependency + Pokanop catalog adapter
```

Suggested source layout:

```text
src/scriptkit/                 # existing modules, unchanged imports
  manager/                     # registry, planning, state, install, wrappers
  generate/                    # spec, templates, renderer, validation
  ai/                          # provider protocol, opt-in proposal validation
  __main__.py                  # python -m scriptkit; entry point main()
templates/                     # packaged versioned resources
schemas/                       # tool spec, catalog, lock, AI proposal
examples/                      # small standalone and collection examples
tests/                         # runtime + installer + generated-project tests
docs/                          # reference, author guide, migration, security
install.sh, install.ps1
```

Packaging: core has no mandatory third-party dependencies; `[rich]` installs the
initially tested Rich range, `[cli]` adds Rich and any strictly needed manager
libraries, `[ai]` adds provider dependencies. Avoid importing manager/AI modules
from `scriptkit.__init__`; `import scriptkit` must work offline without extras.
Use stdlib argparse, tomllib and venv; use pip for dependency resolution rather
than inventing a resolver. Bootstrap installs `[cli]`; a minimal runtime user
can install core alone. Publish wheels and sdists, including template resources.

### Runtime and UX contract

1. Freeze current 1.3.0 behavior with contract tests before moving it. Align the
   new distribution and runtime version at the first extracted release (proposed
   1.3.1); packaging changes must not pretend a new API is required.
2. Keep semantic success/error/warning, icon vocabulary, banners, doctor sections,
   tables, progress counters/ETA and plain fallbacks as the default house style.
3. Add an opt-in `OutputPolicy`/context for streams, color (`auto/always/never`),
   progress (`auto/always/never`), Unicode/ASCII, quiet and machine mode. Existing
   helpers keep legacy defaults; new generated tools use the explicit context.
4. Machine mode emits a documented versioned JSON result on stdout; diagnostic
   messages/progress go to stderr, animation off when redirected. Never infer
   a data schema by scraping tables. Table data and rendering stay separate.
5. Preserve CLI success 0, expected error 1, argparse usage 2 and Ctrl-C 130.
   Specify broken pipes, cancellation and cleanup in tests before adding APIs.
6. Expose theme tokens and a sanctioned shared-console/progress factory instead
   of arbitrary tool-owned console creation. Do not force custom workflows into
   a new all-encompassing application class.
7. Add opt-in strict config validation and atomic writes separately. Existing
   config paths and coercion remain compatible; secret storage uses OS keyring
   or environment, not ordinary config files.

## Bootstrap and tool lifecycle

Proposed experience (illustrative commands/URLs, not live installation instructions):

```sh
curl -fsSL https://raw.githubusercontent.com/pokanop/scriptkit/vX.Y.Z/install.sh | bash
scriptkit registry add pokanop https://example.org/pokanop/catalog.json
scriptkit list --registry pokanop
scriptkit install pokanop/pluck --version 1.2.3
scriptkit doctor
scriptkit update pokanop/pluck --dry-run
scriptkit rollback pokanop/pluck
scriptkit uninstall pokanop/pluck
```

Also support a downloaded, inspected installer and `pipx install
'pokanop-scriptkit[cli]==X.Y.Z'`. Windows gets a downloadable PowerShell installer
with matching options. Initial requirement: user-provided Python 3.11+ with venv;
fail with OS-specific guidance if absent. Do not silently install Python or run
sudo. Standalone binaries/managed Python can follow demonstrated demand.

Bootstrap responsibilities: resolve platform paths, validate Python, create a
manager-only venv, install an exact framework release with a verified release
lock, create the manager wrapper, show PATH guidance. PATH editing is explicit,
reversible and suppressible with `--no-path`; never overwrite foreign wrappers.
Document that curl-to-shell trusts both the fetched script and its origin;
checksums fetched from the same untrusted origin alone do not establish trust.
Publish immutable release artifacts, SHA-256 manifests, provenance and a
verification procedure anchored to trusted release identity. Stable/latest is a
discovery channel that resolves to a recorded immutable version, not mutable
code reused during an install transaction.

### Catalog and installed-state contracts

Catalog schema v1 is data, never executable Python. A namespaced tool identity
maps to immutable versions. Example shape (abbreviated, placeholders):

```json
{
  "schema_version": 1,
  "namespace": "pokanop",
  "tools": {
    "pluck": {
      "description": "Read and edit structured data",
      "releases": {
        "1.2.3": {
          "requires_python": ">=3.11",
          "requires_scriptkit": ">=1.3.1,<2",
          "source": {"kind": "wheel", "url": "https://example.org/pluck.whl", "sha256": "<digest>"},
          "commands": ["pluck"],
          "dependency_lock": {"url": "https://example.org/lock.txt", "sha256": "<digest>"},
          "platforms": ["linux", "macos", "windows"],
          "system_dependencies": []
        }
      }
    }
  }
}
```

The real schema validates versions, Python/platform selectors, HTTPS origins,
hashes, dependency lock format and safe command names. Platform-specific locks
must cover all transitive wheels/hashes; an artifact hash alone is insufficient.
A separate legacy `script-bundle` source adapter supports this repository's
extension-less files plus pinned requirements and an immutable archive/commit.
A development-only local source adapter requires explicit opt-in. Do not allow
arbitrary install shell hooks in catalog v1. Required system dependencies fail
with guidance; optional dependencies warn, using the existing doctor model.

Registry addition displays origin/namespace and requires trust confirmation;
noninteractive mode requires an explicit trust option. Namespace-qualified
resolution avoids dependency confusion; multiple registries never silently
replace each other's tools. Registry metadata has bounded size, strict schema,
cache/expiry and recorded digest. Refresh failure does not silently upgrade from
unknown data. Offline install requires a complete verified cached lock/artifact
set and an explicit offline mode.

Store manager config/cache/data under platform-standard directories (XDG on
Unix, LocalAppData on Windows) with CLI/env overrides. Receipts record schema,
registry origin/digest, tool and framework versions, hashes, venv path, owned
wrappers and previous generation. Tool user data/config is separate and is not
removed by default.

Installation is **plan -> validate -> fetch -> stage -> smoke -> activate**:

- Resolve a pinned version and dependency lock; show filesystem/network effects
  via `--dry-run`. Use one environment per installed tool, not one per catalog.
- Lock manager state; reject path traversal, archive symlinks escaping staging,
  malicious command names and destinations outside owned roots.
- Verify artifacts before extraction/install; prefer wheels, with source builds
  an explicit trust choice. Installing or invoking third-party Python is code
  execution, not a sandbox. A venv provides dependency isolation only.
- Build a new versioned venv; run help/version and declared safe smoke checks
  only after trust approval. Leave the old environment untouched on failure.
- Activate via stable owned launchers and an atomically replaced generation
  pointer/receipt; journal multi-file changes and recover interrupted activation.
  Test Windows locked-file behavior; do not assume POSIX rename semantics.
- Rollback selects a prior verified generation. Uninstall removes only recorded,
  still-owned launchers/environments. Preserve user files, foreign wrappers and
  shell edits outside managed regions. Serialize concurrent installs/updates.
- Self-update uses a staged manager generation and an external bootstrap/launcher
  switch, not pip mutating the interpreter currently running the transaction.

## Deterministic generators

Proposed commands: `scriptkit new tool NAME`, `scriptkit add command NAME`,
`scriptkit new collection NAME`, `scriptkit generate installer`,
`scriptkit generate --spec tool.toml --check`, and `scriptkit validate`.

`tool.toml` is the authoritative schema-versioned specification: identity,
package/module/command names, description, version, Python/framework ranges,
commands/typed arguments, safe default action, dependency declarations, config
schema, doctor checks and template version. Prompt mode writes this spec;
noninteractive mode requires it. All ambiguity becomes an explicit field or a
working example/TODO; neither mode guesses destructive behavior.

Pipeline: validate spec -> normalize names -> render a pinned template -> format
with pinned tooling -> validate paths/syntax/contracts -> preview diff -> apply.
Fixed spec, template and formatter versions must produce byte-identical files
(no timestamps, random IDs, host paths or unordered output). This guarantees
source generation, not reproducibility of unpinned external package installs.

Generate a standalone package by default:

- `pyproject.toml` with framework constraint and console entry point;
- `src/<module>/cli.py` using make_parser/parse_args/dispatch/run_cli;
- `src/<module>/commands/<command>.py` with user-owned handlers;
- config/doctor setup, `--help`, `--version`, README, tests and CI;
- `tool.toml`, catalog-entry output, install instructions and framework rules.

An explicit `--layout scripts` adapter emits an extension-less launcher,
`requirements/<tool>.txt`, docs, tests and a catalog change for this repo.
Generated collection installers are thin, pinned framework bootstrap adapters,
not copies of an 895-line lifecycle host. Publishing a catalog is a reviewed,
separate operation; generation does not register tools on a remote service.

Separate generator-owned wiring from user-owned command modules. Handlers receive
parsed arguments plus an optional context (output, config, cancellation); return
an int/None or raise `CliError`. Ship a runnable hello example, and fail clearly
for intentionally unimplemented commands instead of reporting false success.
Declarative command specs drive wiring without executing user modules during
rendering. Re-running leaves user files alone. Record hashes of generated files;
refuse to overwrite locally modified generated files, emit a diff/conflict, and
require explicit resolution. `--check` is read-only and exits nonzero for drift.
Reject path escapes and identifier collisions before writing anything; stage
writes and refuse nonempty destinations unless an explicit merge plan is accepted.

Version templates independently; upgrades are reviewed migrations, never silent
re-rendering with whatever template happens to be newest. Snapshot tests cover
both layouts, repeated generation, conflicts and upgrading old specs.

## Optional AI: proposals, not ownership of the framework

AI is an opt-in authoring assistant. The renderer, installer and generated tool
must work with no key, provider SDK or network. AI may suggest descriptions,
argument schemas, examples, tests and implementations inside user-owned command
modules. It does not become a required runtime dependency of those tools.

Proposed flow:

```text
scriptkit ai propose --spec tool.toml --provider <name> --model <id>
  -> explicit context preview -> provider request -> schema-valid proposal/diff
  -> local static validation -> human review
scriptkit ai apply <proposal>     # approved spec delta + allowlisted file patches
scriptkit generate --spec tool.toml
```

Use a narrow provider protocol accepting a typed request and returning structured
proposal data; implement one provider first, add a second to prove the boundary,
and permit an explicitly configured local endpoint. No autonomous shell or file
tools. BYOK via provider-specific environment variables or optional OS keyring;
never CLI key arguments, committed files, telemetry or prompts. Redact logs;
do not persist full prompts/responses unless requested. Config stores key
references only. Display destination, model, included files and a request/token
budget before sending; bounded timeout/retries, cancellation and no silent paid
provider fallback. Local endpoints receive no unrelated cloud credentials.

Ship versioned guidance alongside templates: `AGENTS.md`, framework API excerpts,
command-writing skill, output/config/error rules, dependency policy and a
conformance checklist. AI receives only the chosen spec and explicitly selected
files, not the whole repository, home directory or `.env`. Treat file contents,
registry descriptions and model output as untrusted data, not instructions that
can override these boundaries.

Validate returned JSON schema, allowed paths, patch base hashes, size limits,
syntax, declared imports and command contracts. Model proposals cannot modify
bootstrap, trust settings, CI secrets, dependency locks or framework internals.
Dependency suggestions require explicit human review and deterministic lock
regeneration. Static validation is not a security proof: generated Python may
still be malicious. Do not run proposed code/tests automatically on the host;
after review, use an isolated disposable runner with no credentials and network
off by default. Never auto-install, publish, commit or run proposed commands.

Save the approved spec/patch and template version so future rendering is
repeatable; model inference itself is not deterministic, even with temperature
zero. Invalid responses, provider failure or missing keys leave files unchanged
and offer manual editing. Test the adapter using recorded synthetic fixtures,
never live keys in routine CI.

## Bringing the framework back into `scripts`

Migration must explicitly solve source shadowing and the bootstrap dependency
cycle. Keep the existing CLI, wrappers, config paths and markers until separately
migrated; users should not need to rename `scripts install pluck`.

1. **Extract unchanged runtime first.** Copy modules and their unit tests, preserve
   MIT attribution, publish a verified wheel. Run the current tools against that
   wheel in a temporary checkout with local `scriptkit/` removed and outside-CWD
   subprocess tests. Do not use a sys.path trick that hides unresolved imports.
2. **Consume the external runtime.** In one migration PR, remove local
   `scriptkit/`, stop packaging it in `pyproject.toml`, add
   `pokanop-scriptkit[rich]>=1.3.1,<2`, and pin an exact tested version in bootstrap
   locks/constraints. Wire constraints into every requirements installation
   path, including harness-only and per-tool installs. Keep tool-specific deps
   here; requests remains a tool/host dependency where actually needed.
3. **Maintain bootstrap recovery.** A bare-Python `scripts` invocation must still
   reach its minimal install/doctor fallback. Bootstrap installs the external
   dependency into the target venv before normal tool execution; no runtime import
   is required to create/repair that venv. Missing dependency errors tell direct
   source users how to install it. Remove ancestor-search scaffolding and update
   `AGENTS.md`, template, README and `docs/scriptkit.md` together.
4. **Adopt manifests, then lifecycle services.** First replace duplicate catalog
   constants with validated data while preserving behavior. Subsequently make
   `scripts` a branded adapter over the manager using the legacy bundle source.
   Translate v1 markers explicitly; show a dry-run migration and retain the old
   shared venv/wrappers until all staged tool environments pass checks. Do not
   automatically reorganize existing installs in the runtime-extraction release.
5. **Dogfood generators.** Generate a disposable tool in this repository and a
   standalone package, verify both, then remove the disposable tool. Adopt the
   repo-layout generator as the documented authoring route.
6. **Operate as a consumer.** Pin deployed releases; use bounded compatibility
   ranges in package metadata. CI tests the pinned release and a candidate
   framework wheel. Automated dependency PRs run all characterizations before
   changing locks. No tracking main, vendored fork or permanent dual import path.

Rollback: before deleting the local package, tag the last bundled release and
record current receipts. If the external migration fails, restore that scripts
release and its locked dependencies; retain install/config backups. After manager
migration, switch receipts/launchers to the old generations rather than trying
to reverse arbitrary pip changes. Do not uninstall an old `pokanop-scripts`
distribution after installing the new framework in the same venv: both may claim
`scriptkit/` files. Prefer fresh venvs to eliminate overlapping package ownership.

## Delivery sequence and acceptance gates

Indicative engineering effort, not a committed schedule; Windows and packaging
spikes may change estimates. These are planning stages, not newly filed tickets.

| Stage | Scope / dependency | Exit gate | Estimate |
| --- | --- | --- | --- |
| 0 | Naming, API inventory, packaging and bootstrap spike | Wheel works outside source tree; namespace and supported OS decisions recorded | 1–2 days |
| 1 | Unchanged runtime extraction + public repository hygiene | Runtime contracts pass with/without Rich; MIT attribution, README, CONTRIBUTING, SECURITY, release CI present | 2–4 days |
| 2 | External dependency consumption in scripts; depends on 1 | Full suite plus fresh/upgrade/repair install tests pass without local package; rollback exercised | 2–4 days |
| 3 | Catalog, manager, pinned bootstrap, trust and transactions | Fresh install/update/failure/rollback/uninstall demonstrated on Linux, macOS, Windows; foreign files untouched | 5–8 days |
| 4 | Deterministic tool/collection/installer generators; depends on 1 and manager contracts | Offline byte-identical generation, conflict safety, installed-wheel template resources and standalone smoke tests | 3–5 days |
| 5 | Optional AI proposal/apply; depends on 4 | No-key parity, provider fixture tests, secret/path boundary tests, reviewed patch flow | 3–5 days |
| 6 | Branded scripts adapter + general availability; depends on 2–5 | Existing install migration/rollback rehearsal; documented support and compatibility matrix | 2–4 days |

Release the useful runtime and deterministic authoring slice before waiting for
AI. Do not label the full platform stable until transactional installs and
cross-platform gates pass. Additive features use minor releases; changed defaults,
output streams or removed API require explicit compatibility/migration policy.

Verification matrix:

- Existing runtime unit and tool characterization tests; import without Rich;
  help/version/doctor, errors, interrupts, fallback rendering, config precedence.
- Rich/plain, TTY/pipe, NO_COLOR/FORCE_COLOR including empty values, ASCII,
  narrow terminals and stdout/stderr separation. New machine-output snapshots.
- Python 3.11 through the latest supported stable Python; Linux/macOS/Windows.
  Include shell and PowerShell quoting, spaces/non-ASCII paths and PATH cleanup.
- Built wheel/sdist in clean venvs outside checkout; no hidden source imports,
  template resources present, declared dependencies sufficient, no-key offline use.
- Local test catalogs/wheels: invalid schema/hash, unsupported platform, download
  interruption, full disk/permissions, concurrent update, stale lock, unknown
  wrapper ownership, malicious archive, failed smoke and interrupted activation.
- Generator golden files, rerun idempotence, hand edits, spec/template upgrade,
  no-network generation, generated help/doctor and handler tests.
- AI fake-provider timeout/malformed response, secret redaction, prompt injection,
  path escape, stale patch and dependency proposal requiring review.

For this investigation, `python3 -m pytest` on the inspected checkout completed
with **602 passed, 1 skipped**. This is a Linux baseline, not evidence that the
proposed manager, generators or cross-platform migration already work.

## Priorities, risks and deferred scope

Highest-value additions beyond extraction: deterministic project/command
scaffolding, install plans and rollback, structured output, consistent doctor,
atomic config/state, conformance validation, and verified offline installs.
AI-assisted descriptions/handlers come after those foundations.

Principal risks are package-name confusion, source-directory shadowing, overlapping
wheel ownership, legacy shared-venv dependency conflicts, third-party install
trust, Windows activation differences, and accidental output changes. The gates
above address each; preserve the legacy path until replacement evidence exists.

Defer hosted marketplace/accounts, remote arbitrary plugins, automatic system
package installation, autonomous AI execution, a new DSL, compiled standalone
binaries, and full agent runtime/provider-gateway extraction from `aikit`. They
increase attack surface and maintenance without being necessary for this goal.

Owner decisions before publication: final public name, repository/PyPI ownership,
supported platform matrix, release-signing identity and who curates the first
trusted catalog. Recommended defaults are MIT, Python 3.11+, three desktop OSes,
a Pokanop-maintained catalog, and opt-in third-party registries. Missing namespace
or publishing access blocks publication, not the architecture or local prototype.
