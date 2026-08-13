# LIB-L0 Extraction Inventory

This document is a non-authoritative review view for deciding whether an
internal mechanism is ready to move toward a reusable SpiralLens contract. It
does not change the canonical library milestone, promote a Python API, grant
experiment authority, or alter a scientific claim. The Roadmap and API Status
remain authoritative for those boundaries.

## Audited coordinate and claim boundary

- baseline commit: `a7e24f912ffeaa15a6b79bf200c39dccf9cd5746`;
- baseline Git tree: `d553fd83c37c5cb1490dd09e777f734e1192e580`;
- current physical-placement manifest:
  `distribution/spirallens_python_members_v0_1.json`, schema
  `spirallens.python-distribution-members.v0.1`;
- current ordered-export declaration manifest:
  `distribution/spirallens_ordered_exports_v0_1.json`, schema
  `spirallens.ordered-package-exports.v0.1`;
- current installed-import outcome manifest:
  `distribution/spirallens_installed_imports_v0_1.json`, schema
  `spirallens.installed-import-conformance.v0.1`, 8,214 bytes, SHA-256
  `d9a90a30514a64d561e3caaa5ab6309b5c205efa12a91bb93ec07cebe83c6795`;
- current `src/**/*.py` partition: 181 modules = 159 wheel-present modules
  (24 package initializers + 2 console-entrypoint runtime + 133 shipped
  runtime) + 22 repository-only modules;
- `LIB-L0`: `in progress`;
- public root surface: only `spirallens.__version__` is supported;
- closed static ordered `__all__` declaration inventory: 559 namespace-scoped
  entries across 24 package initializers;
- closed installed-module outcome inventory: 159 modules = 154 base-import
  successes + 5 exact blocked-Torch model-extra outcomes; scoped runtime
  `__all__` observation: 23 initializers and 554 entries succeeded, while one
  initializer and five entries were unavailable;
- scientific and VOY deltas: none;
- D7 verified-B interpretation: `insufficient`, Level 0, claim delta `none`,
  and VOY-V3 purpose evidence only; VOY-V4 dispatch remains unauthorized.

Artifact records, documentation projections, tests, CLI wrappers, and members
of one experiment chronology do not count as independent library consumers.
A physically installed module is not thereby a public or stable API.

## Distribution-boundary observation

At the inventory baseline, a wheel built from a clean `git archive` with
`uv 0.11.6` and `setuptools 81.0.0` contained 184 members, including all 22
repository-experiment modules; the same 22 were present in the sdist. That
wheel was 1,103,723 bytes with environment-specific SHA-256
`39603d812080c65ab7d723ad7625ec6d7f5872e04f4a7532c00798649f72462b`.
The distinct three v0.1 `post_d6_code` files, four audited D7 operational
scripts, frozen v1 protocol, and ten tracked v1 artifacts were absent from both
artifacts. This historical observation established the separation defect; it
is not a frozen release identity or a claim that repository files are
generally excluded.

The bounded source inventory is unchanged:

| Group | Source members | Physical LOC | Public/export status | Current distribution status |
| --- | ---: | ---: | --- | --- |
| `spirallens/qualification/confirmation_v1_*.py` | 20 | 17,312 | internal; no `confirmation_v1` export | absent from sdist and wheels |
| `spirallens/access/_pythia160_*.py` | 2 | 1,878 | private; no access/root export | absent from sdist and wheels |

All 22 ordinary source files and their 19,190 physical lines remain at their
reviewed repository paths. A source-origin probe imports all 22 from those
exact paths without loading `torch`, `transformers`, `huggingface_hub`, or
`safetensors`. No source or historical S → A → B byte is moved or rewritten.

`MANIFEST.in` excludes the two reviewed prefixes from the sdist, while the
custom `LibraryBuildPy` command filters the exact 22-module set from wheels.
The build fails closed if the full source tree contains a partial set, a new
prefix-matching file, or a non-regular reviewed path. Only a sdist-shaped
source tree with an ordinary root `PKG-INFO` and no `.git` marker may contain
the empty source set; this marker combination is not an independent provenance
proof. Matching stale `build/lib` outputs, including nested PEP-3147 bytecode,
are rejected before wheel
publication and are not deleted by the build.

