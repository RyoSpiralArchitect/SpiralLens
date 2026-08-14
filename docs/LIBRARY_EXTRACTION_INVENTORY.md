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
  `spirallens.python-distribution-members.v0.1`, 9,850 bytes, SHA-256
  `ca5e4b8523cd0c14cdbc0e846dbf9b5128ab29d51ffc4a4fd83f582b899c303a`;
- current ordered-export declaration manifest:
  `distribution/spirallens_ordered_exports_v0_1.json`, schema
  `spirallens.ordered-package-exports.v0.1`;
- current installed-import outcome manifest:
  `distribution/spirallens_installed_imports_v0_1.json`, schema
  `spirallens.installed-import-conformance.v0.1`, 6,497 bytes, SHA-256
  `0314de5a125262522bdb2b141e4f9b191c8935979a8d0c4da946f215b2abc9cd`;
- current generated navigation/freshness view:
  `docs/generated/lib_l0_status_v0_1.json`, schema
  `spirallens.lib-l0-status-view.v0.1`, non-authoritative;
- current `src/**/*.py` partition: 182 modules = 133 wheel-present modules
  (24 package initializers + 2 console-entrypoint runtime + 107 shipped
  runtime) + 49 repository-only modules;
- `LIB-L0`: `in progress`;
- supported pre-1.0 surface: `spirallens.__version__` is the sole prospectively
  designated coordinate; no policy-bearing release has occurred, repository
  `0.2.0` candidate metadata activates no protection, and historical `0.1.0`
  compatibility is unattested;
- closed static ordered `__all__` declaration inventory: 559 namespace-scoped
  entries across 24 package initializers;
- closed installed-module outcome inventory: 133 modules = 131 base-import
  successes + 2 exact blocked-Torch model-extra outcomes; scoped runtime
  `__all__` observation: 23 initializers and 554 entries succeeded, while one
  initializer and five entries were unavailable; the two failures are
  `spirallens.adapters` and `spirallens.adapters.pythia`;
- scientific and VOY deltas: none;
- D7 verified-B interpretation: `insufficient`, Level 0, claim delta `none`,
  and VOY-V3 purpose evidence only; VOY-V4 dispatch remains unauthorized.

Artifact records, documentation projections, tests, CLI wrappers, and members
of one experiment chronology do not count as independent library consumers.
A physically installed module is not thereby a public or stable API.

The generator binds the Frame, Ledger, Roadmap, validator, three manifests,
and its own bytes. `--check` observes committed/rendered equality for bounded
reads during its invocation, writes nothing, and owner docs record no view hash.
Freshness is not validation and grants no API, support, compatibility,
portability, library maturity, `LIB-L0`, science, authority, or D7 readiness.

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

The historical pre-boundary repository-only inventory was:

| Group | Source members | Physical LOC | Public/export status | Historical distribution status |
| --- | ---: | ---: | --- | --- |
| `spirallens/qualification/confirmation_v1_*.py` | 20 | 17,312 | internal; no `confirmation_v1` export | absent from sdist and wheels |
| `spirallens/access/_pythia160_*.py` | 2 | 1,878 | private; no access/root export | absent from sdist and wheels |

The current repository-only inventory extends that same source-preserving
boundary:

| Group | Source members | Physical LOC | Public/export status | Current distribution status |
| --- | ---: | ---: | --- | --- |
| `spirallens/qualification/confirmation_*.py` | 47 | 54,034 | internal; none is a qualification/root export | absent from sdist and wheels |
| `spirallens/access/_pythia160_*.py` | 2 | 1,878 | private; no access/root export | absent from sdist and wheels |

All 49 ordinary source files and their 55,912 physical lines remain at their
reviewed repository paths. The 27 newly separated confirmation modules account
for 36,722 of those lines; their source bytes and the historical S → A → B
source, artifact, and result bytes are not moved or rewritten. The installed
qualification closure retains exactly 19 model-free D0-D6 modules, 38,377
physical lines, and all 115 ordered qualification-root exports.

`MANIFEST.in` excludes the two reviewed prefixes from the sdist, while the
custom `LibraryBuildPy` command filters the exact 49-module set from wheels.
The build fails closed if the full source tree contains a partial set, a new
prefix-matching file, or a non-regular reviewed path. Only a sdist-shaped
source tree with an ordinary root `PKG-INFO` and no `.git` marker may contain
the empty source set; this marker combination is not an independent provenance
proof. Matching stale `build/lib` outputs, including nested PEP-3147 bytecode,
are rejected before wheel
publication and are not deleted by the build.

