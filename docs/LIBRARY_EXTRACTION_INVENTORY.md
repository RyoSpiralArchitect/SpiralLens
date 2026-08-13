# LIB-L0 Extraction Inventory

This document is a non-authoritative review view for deciding whether an
internal mechanism is ready to move toward a reusable SpiralLens contract. It
does not change the canonical library milestone, promote a Python API, grant
experiment authority, or alter a scientific claim. The Roadmap and API Status
remain authoritative for those boundaries.

## Audited coordinate and claim boundary

- baseline commit: `a7e24f912ffeaa15a6b79bf200c39dccf9cd5746`;
- baseline Git tree: `d553fd83c37c5cb1490dd09e777f734e1192e580`;
- `LIB-L0`: `in progress`;
- public root surface: only `spirallens.__version__` is supported;
- observed `__all__` baseline: 559 names across 24 package initializers;
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

The v0.5 repository-only distribution validator records zero matching members
in the sdist, direct-source wheel, and sdist-derived wheel. Fresh non-editable
installs of both wheels produce 22 exact requested-module
`ModuleNotFoundError.name` receipts and retain the ordered
`spirallens.access` and `spirallens.qualification` `__all__` surfaces. This is
a bounded two-prefix separation result, not a general repository-file
allowlist: `closed_library_allowlist_established` remains `false`, and every
authority, library, public-API, and scientific grant remains `false`.
The sdist is a library source artifact, not the repository experiment replay
or test bundle: experiment-facing tests that remain in it require the omitted
repository source modules and are not an installed-distribution conformance
surface.

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
| strict YAML loading | provisional duplicated mechanism | present; PyYAML | supplied YAML parsing; domain schemas and errors stay local | contexts, instrument registry, synthetic protocol, Atlas engineering protocol | distinct domains | not established | not established | duplicated local loaders; no extraction delta yet | hold until an exact policy/failure matrix shows material reduction |
| immutable-array/fingerprint helpers | provisional local mechanisms | present; NumPy | in-memory numeric identity; scientific interpretation stays local | graphs, qualification, synthetic | multiple domains but compatibility unproved | not established | not established | small scattered duplication | hold; do not merge distinct hash framing or scientific units for cosmetic deduplication |
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
6. A fresh non-editable wheel verifies both import origin and its complete
   library/experiment member classification.
7. The change materially removes duplicated production plumbing. A review
   should normally stop a pure deduplication that removes fewer than 20 lines
   or less than 20 percent of the duplicated block; a boundary split may
   substitute proof that its forbidden dependency/member set becomes empty.
8. If a proposed common scaffold is net-positive or fails equivalence review
   twice, retain only the rejection record rather than the scaffold.

## Next bounded decisions

1. Preserve the fail-closed exact-set build gate and machine-readable proof
   that the 22 repository-experiment modules remain in source but not in the
   sdist, either wheel route, or either fresh non-editable installation.
2. Keep the accepted bounded-file primitive private and preserve its audited
   limits. It remains POSIX `dir_fd`-oriented, uses `O_NOFOLLOW` only when the
   host exposes it, may block while opening a FIFO before the regular-file
   check, and detects bounded before/after metadata drift without proving full
   hostile-race or TOCTOU safety. Any additional consumer requires a new
   equivalence audit.
3. Continue `RepositoryContext` migrations only where the existing marker
   reduces duplicated origin plumbing without changing domain failures.
4. Preserve the accepted Atlas reader/capture import boundary and its
   fresh-wheel forbidden-prefix probe; any public promotion or added capture
   coupling requires a separate review.
5. Keep VOY-V4 on hold. Returning to that lane requires a separate reviewed,
   versioned readiness/authority decision and disjoint execution coordinates.