The successor v0.8 diagnostic retains the versioned physical manifest and
closed wheel Python-module inventory. They fail closed over every
`src/**/*.py` path and require the exact 159-member shipped set in the sdist,
direct-source wheel, sdist-derived wheel, and both fresh non-editable
installations. The 159-member ordered-path SHA-256 is
`8769ac8ffc92e5123a8bf802eb09cab24a5a3e28882ac38cf84f3deee25c31aa`;
the source inventory is the exact 159 + 22 partition. The sdist also carries a
byte-identical copy of the classification manifest. Unclassified additions,
removals, renames, rogue top-level packages, unclassified package files, and
stale build/install bytecode fail before a wheel is accepted. A role change is
not inferred by the gate: it requires an explicit reviewed manifest delta and
refreshed validation evidence.

The four physical-manifest roles describe placement only; the
`package_initializer` role does not classify an export declaration. The
separate ordered-export manifest records the exact literal ordered `__all__`
declaration for all 24 classified initializers, totaling 559
namespace-scoped entries. The source tree, sdist, direct-source wheel,
sdist-derived wheel, and both fresh installations have the same initializer
byte digest
`fcfef3724bb9902675052d88301c70422907eba60197c203925281fa45efd145`
and ordered-export digest
`e2c947c30f0323c54c1713274dac0117fd74dc86cd576279c44a040dfc0ae798`.
The sdist carries a byte-identical copy of the manifest, whose SHA-256 is
`cb9d58ba50c3ead9551da17a7b3d31180157c0b0f7b005aff2df4c5f05effe3e`.
Fresh-install inspection parses distribution-owned initializer bytes without
importing a `spirallens` module.

The installed-import manifest adds a distinct dynamic observation without
changing those physical or static roles. For both the direct-source and
sdist-derived wheels, the v0.8 diagnostic imports each of the exact 159 modules
in its own fresh `-I -S -B`, 30-second process from a neutral working
directory and without `PYTHONPATH`. Site initialization is disabled and `.pth`
startup is not executed. This is a single-current-host observation, not a
host, Python, or dependency-version portability matrix. The validator explicitly
adds only the fresh-wheel root and the exact roots of the declared host NumPy
2.4.4, PyYAML 6.0.3, and SciPy 1.17.1 distributions. Because those roots share
host directories, this is not a freshly installed or isolated base-dependency
environment. Its repository parent uses `packaging` supplied by the
already-declared dev `build` toolchain; no isolated child imports `packaging`.
The base runtime dependencies are unchanged, and the installed metadata must
contain the exact 13 normalized `Requires-Dist` records: three base and ten
optional-extra requirements. The six
`cryptography`, `faiss`, `huggingface_hub`, `safetensors`, `torch`, and
`transformers` prefixes are blocked. A separate generic blocker rejects
distribution-backed imports outside the three declared bases; the exact
observed blocked attempt is `charset_normalizer`, and it is not loaded. Each
route observes 154 base-import successes, five exact blocked-Torch model-extra
outcomes, no loaded optional prefix, and the exact three declared bases as its
aggregate loaded third-party distributions. Of the 24 initializers, 23
reproduce their exact runtime list-valued `__all__`, totaling 554 entries; the
five `spirallens.adapters` entries are unavailable with that initializer at the
blocked Torch boundary. Their normalized startup receipts are equal. Both
routes have outcome-manifest SHA-256
`8f885faab04cd796285d6263381172a4697fc310dafd96c504de44b4214187c7`.
The adopted pre-projection live validation receipt has SHA-256
`2ce75371e7a8f39db66c136cf64c039f6f76fcbdf84b6f6b76b6bdf5f0b502b4`.
The separately retained preA/preB/post invariants bind that receipt to
validator SHA-256
`a08ddf98f8d7da985f0ed5029b999c0ab40d6b37a250e450a8df51a38a89575c`,
setup SHA-256
`da83e2ad642bef085948571a26bef52030abadc91f0cb5d8d3a2450160b0079f`,
manifest SHA-256
`d9a90a30514a64d561e3caaa5ab6309b5c205efa12a91bb93ec07cebe83c6795`,
and unchanged `src` inputs before this receipt-projection documentation was
added. Because the documentation
changed afterward, and `README.md` is embedded in distribution metadata, its
artifact hashes do not attest artifacts rebuilt from the later documentation
state.

The audit hook begins after isolated interpreter and standard-library probe
bootstrap and observes zero denied events within its bounded policy for file
writes, process creation, network access, and selected filesystem mutation.
It is not a complete side-effect proof: it deliberately permits
`ctypes.dlopen`, `os.putenv`, and `os.unsetenv`, and does not observe every
possible native, environment, descriptor, signal, thread, or external effect.
One-process-per-module isolation prevents prior SpiralLens imports from
contaminating the next receipt, but proves neither combined import-order nor
concurrent-import behavior. The probes import modules; they do not invoke
their operations.