The current v0.10 diagnostic retains the versioned physical manifest and
closed wheel Python-module inventory. They fail closed over every
`src/**/*.py` path and require the exact 133-member shipped set in the sdist,
direct-source wheel, sdist-derived wheel, and both fresh non-editable
installations. The 133-member ordered-path SHA-256 is
`14af4613ed6479b0bacfd5c1293a7c6c12ee9087e85c43adc771d2d2dd4e91f4`;
the source inventory is the exact 133 + 49 partition. The sdist also carries a
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
`6f4556d990e93b4b82b857a872c25f7efd0b40a9e2131ee818832946137a7efa`
and ordered-export digest
`e2c947c30f0323c54c1713274dac0117fd74dc86cd576279c44a040dfc0ae798`.
The sdist carries a byte-identical copy of the manifest, whose SHA-256 is
`cb9d58ba50c3ead9551da17a7b3d31180157c0b0f7b005aff2df4c5f05effe3e`.
Fresh-install inspection parses distribution-owned initializer bytes without
importing a `spirallens` module.

The unreleased `0.2.0` candidate received a separate full-distribution observation from clean main
`58ce3e19521934fc3b0c20b1fb35fefca28afcf6`, tree
`fbbcfaeb1901aee949a8255ba9bb3d256ab5558a`, with empty pre/post status. The command
`python3 scripts/validate_distribution.py --source-root .`, using validator SHA-256
`b928c365253115a6c433a8762f12c40cb105cb9d77a5bbf29fb9547f6d601b48`, emitted 759,149 bytes at
`b8fff56976a404357905fd1b024f8867c74de26e47b3f1b85ef14185af5352ab`; schema v0.9 reported `pass`.
Host: CPython 3.13.13 / macOS 26.2 arm64; `pip/build/setuptools/packaging/numpy/scipy/PyYAML`
`26.1.1/1.5.1/81.0.0/26.0/2.4.4/1.17.1/6.0.3`. Host `wheel` was absent; isolated backend versions were unrecorded.

- sdist: `spirallens-0.2.0.tar.gz`, 969,693 bytes, `4648993d607d9daeeddea91b743c2e07f4cd23f4fa83bd255a75ce537632e11a`;
- direct wheel: 959,887 bytes, `b38f5dbba968fa8d9dc4e2ba7e9a83f0d4dc03d0b081a5e1176da77d06024c73`;
- sdist-derived wheel: 959,887 bytes, `66b97f8e0f4c7d5c6c2ff9fc6938fe851101ac840928200183dfeefe6b3503f4`.

The report observed 181 source modules and exact 159-member parity through the sdist, both wheels,
and both fresh non-editable installs; 24 initializers / 559 exports; an absent top-level sdist `tests` path; initializer digest
`6f4556d990e93b4b82b857a872c25f7efd0b40a9e2131ee818832946137a7efa`; and equal outcome digest
`8f885faab04cd796285d6263381172a4697fc310dafd96c504de44b4214187c7` on both installs.
Separately, main run `31719129800` passed the selected direct-wheel six tests on CPython
3.11.16 / 3.12.14 / 3.13.15; wheel hashes were
`f369816d8af8c2e3abbe0117758be0255f79573f8d1ca45765c2c72ee287db95` /
`19a2505a064a05f8a696b554628b2979feb9376f48e9b34bf8021d74a33d641c` /
`eb2776438cf52f8a38daf98a692a3f1d8bb724d3aa58c2597c2649da0b8960c4`.
These are nondurable environment-specific observations, not reproducible or published identities;
build isolation was not hash-locked and base dependencies were host-projected. No tag, index install,
release, support, full compatibility, portability, core promotion, D7 readiness, science, or authority is
established; these later docs are outside the tested checkout.

The installed-import manifest adds a distinct dynamic observation without
changing those physical or static roles. For both the direct-source and
sdist-derived wheels, the v0.10 diagnostic imports each of the exact 133 modules
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
route observes 131 base-import successes, two exact blocked-Torch model-extra
outcomes, no loaded optional prefix, and the exact three declared bases as its
aggregate loaded third-party distributions. Of the 24 initializers, 23
reproduce their exact runtime list-valued `__all__`, totaling 554 entries; the
five `spirallens.adapters` entries are unavailable with that initializer at the
blocked Torch boundary. Their normalized startup receipts are equal. PR100's
two then-new successes were the private `spirallens._model_observer` seam and
`spirallens.atlas._capture_store`. `BatchObservationProtocol` declares only
the structural observation/import boundary; offline conformance passes a reference
`PythiaAdapter` observation into the store without replacing the Tensor-backed
`BatchObservation`, changing an artifact schema, or advancing residual-hooks
v2. Satisfaction is implicit, not a runtime `isinstance` gate. It is not a
public adapter protocol or a NumPy-owned/value-neutral record. The two later
Atlas successes are `spirallens.atlas.id_sweep` and
`spirallens.atlas.engineering_run`. A source probe and both fresh-wheel workers
resolve all exact 20 root/star exports with their defining identities under
blocked model prefixes. The neutral sweep hints resolve; `run_id_sweep` keeps
its raw signature/annotations and imports Torch before adapter/config access.
The public runner keeps its root identity, structural signature, raw
annotations, and exact model-free resolved hints; its first executable work on
call imports Torch and then the adapter before argument/root access. Default
resolved run-sweep hints, resolved private-helper hints, and compatibility for
former private adapter/capture-version globals remain outside this claim. The
historical
pre-boundary 159-member routes had outcome-manifest SHA-256
`8f885faab04cd796285d6263381172a4697fc310dafd96c504de44b4214187c7`.
Their adopted pre-projection live validation receipt has SHA-256
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

The v0.10 report adds `qualification_state_conformance`, schema
`spirallens.qualification-state-conformance.v0.1`, from one identical
model-free probe over staged source and both fresh-install routes. It requires
the exact origins `spirallens`, `spirallens.core`, `spirallens.core.canonical`,
`spirallens.qualification`, its `.common`, and its `.contracts` under each
intended root. Exact `pass`, `fail`, `insufficient`, and `not_run` `GateResult`
rows are canonically rendered, parsed, reconstructed with `from_dict()`, and
rerendered; the report requires route equality, preserved state and claim scope,
and no negative-to-`pass` change. A passing report observes only that fixture
gate and a bounded origin slice, not a full library suite or API/runtime-artifact
schema, support, compatibility, portability, science, authority, D7/re-anchor,
release, or `LIB-L0` grant.

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
roles. Portability is also independent: the shipped set retains exactly 19
model-free D0-D6 qualification modules and all 115 ordered qualification-root
exports, while the 47 D7 `confirmation_*` implementation modules are
repository-only. Legacy repository-inferred operations and other open gates
mean that the full wheel is still not library-grade. The report states
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
or test bundle. A current repository test-file count is intentionally not
frozen here. The former sdist's 106-file surface was an implicit partial subset,
retaining tests that can depend on omitted helpers or
the deliberately repository-only experiment modules. That subset was neither
self-contained nor an installed-distribution conformance, replay, or maturity
surface. The v0.10 diagnostic now requires exact absence of the top-level
sdist `tests` path and records `observation="absent"`, `count=0`, and
`members=[]`. This is explicit distribution-role separation, not a closed
inventory of every sdist member, an installed test contract, experiment replay,
or library evidence.
The v0.1 classification admits only ordinary Python modules. Shipping package
data, extension modules, namespace/generated modules, or bytecode-only modules
requires a reviewed, versioned manifest/schema successor rather than an
implicit exception to the closed inventory.

## Namespace-export repository-context audit

The bounded static audit at clean baseline
`a2b7a01f97dc8bbc1e83a9d30142bcff009bbaf0` stops before creating a
normative manifest. The 24 package initializers still declare exactly 559
ordered namespace entries. Their source forms comprise 175 eager operations,
264 eager classes, 109 eager values, four `TypeAlias` declarations, and seven
lazy Atlas exports. Resolving those seven static lazy bindings yields 178
operation entries representing 175 unique functions, 271 types, 110 values,
and zero unresolved entry kinds. This is a source census only: a namespace
entry is not thereby a public API, and a resolved operation is not thereby
portable, safe, supported, importable in every environment, or repository
independent.

Only 14 operation entries, each a unique function, have a defensible
repository-context classification at this review coordinate:

| Classification | Count | Exact namespace operations |
| --- | ---: | --- |
| explicit context required | 8 | `spirallens.atlas:run_public_example_plumbing`; `spirallens.qualification:build_current_qualification_engine_binding`; `spirallens.qualification:prepare_closed_d0_d5_selection_protocol`; `spirallens.qualification:prepare_selection_launch`; `spirallens.qualification:publish_closed_d0_d5_preseed_readiness_artifact`; `spirallens.qualification:verify_closed_d0_d5_preseed_source_readiness`; `spirallens.qualification:verify_protocol_source_binding`; `spirallens.qualification:verify_protocol_source_binding_successor` |
| optional context with repository fallback | 3 | `spirallens.qualification:advancement_source_binding_sha256`; `spirallens.qualification:build_current_advancement_source_binding`; `spirallens.qualification:validate_advancement_decision_source` |
| direct repository inference | 1 | `spirallens.qualification:run_and_publish_calibration_selection` |
| transitive repository inference | 2 | `spirallens.neighbors:run_faiss_hnsw_qualification`; `spirallens.synthetic:emit_representation_phantom_bundle` |

At that gate the other 164 operation entries, representing 161 unique
functions, remained `not_established`. Neither absence of a direct `__file__`
expression nor lack of an observed repository access proves that a callable or
its transitive callees are repository independent. A 559-row normative
declaration would therefore either duplicate the existing ordered-export
inventory or turn those unknowns into unsupported portability claims. Adding a
parser and report projection would grow the experimental validation surface
without closing a `LIB-L0` exit criterion. The manifest/parser/report proposal
was rejected at that gate; no source, test, schema, report, runtime, export,
dependency, API, library, scientific, authority, or VOY state changed.