These are bounded placement, declaration, and installed-import inventories,
not an API contract. Runtime `__all__` is observed only for the 23 successfully
imported initializers; the probe does not resolve the 554 named attributes or
establish symbol importability, identity, signature or behavior, star-import
behavior, alias absence, dynamic-mutation absence, operation safety, or
portability. The `models`, `ann`, `witness`, and `dev` extras
classify dependency installation, not wheel membership or export-declaration
roles. Portability is also independent: the shipped set still contains 46
qualification modules and legacy repository-inferred operations.
Consequently the full wheel is not an experiment-free or library-grade
subset. The report states
`closed_wheel_python_module_inventory_established=true` and
`closed_ordered_package_export_inventory_established=true`, plus
`closed_installed_module_import_outcome_inventory_established=true` and the
scoped `runtime_successful_package_export_values_established=true`; it keeps
`runtime_export_values_established=false`,
`all_package_runtime_export_values_established=false`,
`export_symbol_importability_established=false`,
`side_effect_free_imports_established=false`,
`closed_public_api_contract_established=false`, and
`closed_library_allowlist_established=false`, and keeps its authority,
`lib_l0`, library, portability, public-API, and scientific grants `false`.
The installation report separately records
`base_dependencies_freshly_installed=false`,
`host_projected_base_dependencies=true`, and
`isolated_base_dependency_environment_established=false`.

The sdist is a library source artifact, not the repository experiment replay
or test bundle. Its current 106 test files are not a self-contained suite for
the 159 shipped modules: experiment-facing tests still require omitted
repository-only source and other repository context. They are neither an
installed-distribution conformance surface nor replay or maturity evidence.
The v0.1 classification admits only ordinary Python modules. Shipping package
data, extension modules, namespace/generated modules, or bytecode-only modules
requires a reviewed, versioned manifest/schema successor rather than an
implicit exception to the closed inventory.

## Candidate inventory

`input equivalence` includes accepted values, bounds, and observation order.
`failure equivalence` includes exception type, stable code/message boundary,
and retained state. `Unknown` or `not established` stops extraction.