One later bounded audit at clean baseline
`e55a05e812e6fefda8e5924e0ba483b35fc6840e` classifies exactly four
coordinates as `implementation_repository_context_not_required`:
`spirallens.core:canonical_json_bytes`,
`spirallens.core:canonical_json_sha256`,
`spirallens.core:parse_canonical_json`, and
`spirallens.core:sha256_bytes`. Their exact defining targets are the same names
under `spirallens.core.canonical`. The reviewed source identities are
`src/spirallens/core/__init__.py` SHA-256
`3a1af1d86ac24e9796d5f0961180352c669e5dd37ed46e8fa2c0cea9dc31df1d`
and `src/spirallens/core/canonical.py` SHA-256
`0a39f0b896e0ae1c2af8d1910dd37afae31ad563c20df785973a91ff4cadac5e`.

The 6,101-byte test
`tests/test_core_repository_context_policy.py`, SHA-256
`f2e2580eb3c017a21508887b9d350f00bfb4e7fafb146a2b871a20bcdc7dc5d0`,
fails on source-identity, exact-import, namespace/defining-function join,
module-top-level call, local-call-closure, exact-call-syntax, or forbidden-name
drift. Its focused gate passed once. This establishes only that the current
SpiralLens-owned implementation closure requires no repository context.
Receiver and protocol calls, including custom `Mapping` methods, can execute
caller-owned code; the test is not a purity, callback-freedom, side-effect
freedom, safety, portability, compatibility, support, API, or stability proof.

The counters are now 18 classified namespace coordinates and 18 audited
function identities. The remaining 160 `not_established` coordinates comprise
157 never-audited function identities plus the three
`spirallens.instrument_contracts` root aliases `canonical_json_bytes`,
`canonical_json_sha256`, and `parse_canonical_json`. Those aliases reach
already-audited targets, but their namespace import closure has not been
audited, so they inherit no declaration. `LIB-L0`, science, authority, and VOY
remain unchanged.

The final declaration-only candidate, at clean baseline
`65a567659200ac41c5a15329af1074239b525ac5`, was
`spirallens.gauge:{orthonormal_frame,principal_angles,procrustes_connection,track_subspaces}`
across `src/spirallens/gauge/{__init__.py,procrustes_connection.py,subspace_tracking.py}`.
Its owned implementation closure was semantically eligible and showed no
repository, file, environment, process, or network dependency, but the honest
formatted non-import AST ratchet required 230 lines and exceeded its hard
220-line gate. The candidate was withdrawn rather than hidden behind opaque
digests or a shared analyzer, and no test or declaration was adopted.
The counters remain 18 classified coordinates / 18 audited identities and 160
unknown coordinates = 157 never-audited identities + the three unaudited
`spirallens.instrument_contracts` aliases. Mechanical declaration-only rollout
stops here. At clean baseline
`20409385eda0e0922772f08137f02ed8fc54d012`, production migration of
`spirallens.qualification:{advancement_source_binding_sha256,build_current_advancement_source_binding,validate_advancement_decision_source}`
was rejected. The first signature already requires the `repository_root`
keyword but accepts `None`; the latter two also default it to `None`. Removing
those forms changes accepted inputs and public signatures. Reviewed SHA-256
values were `7001959db17fb2d6c44fcdca024cc6ffc22b4df74a0a20333e94e113e470cc0a`
for `advancement.py`, `ce82f280348cbe4a5a21881c6dfea6d7a66d5a3e502e0ef00e27060350326f50`
for `_repository_context.py`, and `e000cddd999a78af5911ca00325f0c6cb9da9e1a776311e66a629c8042d3b879`
for `qualification/__init__.py`. Advancement is an exact D7 critical-runtime
source/chronology member; its frozen bindings are not rewritten or re-anchored.
A `samefile` gate would change repository acceptance, validation/error order,
and the existing TOCTOU surface; a new wrapper would retain the fallback and
expand the namespace. Both are rejected. Even deleting the 11-line resolver
from the 217-line operation cluster yields at most `-5.1%` and fewer than 20
lines, below the materiality gate. Counts remain 18 / 18 with 160 unknown.

At clean baseline `9eeec4234790babae22989f36f4ad94c5eef94df`, the Faiss transitive-context audit rejected every migration shape. The exact exported signature is
`(output_path: str | Path, *, worker_runtime_contract: Mapping[str, str] | None = None) -> FaissHNSWQualificationReceipt`; it has no repository argument. Its sole production
caller, the CLI preflight, also independently infers its root from `__file__`. The runner
captures source twice, each through 10 Git subprocesses including `ls-remote`; its
reporter-first happy path launches 25 subprocesses overall and accepts mixed physical
origins with parent A and worker B.
The 119-line source capture plus 200-line exported runner total 319 lines; replacing one
inferred-root line is about 0.3% and meets neither the 20-line nor 20% materiality gate,
with only one production consumer. Required context changes accepted inputs and
failure/observation order; optional context retains the fallback; a wrapper retains the
legacy coordinate while expanding exports. Reviewed SHA-256 values are
`ed29de5a89284d57b2a3628debc3cd8a8fe1586522fab5e02c2506778358ba92` for the runner,
`ce82f280348cbe4a5a21881c6dfea6d7a66d5a3e502e0ef00e27060350326f50` for the context,
and `934695307a3b116805a7115a95b75dd411d61089697e31e3c3d0c94919bef4f2` for the CLI.
The runner is a historical D7 C1/C2 source member, not a direct `_CRITICAL_RUNTIME_MODULES`
trust root; historical receipt `3c8c136c1e0dbbd84033b3c7144708b496e79bedc21dd9d5768494d37ba46b76` remains frozen and unre-anchored. Faiss stays transitively inferred; counts stay 18 / 18
with 160 unknown. At clean baseline `8cc2a594ceb25697f276d8c56bc0c718131dbcff`,
the phantom audit also rejects every migration shape. The exact exported signature is
`(protocol_path: Path, output_dir: Path) -> EmittedRepresentationPhantomBundle`; its
sole production consumer is the CLI adapter. The reviewed 301-line cluster
is the 21-line Git helper, 27-line revision verifier, two-line root helper,
23-line registry resolver, and 228-line exported emitter. Replacing its one
inferred-root expression is `1 / 301`, about `0.33%`, below both materiality
gates. Required context breaks accepted Python/CLI inputs and inserts a new
root/origin observation into the existing protocol load, generator-source/Git
verification, registry resolution/digest, and staged/published-output validation
order. Optional context retains inference; a wrapper retains the legacy
coordinate and expands exports. The emitter is a historical D7 v0
C1/item21/item22 and v1 C1/C2 source member, but not a direct
`_CRITICAL_RUNTIME_MODULES` trust root. It is distinct from the frozen P1
protocol and `representation_phantom.py` generator; neither frozen byte set nor
historical receipt is rewritten or re-anchored. Phantom remains transitively
inferred; counts stay 18 / 18 with 160 unknown. Repeated context-rejection
reviews stopped here; the completed core promotion audit retains HOLD. No production source,
test, schema, artifact, report, receipt, re-anchor, runtime, export, dependency, API,
portability, maturity, network-free, `LIB-L0`, science, authority, or VOY state changes.

## Candidate inventory

`input equivalence` includes accepted values, bounds, and observation order.
`failure equivalence` includes exception type, stable code/message boundary,
and retained state. `Unknown` or `not established` stops extraction.