| Surface group | Current maturity | Wheel/dependencies | I/O and claim boundary | Existing production consumers | Consumer independence | Input equivalence | Failure equivalence | Current production/export delta | Disposition and blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `spirallens.core.canonical` | stable candidate | present; standard library | in-memory canonical bytes/digests; no claim or authority meaning | many modules across independent namespaces | established for the shared byte codec, not for every domain reconstruction | established for the codec | domain errors remain local | already shared; 7 `core` exports | keep; stable promotion still needs the full compatibility and release gates |
| private `RepositoryContext` | internal | present; standard library | construction performs no I/O; consumers perform repository/import-origin checks; no Git, claim, chronology, or authority proof | `build_current_qualification_engine_binding()` and `run_public_example_plumbing()`; D7 internals are one chronology family | candidate pair only; not yet an accepted two-consumer decision | each consumer retains its own policy | deliberately domain-local | foothold baseline `+109` production LOC, `+0` exports | hold private; reuse this one marker for reviewed migrations and create no parallel context family |
| private bounded held-file byte read | internal private primitive | present as a private package module; standard library only | bounded regular-file bytes through held directory/file descriptors; parsing, digest checks, read traces, and authority remain in wrappers | `access.descriptor` and `referents.loader` | established: two distinct production domains | established for the byte primitive; each wrapper retains its exact path/digest preprocessing and observation order | established at the wrapper boundary, including domain exception type/message, direct OS cause/context, policy no-cause/context, and held-descriptor close order | against extraction baseline `be274333e77d7518cb21ddb6afda3d62222e4b6c`, `_held_file.py` / `access/descriptor.py` / `referents/loader.py`: `0/517/179 → 85/457/105`, total `696 → 647` (`-49`, 25.8% of the audited 190 duplicated LOC); `+0` exports and dependencies | accepted only as a private neutral byte primitive; no public promotion or additional consumer follows without a new equivalence audit |
| Atlas manifest reader/capture boundary | provisional/model extra | present; reader closure retains NumPy/PyYAML and a fresh wheel loads none of `torch`, `transformers`, `huggingface_hub`, `safetensors`, `spirallens.adapters`, `spirallens.atlas.id_sweep`, `spirallens.atlas.engineering_run`, or `spirallens.atlas._capture_store`; capture remains a model extra | manifest/file I/O only; no capture, model, claim, or authority meaning enters the reader | `metrics.candidate_pairs` and `atlas.engineering_receipt` | established: two distinct production domains | established for reader signatures, defining modules, public symbol identities/order, accepted inputs, return behavior, and validation order | established for exception-class identity, type/message boundaries, and existing reader failures | against split baseline `a1d6c615da9e39247afa0332658e9aee7b24bb5a`, `store.py` / `_capture_store.py` / `id_sweep.py` / `__init__.py`: `1226/0/589/57 → 760/492/590/78`, total `1872 → 1920` (`+48`), while the reader store loses 466 lines; ordered 20-name `__all__`, exports, and dependencies are unchanged | accepted as a reader import-boundary split because its forbidden import set is empty, not as a total-LOC reduction; whole Atlas remains provisional/model extra, and public promotion requires its own review |
| private strict YAML mapping loader | internal private primitive | present as a private package module; existing PyYAML dependency | SafeLoader mapping syntax only; size/source-digest/UTF-8 checks, domain schemas, canonical digests, and claim meaning stay in each wrapper | contexts, instrument registry, synthetic protocol, and Atlas engineering protocol | established: four distinct production domains | established for alias, merge-key, string-key, duplicate-key, standard safe-tag, anchor-only, nonfinite-scalar, and wrapper preprocessing behavior | established for exact domain type/message/cause/context, wrapped PyYAML errors, and raw recursion failure | against extraction baseline `366d195f112bc3b95f36504e8a711029c71e6161`, the four consumers plus `_strict_yaml.py` change from `3081` to `2987` physical lines (`-94`); the audited extraction surface changes `158 → 64` (`-59.5%`), with `+0` exports and dependencies | accepted only as a private syntax-policy factory; domain parsing stays local, and the semantically different CLI, neighbor-receipt, and ordinary `safe_load` families remain excluded |
| exact array-fingerprint framing | rejected at current gate | present; NumPy | in-memory `dtype.str` + shape + NUL + C-order byte identity only; no scientific interpretation | `graphs.common`, `qualification.common`, and `synthetic.representation_estimator` | three candidate domains, but qualification is a frozen D7 trust root and the graph/synthetic pair is coupled | established only for stable ndarray metadata across 21 audited case families; unrestricted duck-typed inputs differ in metadata observation order | native ndarray failures are aligned, but callable-level failure/observation equivalence is not established for changing duck-typed metadata | no production/export delta; the three local function groups total 49 lines, while the only trust-root-free pair totals 33 lines and has no reviewed design demonstrating the required 20-line net reduction | reject extraction: changing `qualification/common.py` adds a direct reviewed-S execution-source violation; do not weaken that verifier, and do not add a sub-threshold two-consumer helper |
| immutable-array helpers | provisional local mechanisms | present; NumPy | in-memory numeric ownership and immutability; scientific interpretation stays local | graphs, qualification, referents, instrument contracts, and synthetic variants | multiple domains but policies differ | not established across rank, dtype, range, nonfinite, negative-zero, and copy behavior | not established across domain exception types and native failures | small scattered duplication | hold; do not merge distinct validation or representation policies for cosmetic deduplication |
| `PythiaAdapter` | provisional/model extra | present; optional model stack | model observation/capture; fake-surface mechanics are not real-model parity | one Pythia-family adapter | fewer than two adapter families | not applicable | not applicable | existing provisional exports unchanged | hold; a second adapter and conformance evidence are required for `LIB-L2` portability |
| D7 v1 `confirmation_v1_*` | internal experiment implementation | repository source only; absent from sdist and wheels; qualification dependency set | fixed source/history, chronology, authority, no-replace publication, and result joins | callers inside one D7 v1 chronology | not independent library consumers | intentionally experiment-specific | intentionally experiment-specific | 20 modules / 17,312 LOC retained in source; no exports | reject extraction; preserve the verified distribution separation and frozen identities |
| Pythia-160M private kernels | internal repository experiment | repository source only; absent from sdist and wheels; standard-library validation kernels | declaration/provider-metadata evidence only; no model load, subject run, or science authority | acquisition script and tests | scripts/tests are not two production consumers | experiment-specific | experiment-specific | 2 modules / 1,878 LOC retained in source; no exports | hold outside library promotion; preserve the verified distribution separation |
| audited D7/Pythia protocols, scripts, and artifacts | repository evidence/data | not package modules; the audited v1 sets were absent from the observed sdist/wheel | frozen declarations, one-shot operations, and persisted evidence | experiment tooling only | not library consumers | not applicable | not applicable | no library export | keep experiment-bound; never count the artifact chain as a consumer |