| Surface group | Current maturity | Wheel/dependencies | I/O and claim boundary | Existing production consumers | Consumer independence | Input equivalence | Failure equivalence | Current production/export delta | Disposition and blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exact-seven `spirallens.contracts` root namespace | provisional; bounded source/direct-wheel namespace observation only | present; NumPy; the SHA-fixed test runs exact 42 source nodes and exact 41 wheel-safe nodes at the exact three CPython / Ubuntu 24.04 x86_64 locked-dependency direct-wheel coordinates; only the source manifest/consumer join is excluded from the wheel selectors | in-memory typed mathematical/calibration values; no persistence, science, or authority grant | exact source-static direct-root graph: `calibration/{phantoms,suite}`, `holonomy/{connection,discrete,metrics}`, `loops/sampled`, and `topology/winding`; this is not runtime/installed consumer evidence | `ContinuousHolonomy=established` from discrete construction and the independent metrics matrix/polar consumer; connection annotation/delegation is excluded. `SampledLoop=established` from sampled construction, connection integration, and independent winding field sampling. `CalibrationCheck=not_established`; `CalibrationReport=not_established`; `LoopOrientation=not_established`; `SampledWinding=not_established`; `WindingEstimate=not_established`. Direct-import module count alone never decides independence | the enumerated behavior and root/defining identities are bound in source and the direct wheel, with exact origins for `spirallens`, `spirallens.contracts`, and its two defining modules | only the test's exact enumerated failures are bound in source and the direct wheel | existing manifest-owned seven names; PR107's `+1` production line makes default-generated `SampledLoop.parameter_values` read-only; PR110 changes only test, workflow coordinate, docs, and generated view | admit only the bounded observation and source-static per-name independence decisions, not full library-test ownership, the other 552 exports, sdist-derived behavior, runtime/installed consumer independence, namespace admission, or promotion; `closed_library_allowlist_established=false`; `closed_public_api_contract_established=false`; all distribution grants remain false; support/stability/compatibility/portability/typing/release remain unestablished; `LIB-L0` remains in progress; no science/authority/D7 state changes; historical source/D7 receipts remain unchanged and unre-anchored, with current readiness false |
| exact-25 analytic calibration/holonomy/winding slice | provisional; bounded model-free source/direct-wheel observation only | present; NumPy/SciPy; the exact three SHA-fixed test files run 1 + 10 + 14 nodes by full-file execution without node-id selectors, skips, deselection, or xfail in source and a neutral direct wheel at the exact CPython 3.11.16 / 3.12.14 / 3.13.15, Ubuntu 24.04 x86_64, locked-dependency coordinates | analytic positive/negative controls only; no persisted, scientific, authority, or D7 meaning | one vertical production lane: `spirallens.cli` -> `calibration.suite` -> `loops`/`holonomy`/`topology` | no second independent production consumer established | exact 15-module loaded/origin closure plus exact 24 ordered check names/categories, finite values, and pass recomputation | only selected analytic behavior; namespace signatures and exhaustive failures are unobserved | one test-file delta and workflow plus docs only; no production, export, dependency, manifest, validator, report, or schema delta | no namespace admission/promotion or full exact-27 coverage: `affine_transform_loop` and `signed_area_2d` remain unobserved; no sdist behavior, repository independence, portability, support/API/compatibility/release, full library-test ownership, science/authority/D7 change, or `LIB-L0` completion |
| `spirallens.core.canonical` | stable candidate; promotion HOLD | present; standard library | in-memory canonical bytes/digests; no claim or authority meaning | many modules use defining or legacy leaf paths; exact root-name consumers remain zero | 5 / 7 exact symbols meet the per-symbol gate; `JsonScalar` and `JsonValue` each have zero independent production consumers, and the neighbor alias is a separate local definition | selected exact success and ordering behavior plus the README example are frozen; the six-test surface passed from direct installed wheels only for CPython 3.11.16, 3.12.14, and 3.13.15 on the recorded Ubuntu 24.04 x86_64 runner images and exact locked dependency tuple; full compatibility, typing, other environments, and exhaustive/custom-`Mapping`/resource behavior remain unestablished | selected core failures are frozen; domain errors remain local, and exhaustive/custom-`Mapping`/resource behavior is excluded | exact seven exports unchanged; test/docs/CI-only ratchet; no `py.typed` or static-checker receipt | coherent exact-seven promotion is rejected: HOLD, not designated, and inactive; no release, version, support, stability, or typing state changes |
| private `RepositoryContext` | internal | present; standard library | construction performs no I/O; consumers perform repository/import-origin checks; no Git, claim, chronology, or authority proof | `build_current_qualification_engine_binding()` and `run_public_example_plumbing()`; D7 internals are one chronology family | candidate pair only; not yet an accepted two-consumer decision | each consumer retains its own policy | deliberately domain-local | foothold baseline `+109` production LOC, `+0` exports | hold private; reuse this one marker for reviewed migrations and create no parallel context family |
| private bounded held-file byte read | internal private primitive | present as a private package module; standard library only | bounded regular-file bytes through held directory/file descriptors; parsing, digest checks, read traces, and authority remain in wrappers | `access.descriptor` and `referents.loader` | established: two distinct production domains | established for the byte primitive; each wrapper retains its exact path/digest preprocessing and observation order | established at the wrapper boundary, including domain exception type/message, direct OS cause/context, policy no-cause/context, and held-descriptor close order | against extraction baseline `be274333e77d7518cb21ddb6afda3d62222e4b6c`, `_held_file.py` / `access/descriptor.py` / `referents/loader.py`: `0/517/179 → 85/457/105`, total `696 → 647` (`-49`, 25.8% of the audited 190 duplicated LOC); `+0` exports and dependencies | accepted only as a private neutral byte primitive; no public promotion or additional consumer follows without a new equivalence audit |
| private held-directory traversal | internal private primitive | present inside the existing `_held_file.py` wheel member; standard library only | absolute directory-component traversal and caller-owned final descriptor only; leaf open, read/write, mode, identity, fsync, reservation, recovery, publication, and authority remain in callers | bounded readers in access/referents; the access descriptor exclusive writer; the neighbor-audit reservation publisher | established across three independent read/write/publication roles | consumer-normalized absolute paths, optional `O_DIRECTORY` / `O_CLOEXEC` / `O_NOFOLLOW`, open/close order, and caller-owned return are preserved | access/audit wrappers retain their exact relative-path exception type/message; component-open `BaseException` identity and current-descriptor cleanup are preserved when cleanup close succeeds | against baseline `da10e358e6a6fc009992c5bec3dc7bf0e9d6bca8`, `_held_file.py` / `access/descriptor.py` / `audit_output.py`: `85/457/292 → 85/437/273`, total `834 → 795` (`-39`); the three opener definitions change `65 → 21` (`-44`, 67.7%), with `+0` modules, exports, and external dependencies | accepted only for the neutral traversal; publication and all domain semantics remain local, with no security, portability, API, support, D7, science, or authority promotion |
| private neighbor digest-syntax validator | internal private primitive | present inside the existing `neighbors.contracts` wheel member; no new dependency | lowercase 64-character SHA-256 string syntax only; no digest computation, content identity, security, or authority meaning | neighbor backend contracts, execution-freeze validation, neighbor-audit evaluation, and its downstream persistence receipt | established by execution-freeze and neighbor-audit as two independent consumers; the downstream receipt is reuse but is not counted as independent | exact `str`/subclass acceptance, short-circuit order, original-object return, and label interpolation are preserved | exact built-in `ValueError` type/message and no cause/context are preserved; private helper identity, module, and traceback frame are not compatibility claims | against baseline `c9167ae76757c287d7d75223fd2a33be23e5c777`, `neighbors/contracts.py` / `execution_freeze.py` / `metrics/neighbor_audit.py` / `metrics/neighbor_receipt.py`: `496/2608/3234/1921 → 496/2599/3225/1912`, total `8259 → 8232` (`-27`); validator implementations plus imports change `32 → 11` (`-21`, 65.6%), with `+0` modules, exports, and external dependencies | accepted only for the exact raw-`ValueError` neighbor-family subset; custom-error access/Atlas validators and frozen Faiss source members remain local, with no API, support, security, D7, science, or authority promotion |
| private access schema validators | internal private primitives | present inside the existing `access.contracts` wheel member; standard library only | string-keyed mapping shape, exact keys, lowercase SHA-256 syntax, and enum decoding only; no file, model, claim, chronology, or authority meaning | access policy/descriptor contracts, terminal lifecycle records, and value-access lineage | established across three distinct schema roles; lifecycle and lineage neither wrap nor replay each other | exact production `Mapping`, plain-set key, `str`/subclass digest, and enum inputs, return identity, validation order, and label interpolation are preserved | exact `AtlasAccessContractError` type/message and no-cause boundary are preserved; unsupported enum values retain their native `ValueError` cause/context; private helper identity, module, and traceback frame are not compatibility claims | against baseline `7782b24c350e1ee5f6aeb8e942e82e7063734bb0`, `access/contracts.py` / `access/lifecycle.py` / `access/lineage.py`: `919/566/229 → 919/526/221`, total `1714 → 1666` (`-48`); validator definitions plus import bindings change `74 → 40` (`-34`, 45.9%), with `+0` modules, exports, and external dependencies | accepted only for exact schema-syntax reuse; identifier, lifecycle fact, typestate, lineage derivation, and domain authority remain local, historical source receipts remain immutable and unre-anchored, and no API, support, security, D7, science, or authority promotion follows |
| Atlas manifest reader/capture boundary | provisional/model extra | present; reader closure retains NumPy/PyYAML and a fresh wheel loads none of `torch`, `transformers`, `huggingface_hub`, `safetensors`, `spirallens.adapters`, `spirallens.atlas.id_sweep`, `spirallens.atlas.engineering_run`, or `spirallens.atlas._capture_store`; capture remains a model extra | manifest/file I/O only; no capture, model, claim, or authority meaning enters the reader | `metrics.candidate_pairs` and `atlas.engineering_receipt` | established: two distinct production domains | established for reader signatures, defining modules, public symbol identities/order, accepted inputs, return behavior, and validation order | established for exception-class identity, type/message boundaries, and existing reader failures | against split baseline `a1d6c615da9e39247afa0332658e9aee7b24bb5a`, `store.py` / `_capture_store.py` / `id_sweep.py` / `__init__.py`: `1226/0/589/57 → 760/492/590/78`, total `1872 → 1920` (`+48`), while the reader store loses 466 lines; ordered 20-name `__all__`, exports, and dependencies are unchanged | accepted as a reader import-boundary split because its forbidden import set is empty, not as a total-LOC reduction; whole Atlas remains provisional/model extra, and public promotion requires its own review |
| Atlas neutral import boundaries | provisional/model extra | all exact 20 root/star bindings are base-importable; sweep/runner execution still requires Torch | declaration/configuration/manifest plumbing only; no model execution claim | preparation and model-extra execution sides of one Atlas lane | boundary, not a promoted common primitive | defining/root identities, public signatures/raw annotations, neutral hints, runner hints, and bounded selection are fixed | missing Torch fails first on call before sweep adapter/config or runner arguments/root; private-helper hints are excluded | no module/export/dependency delta; installed outcomes become 131 + 2 | accepted only as a bounded import boundary; operation portability, public protocol/API, support, release, D7 authority, and `LIB-L0` completion remain open |
| private model-observer seam | internal | present; NumPy only, with Torch retained behind the Pythia adapter | private `BatchObservationProtocol` and store-local NumPy import only; no model value or claim meaning | reference `PythiaAdapter` output and private Atlas capture store | producer/consumer boundary, not a promoted common primitive | current Tensor-backed observation satisfies the protocol structurally without changing its public identity or capture v2 identity | store validation remains the owner of array shape and finite-value failures | `+1` shipped module; `_model_observer`, `_capture_store`, `id_sweep`, and `engineering_run` are current base-import successes, while the exact two adapter modules remain blocked on Torch | accepted only as a private import boundary with internal reference conformance; no runtime registration, NumPy-owned value type, public adapter protocol, portability, or `LIB-L0` completion |
| private strict YAML mapping loader | internal private primitive | present as a private package module; existing PyYAML dependency | SafeLoader mapping syntax only; size/source-digest/UTF-8 checks, domain schemas, canonical digests, and claim meaning stay in each wrapper | contexts, instrument registry, synthetic protocol, and Atlas engineering protocol | established: four distinct production domains | established for alias, merge-key, string-key, duplicate-key, standard safe-tag, anchor-only, nonfinite-scalar, and wrapper preprocessing behavior | established for exact domain type/message/cause/context, wrapped PyYAML errors, and raw recursion failure | against extraction baseline `366d195f112bc3b95f36504e8a711029c71e6161`, the four consumers plus `_strict_yaml.py` change from `3081` to `2987` physical lines (`-94`); the audited extraction surface changes `158 → 64` (`-59.5%`), with `+0` exports and dependencies | accepted only as a private syntax-policy factory; domain parsing stays local, and the semantically different CLI, neighbor-receipt, and ordinary `safe_load` families remain excluded |
| private installed-import policy seam | internal repository/build tool | absent from the wheel; exactly one regular byte-identical file in the sdist; standard-library only | immutable installed-import metadata and pure no-I/O worker projection only; no manifest/TOML parsing, operation, claim, or authority meaning | `setup.py` and the repository validator; isolated workers receive projection bytes and do not import the seam | build-tool consumers only, not independent library consumers | established for exact metadata and deterministic canonical JSON projection; setup and validator retain independent parsers and validation | fail-closed policy loading, independent parser/adversary families, and worker missing/extra/type/empty-value/outcome-tamper rejection remain separate | against baseline `ef84d7e2107fb4ff9d931e34523f3e942e9244ad`, `setup.py` / validator / policy / `MANIFEST.in`: `1029/5096/0/5 -> 985/5046/61/6`, total `6130 -> 6098` (`-32`); four exact duplicated blocks move from 66 physical occurrences and 33 redundant lines to zero setup/validator duplicate excess (`33 -> 0`, 100%); `+0` exports and dependencies | accepted as private anti-bloat maintenance only; preserve parser/adversary independence and never install the policy in the wheel |
| exact array-fingerprint framing | rejected at current gate | present; NumPy | in-memory `dtype.str` + shape + NUL + C-order byte identity only; no scientific interpretation | `graphs.common`, `qualification.common`, and `synthetic.representation_estimator` | three candidate domains, but qualification is a frozen D7 trust root and the graph/synthetic pair is coupled | established only for stable ndarray metadata across 21 audited case families; unrestricted duck-typed inputs differ in metadata observation order | native ndarray failures are aligned, but callable-level failure/observation equivalence is not established for changing duck-typed metadata | no production/export delta; the three local function groups total 49 lines, while the only trust-root-free pair totals 33 lines and has no reviewed design demonstrating the required 20-line net reduction | reject extraction: changing `qualification/common.py` adds a direct reviewed-S execution-source violation; do not weaken that verifier, and do not add a sub-threshold two-consumer helper |
| immutable-array helpers | provisional local mechanisms | present; NumPy | in-memory numeric ownership and immutability; scientific interpretation stays local | graphs, qualification, referents, instrument contracts, and synthetic variants | multiple domains but policies differ | not established across rank, dtype, range, nonfinite, negative-zero, and copy behavior | not established across domain exception types and native failures | small scattered duplication | hold; do not merge distinct validation or representation policies for cosmetic deduplication |
| `PythiaAdapter` | provisional/model extra | present; optional model stack | model observation/capture; fake-surface mechanics are not real-model parity | one Pythia-family adapter | fewer than two adapter families | not applicable | not applicable | existing provisional exports unchanged | hold; a second adapter and conformance evidence are required for `LIB-L2` portability |
| D7 `confirmation_*` family | internal experiment implementation | repository source only; absent from sdist and wheels; qualification dependency set | fixed source/history, chronology, authority, no-replace publication, and result joins | callers inside one D7 chronology family | not independent library consumers | intentionally experiment-specific | intentionally experiment-specific | 47 modules / 54,034 LOC retained in source; no qualification/root exports | reject extraction; preserve the verified distribution separation and frozen identities |
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

1. Preserve both reviewed inventories: the 182 = 133 + 49 Python-member
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
4. Preserve the completed private installed-import policy seam. It may own
   immutable metadata and pure worker projection only: setup and validator
   must retain independent fail-closed manifest and `pyproject.toml` parsing,
   validation, error boundaries, and adversaries. Keep exactly one regular
   byte-identical copy in the sdist and none in the wheel; workers must receive
   the canonical projection without importing the seam and must validate it
   independently. Any schema successor or new host-specific exception,
   dependency environment, import mode, or artifact kind requires a new
   reviewed delta rather than a parallel policy copy. This does not convert
   the two build-tool consumers into independent library consumers.
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