## Extraction decision gate

Extraction stops unless all of the following are demonstrated before editing
the affected implementation:

1. At least two independent production consumers exist; one may not merely
   wrap or replay the other. Tests, docs, scripts, and artifacts do not count.
2. An exact matrix shows equivalent accepted inputs, output-byte behavior,
   validation and observation order, and failure semantics.
3. Domain wrappers retain claim, authority, chronology, typestate,
   publication, and repository-history meaning. A shared primitive receives
   none of those facts.
4. Frozen canonical bytes, historical pins, artifact schemas, and
   `pass`/`fail`/`insufficient`/`not_run` distinctions remain unchanged unless
   an explicit versioned migration precedes consumption.
5. No public export, mandatory dependency, implicit repository discovery, or
   framework type leaks into a framework-neutral boundary.
6. Fresh non-editable installations verify import origin and the exact closed
   wheel Python-module inventory. This placement receipt does not classify
   library/experiment maturity, portability, or public exports.
7. The change materially removes duplicated production plumbing. A review
   should normally stop a pure deduplication that removes fewer than 20 lines
   or less than 20 percent of the duplicated block; a boundary split may
   substitute proof that its forbidden dependency/member set becomes empty.
8. If a proposed common scaffold is net-positive or fails equivalence review
   twice, retain only the rejection record rather than the scaffold.

## Next bounded decisions

1. Preserve both reviewed inventories: the 181 = 159 + 22 Python-member
   partition and the exact 24-initializer, 559-entry static ordered-export
   declarations. Keep their fail-closed parity proofs through source, sdist,
   both wheel routes, and both fresh installs. Any intended module, role,
   initializer, or literal ordered-declaration change requires an explicit
   reviewed manifest delta and refreshed validation evidence; neither
   manifest promotes the changed surface into a public API.
2. Move a repository-only module into the shipped set only after its own
   two-independent-consumer, exact-equivalence, and material-benefit review.
   Public export requires a separate `__all__`, compatibility, documentation,
   and release decision; an optional-extra change requires a separate
   dependency decision.
3. Introduce package data, extension modules, namespace/generated modules, or
   bytecode-only distribution support only through a versioned
   classification/schema successor and new artifact/install adversaries.
4. Before an installed-import schema successor adds another host-specific
   exception, dependency environment, import mode, or artifact kind,
   centralize the repeated manifest/setup/validator/embedded-worker metadata
   policy in one private reviewed boundary. Retain independent fail-closed
   parsing, validation, and adversaries; do not grow parallel policy copies.
   The current single-host diagnostic remains proportionate only as a bounded
   ratchet with no `src/spirallens` runtime, export, base-dependency,
   persistence/science-artifact, or authority change.
5. Keep the accepted bounded-file primitive private and preserve its audited
   limits. It remains POSIX `dir_fd`-oriented, uses `O_NOFOLLOW` only when the
   host exposes it, may block while opening a FIFO before the regular-file
   check, and detects bounded before/after metadata drift without proving full
   hostile-race or TOCTOU safety. Any additional consumer requires a new
   equivalence audit.
6. Continue `RepositoryContext` migrations only where the existing marker
   reduces duplicated origin plumbing without changing domain failures.
7. Preserve the accepted Atlas reader/capture import boundary and its
   fresh-wheel forbidden-prefix probe; any public promotion or added capture
   coupling requires a separate review.
8. Keep the strict YAML factory private and limited to the four audited
   mapping-policy consumers. Adding the CLI, neighbor-receipt, or ordinary
   `safe_load` families requires a new equivalence decision because their
   alias, merge, key, and failure behavior differs.
9. Preserve the array-fingerprint rejection. Reconsider only after a versioned
   D7 trust-closure decision no longer requires the exact
   `qualification/common.py` bytes and a remaining independent consumer set
   demonstrates the material-reduction gate; never relax the historical
   verifier merely to enable deduplication.
10. Keep VOY-V4 on hold. Returning to that lane requires a separate reviewed,
   versioned readiness/authority decision and disjoint execution coordinates.
