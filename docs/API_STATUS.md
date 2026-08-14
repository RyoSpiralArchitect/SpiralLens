# API Maturity and Compatibility Status

- **Package version:** `0.2.0` repository candidate (unreleased)
- **Software maturity:** experimental, pre-1.0
- **Scientific maturity:** tracked separately by the claim ladder
- **Roadmap lanes:** [canonical current-state table](ROADMAP.md#3-two-independent-maturity-axes)

This document declares which Python surfaces downstream users may treat as
supported, which ones are compatibility candidates, and which ones remain
provisional research APIs. A scientific result cannot stabilize an API, and a
stable software contract cannot promote a scientific claim.

The [Roadmap](ROADMAP.md#3-two-independent-maturity-axes) alone governs lane
status, requirement IDs, and D7 operation IDs. This document governs API
maturity labels only; its implementation summaries are non-normative snapshots
and cannot change experiment status or authority.

## Maturity labels

- **Supported pre-1.0 surface:** explicitly enumerated names protected within
  the first policy-bearing `0.y` line; `spirallens.__version__` is the sole
  prospectively designated coordinate, and no protection is active yet.
- **Stable 1.0 surface:** the later semantic-versioned contract; none exists.
- **Stable candidate:** framework-neutral functionality whose compatibility
  tests have started, but which has not yet met every promotion gate below.
- **Provisional:** documented and tested, but allowed to change between minor
  pre-1.0 releases with migration notes.
- **Internal:** repository or experiment implementation detail. Import paths,
  call signatures, and persistence behavior are not public contracts.

Current owner navigation and byte digests are in the non-authoritative
[generated LIB-L0 status view](generated/lib_l0_status_v0_1.json), schema `spirallens.lib-l0-status-view.v0.1`.
[`--check`](../scripts/generate_lib_l0_status_view.py) observes committed/rendered
equality for bounded input reads during that invocation and writes nothing. It
is not an API owner, validation pass, or grant of support,
compatibility, portability, or library maturity, and establishes no
`LIB-L0` completion, release, science, authority, or D7 readiness/re-anchor.

## Current surface

| Namespace or symbol | Status | Compatibility boundary |
| --- | --- | --- |
| `spirallens.__version__` | prospectively designated supported pre-1.0 coordinate | no policy-bearing release has occurred; repository `0.2.0` candidate metadata activates no protection, historical `0.1.0` compatibility is unattested, and its exact string equals the source/build and installed-distribution version owners |
| `spirallens._repository_context` | internal | non-authorizing marker for a caller-supplied absolute root plus a narrow same-file import-origin comparison; no public export, root discovery, Git, claim, chronology, or publication semantics |
| `spirallens._model_observer` | internal | private `BatchObservationProtocol` declared/import seam used by the Atlas capture store; the reference Pythia output satisfies it structurally, without runtime registration or a change to the Tensor-backed `BatchObservation` identity, artifact schema, or residual-hooks v2 capture contract |
| `spirallens.core.canonical` | stable candidate (promotion HOLD) | the coherent future promotion candidate is the current exact seven-name `spirallens.core` surface: four functions, `CanonicalJsonError`, `JsonScalar`, and `JsonValue`; shared-codec use is established at defining and legacy leaf paths, but exact root-coordinate production consumers remain zero and the compatibility preflight grants no support or stability |
| `spirallens.access` | provisional | typed access, value lineage, pre-observation descriptor, and execution-lifecycle contracts |
| `spirallens.referents` | provisional | canonical F0-F4 pointwise definitions and model-free same-object numeric relations; no substrate field |
| `spirallens.instrument_contracts` | provisional | versioned v0.x artifacts plus an explicit lineage-gated numeric payload session |
| `spirallens.contracts` | provisional; bounded source/direct-wheel namespace observation only | the ordered-export manifest owns the exact seven root names. The SHA-fixed focused test runs exact 42 source nodes and exact 41 wheel-safe nodes—the source manifest/consumer join alone is excluded—at the exact CPython 3.11.16, 3.12.14, and 3.13.15 / Ubuntu 24.04 x86_64 locked-dependency direct-wheel coordinates. It binds the root/defining identities, exact installed origins, and only its enumerated behavior and failures. One provisional source line makes default-generated `SampledLoop.parameter_values` read-only like explicit inputs, with no numeric value, signature, export, or dependency delta. This is not full library-test ownership and covers neither the other 552 exports, sdist-derived behavior, deep-module or per-name two-consumer admission, nor promotion: `closed_library_allowlist_established=false`; `closed_public_api_contract_established=false`; all distribution grants remain false; support, stability, compatibility, portability, typing, and release remain unestablished; `LIB-L0` remains in progress; no science, authority, or D7 state changes; historical source/D7 receipts stay unchanged and unre-anchored, and current readiness remains false |
| `spirallens.loops`, `spirallens.holonomy`, `spirallens.topology` | provisional; outside this observation | framework-neutral mathematics; scientific meaning remains artifact-bound, and no admission decision or promotion follows from the `contracts` observation |
| `spirallens.synthetic`, `spirallens.graphs` | provisional | model-free generator-family controls plus exact graph/domain fingerprints; `CartesianFourierEstimatorInputs.from_observable_arrays()` is the owner boundary for deriving label-free content IDs; scientific qualification remains artifact-bound |
| `spirallens.qualification` | provisional | the installed namespace retains exactly 19 model-free D0-D6 modules and all 115 ordered root exports: frozen D0-D5 protocol and terminal chronology, read-only historical terminal binding, plus a scope-limited D6 decision. The 47 deep-internal `confirmation_*` D7 implementation modules remain at their reviewed repository source paths but are absent from sdist and wheels. They include C1/C2, replay-target/attempt-envelope specifications, D7 record/evidence/result joins, launch/persistence/runner mechanics, the corrected `D7-OPS-21` chain, one repository-local `D7-OPS-22` Level-0 transaction/freeze receipt, one operationally complete/scientifically insufficient but chronology-deviated item-23 result, one all-false descriptor/intent, and a canonical v0.1 disposition; every official v0.1 execution entry is blocked, none is a public export or caller-configurable supplier surface, and no official start/run, trusted pin root, independent confirmation, or D7/D8 authority exists |
| future subject APIs | provisional | no subject execution surface is stabilized or authorized by this table |
| `spirallens.atlas` | provisional/model extra | manifest-reader imports retain NumPy/PyYAML but load no model framework, adapter, or capture runtime. With model prefixes blocked, all exact 20 root/star exports resolve with their defining identities. The five `id_sweep` bindings and neutral hints remain available; `run_id_sweep` still imports Torch before adapter/config access, and its default resolved hints remain outside this boundary. `run_public_example_plumbing` preserves its root identity, structural signature, raw annotations, and model-free resolved public hints; on call, its first executable work imports Torch and then the adapter before argument or repository-root access. Former private adapter/capture-version globals receive no compatibility aliases, and resolved hints for private helpers are nonclaims. The declared Atlas namespace is now base-importable, but execution remains model-extra and the public-example runner remains repository-bound; this grants no operation portability, public API/support, `LIB-L0` completion, release, or D7 authority |
| `spirallens.adapters`, `factors`, `interventions` | provisional/model extra | no framework types may define core artifact schemas; the private seam is not a NumPy-owned or value-neutral observation contract and does not make these namespaces base-importable |
| CLI handlers, workers, frozen one-experiment runners, private context markers | internal | CLI is a thin adapter, never the Python API |

The post-matrix gate qualifies 5 / 7 exact names; `JsonScalar` and `JsonValue`
each have zero independent production consumers. Exact-seven promotion is
coherent, so the review rejects partial promotion: HOLD, not designated or
active. Six selected tests are not full compatibility, and there is no PEP 561
typing claim (`py.typed` and a static-checker receipt are absent).

Repository-bound provisional migration note: callers of
`build_current_qualification_engine_binding()` and
`run_public_example_plumbing()` must now provide `repository_root` explicitly;
the latter's CLI adapter requires `--repository-root`. This is an intentional
pre-1.0 fail-closed change. Neither parameter nor the private context marker
attests Git-root identity or grants experimental authority. The physical
import-origin comparison prevents executing one checkout while attributing its
source binding to another; it is not a Git or scientific-authority proof.

The PR #11 post-D6 descriptive plan and value-blind D7 gap matrix are canonical
research artifacts, not Python APIs. Their historical bytes intentionally add
no runner, writer, family-admission helper, or promotion surface. Later
repository-only `D7-OPS-23` modules now implement the plan's fixed 27-output
derivation and repository-bound no-replace lifecycle. Those exact three v0.1
files remain outside the installed wheel and export nothing from the package
or qualification namespace. All 47 `qualification/confirmation_*.py` modules
and two private Pythia-160M kernels remain an exact 49-module repository-only
source set. They are absent from the sdist, direct-source wheel,
sdist-derived wheel, and both fresh non-editable wheel installations; the
ordered `spirallens.access` and `spirallens.qualification` `__all__` surfaces
remain unchanged; the latter still exposes its exact 115 names from the 19
retained model-free D0-D6 modules. This separation creates no public API and
does not complete `LIB-L0`. The exact three files are members of the reviewed
source/runtime
re-anchor, which was exact-current at issuance. The `0.2.0` candidate changes
frozen v0.1 execution-source members: historical reload remains valid, current
live readiness is false, and no successor re-anchor is created. The
historical plan bytes retain `status=frozen_not_run`,
`runner_implemented=false`, and
`writer_implemented=false`; those fields describe the plan when it was frozen
and are not rewritten as living execution metadata. Commit
`83ed5f419ff27af0935aa84c363df64f04926cac` now introduces the sole item-23
result: 5,293,662 canonical bytes, SHA-256
`d0d498b4fb62b38b31de063010516eb17323a4f5b96f44b3ba1f8e7d5680cf4a`, schema
`spirallens.postselection-descriptive-analysis-result.v0.1`, and result ID
`post-d6-descriptive-a654fa3d9117d2ec9f9275dd`. It has
`status=insufficient`, `operational_status=complete`, Level-0 claim ceiling,
`claim_delta=none`, 26 available outputs, one blocked output, and an exact
seven-file analysis-input trace. The sole blocked output is
`amplitude-identifiability-support-separation`: the historical main D2 scalar
values were not persisted, and no rerun or current-code reconstruction was
performed. No authority flag is true, and D7 and D8 remain `not_run`. A later
review found that item 23 did not satisfy the broader 2026-07-29 chronology;
its separate conformance axis is therefore `deviated`, and it supplies no
`D7-OPS-23` completion credit. The
historical item-22 freeze checkpoint is `full-design-frozen`; the later
all-false descriptor/intent commit moves the current observer to
`launch-intent-present` without launching anything or curing the deviation.
Official v0.1 item 24 is blocked; any execution requires a reviewed versioned
successor. Reusable analysis primitives remain extraction candidates until a
second independent consumer exists.

The spectral-moment four-case generator and
`spirallens.qualification.confirmation_protocol` foundation are internal
development surfaces. Its ordinary or novel builder and strict reader accept
only an authoritative committed-D6 loader receipt, but it deliberately exposes
no full-design freeze, source-closure, admission, lifecycle, execution, result,
or promotion surface. `D7ParentD6Binding` and the foundation are now internal
`v0.2` drafts. They remain unpersisted as standalone/public artifacts, while
C1 preserves their exact canonical historical bodies inside its Level-0
wrapper. Their canonical identity excludes the ephemeral current-loader HEAD
and source-binding digest, while ordinary or novel construction still requires
and validates the typed authoritative loader receipt. The prior internal `v0.1`
drafts have no standalone artifacts or migration surface.

PR26 adds one private, recorded-C1-only archival reconstruction route for the
fixed producer. It first verifies pinned C1/C2, loads the exact parent protocol,
reconstructs the typed design from the C1-embedded binding, and requires
whole-document equality with the design recorded in C1. It is not a general
alternate construction path or a historical reinterpretation of D6 or C1, and
it accepts no caller-authored design.

`spirallens.qualification.confirmation_execution_design`,
`spirallens.qualification.confirmation_execution_kernel`, and
`spirallens.qualification.confirmation_crossed_development` are also internal.
The first requires a strict full parent-protocol load and constructs a
commit-stable `v0.2` seed-slot execution draft. That draft remains unpersisted
as a standalone/public artifact, while C1 preserves its exact canonical
historical body inside the Level-0 wrapper. The second is the single
oracle-free numerical prediction kernel for an explicitly supplied seed;
supplying one attests no freeze, authorization, or chronology. The third
remains a development adapter that accepts only permanently excluded seeds and
stops at sealed predictions. None of these modules is exported
from `spirallens.qualification` or the package root. Their schemas and call
signatures may change before pre-1.0 stabilization. They expose no freeze,
official seed supplier, admission, gate, result, terminal writer, replay, or
promotion API.

`spirallens.qualification.confirmation_rebinding` remains an internal
historical-proposal surface. Its `v0.1` factory and strict reader encode a
successor-only structural rule without mutating D6 v0.1; exact historical
admission remains false.

`spirallens.qualification.confirmation_c1` and
`spirallens.qualification.confirmation_source_closure` are also deep internal
modules. The first persists one atomic, strictly reloadable Level-0 C1
candidate containing the stable seed-free design, declared static-bounded
construction review, implementation registry, aggregation application,
successor-rebinding review contract, and declared source manifest. Declared
source set is not closure: C1 deliberately embeds no future commit,
repository-review attestation, or C2 receipt, and its own historical
`source_closure_verified=false` remains unchanged. The second contains the
choice-free C2 issuer/loader. Its separately committed receipt binds exact
post-merge C1 `e58a8169b41be688628ab7dda583e68088d3affc`; the unique
receipt-introduction commit is
`2f4e715a951211af8ca0ca4f6b2f7473134bf92b`. Neither module is re-exported or
compatibility-supported.

`spirallens.qualification.confirmation_replay_contracts` is another deep
internal module. It implements the canonical, unpersisted
`D7ReplayTargetContractSpec`
(`spirallens.d7-replay-target-contract-spec.v0.1`) and
`D7AttemptEnvelopeContractSpec`
(`spirallens.d7-attempt-envelope-contract-spec.v0.1`). The first defines the
future immutable seed-bearing execution identity without attempt-local paths
or outcomes. The second binds that contract and defines an append-only
attempt-declaration, launch-authorization, exclusive-claim, execution-start,
scientific-result-or-failed-attempt, terminal-manifest, and
terminal-consumption model.
`load_d7_replay_attempt_contract_foundation()` reruns the pinned committed-C2
loader internally and returns only an in-memory
`LoadedD7ReplayAttemptContractFoundation`; it accepts no caller-supplied
source-closure wrapper, expected digest, seed, result, namespace, or
authorization.

`spirallens.qualification.confirmation_attempt_records` and
`spirallens.qualification.confirmation_attempt_validation` are separate deep
internal modules. The first defines closed canonical records for role
evidence, declaration, authorization, claim, start, scientific result or
infrastructure failure, terminal manifest, and consumption. The second
performs pure structural joins over already constructed typed records. Its
isolated-replay derivation requires the complete, internally consistent,
consumed primary chain and a passed primary result; a caller-supplied role
label or disconnected digest set is insufficient. The generic scientific
attempt validator accepts primary attempts only; the combined isolated-replay
validators require both that primary chain and the complete scientific or
failed replay chain. They require the same store identity, because alternate
store global one-shot behavior is unproved. Across primary and replay, the
five execution/intent/key/namespace/path identifiers and four
authorization/pre-start absence-receipt digests form disjoint sets. Both deep
modules declare an empty `__all__`; direct named deep imports remain internal.
Neither module loads a target, verifies external witness bytes, touches a
namespace, writes a record, publishes a terminal, or grants authority.

The separate deep-internal
`confirmation_result_components` and
`confirmation_result_component_validation` modules define canonical,
attempt-independent bytes and pure structural joins for all six result
components. Their closed bundle contains exactly 1,344 event lanes, 192 core
cells, 1,152 loop cells, 64 cell-derived joined primaries, six mechanically
derived strata, and four-state gate rows bound to the outer result. They
enforce digest-before-parse, canonical row reconstruction, exact Cartesian
cell structure, seed-slot case pairing, graph-fingerprint functionality, and
a structural floor that prevents incomplete evidence from becoming an
aggregate pass. They do not load the authoritative target; exact target
inventory and seed values, case membership, and graph nonvacuity therefore
remain unverified. On the fixed PR26 producer/validator path, the exact six
stratum memberships are mechanically rederived from canonical joined-primary
stress assignments, and the exact four-gate manifest, definitions, states,
reasons, evidence digests, and outer-result reasons are reconstructed. This is
code-side structural consistency only; it does not authenticate a target,
authorize an invocation, prove execution, publish an artifact, or establish a
D7 run. Event-stage hashes bind declared structure; they do not prove that
execution occurred or establish producer chronology.

The deep-internal `confirmation_attempt_evidence` and
`confirmation_attempt_evidence_validation` modules define canonical bytes and
pure joins for authorization/pre-start path-absence receipts, in-process or
external failure payloads, and external-abort verification receipts. The path
receipts bind normalized absolute POSIX parents, lowercase portable ASCII
leaves, parent device/inode identity, and distinct authorization/pre-start
observations. They are directly constructible point-in-time assertions: no
authority follows from construction alone. The persistence writer reobserves
their local parent/leaf coordinates, but no reservation, hostile-process
TOCTOU protection, or post-publication inode proof is implemented. A
schema-valid external receipt is likewise not an
authenticated witness, verified abort, or finalization capability.

The deep-internal `confirmation_attempt_persistence` module persists a
caller-supplied primary declaration, launch-authorization record, claim record,
and start record only as evidence. A no-replace immutable store scope and four
predecessor-chained envelopes occupy the dedicated
`d7-prefix-evidence-only-v0/` namespace; raw lifecycle-record bytes are never
top-level stage files. Scope and envelope bytes permanently record false
authority/capability fields and prohibit in-place promotion. Files are
canonical, digest-before-parse, bounded descriptor reads and are published by
descriptor-relative native exclusive rename with file and parent-directory
fsync; Darwin/Linux syscall branches exist and other platforms fail closed,
but only the current Darwin host is qualified by this slice. The
four absence receipts are content-addressed. Authorization/start evidence
reobserves the declared real parent device/inode and absent leaf. Every
existing envelope conflicts even when its bytes are identical. This is a
trusted-local-operator, persistence-only boundary: it does not load the target,
verify source/runtime or execution-identity authority, reserve a namespace,
resist a hostile concurrent administrator, or prove post-publication inode
disjointness.
An interrupted pre-rename publication may leave a dot-prefixed staging entry.
Any such entry blocks lane/evidence reload and retry, is never interpreted as
a stage, and first requires live writers to quiesce. Only a confirmed orphan
may enter a separate offline operator recovery protocol; automatic scavenging
is not exposed.
Its terminal inspection can report only
`caller_supplied_start_record_present_terminal_absent` or
`terminal_path_present_unverified`; it explicitly records
`execution_observed=false` and `started_unresolved_established=false`.

The deep-internal `confirmation_attempt_authority` module adds a separate
non-authorizing structural input candidate. It gives canonical shapes to a
concrete subset of prerequisites that a later operational boundary must
verify. Its replay-target record uses dedicated caller-claimed admission,
exact-full-design, and exact-source/runtime candidate leaf types. Each leaf
and its nested artifact bindings record `identity_authenticated=false`;
positive leaf fields describe claims, not authenticated facts. The admission
leaf preserves the complete construction-review and admission-spec binding
identities. Typed
exclusive-supply-claim and single-supplier-invocation inputs causally join the
supplier, development and parent registries, readiness, caller-alleged
admission and source/runtime receipts, official inventory, and atomic
inventory/full-design/target publication. All claim, invocation, chronology,
inventory-output, and publication verification fields remain false.

The physical input fixes the `primary-confirmation` role and derives the exact
attempt key from the canonical replay-target digest. It binds normalized
store/lane/output/terminal paths, positive store/lane/parent device/inode
coordinates, and the lane-parent-to-store relationship while requiring the
lane identity to differ from the store. It excludes persistence-reserved
evidence, attempt-envelope, and chronology paths by both lexical path and
known declared physical key, and rejects double-slash aliases, embedded NUL,
and overlong declared paths. The artifact-binding API has no raw
`from_bytes` factory. The strict bundle loader applies its byte-size cap first,
checks the expected SHA-256 before parsing, translates malformed, deeply
nested, and oversized-numeric JSON parser failures into
`D7AuthorityInputError`, and then rejoins the decoded records
structurally. The loaded object permanently reports all authorization,
source/runtime verification, admission, freeze verification, path-absence
observation, physical reobservation, and execution claims as false.

This module does not make caller records trustworthy. A canonical record,
matching digest, serialized “capability,” or caller-chosen token is still
caller-constructible data and cannot establish authority. The physical
identity record describes normalized paths, the target-and-primary-role-bound
attempt key, and
declared device/inode coordinates; it is not a live filesystem observation,
reservation, or exclusive claim. “Complete” seed registries mean complete
relative to the explicitly bound registry sources and counts in this
candidate, not proof that an authoritative supplier, parent history, or
unopened-seed boundary has been verified. The typed invocation is likewise a
caller-claimed structural input, not evidence that a supplier ran. No
reusable capability is emitted.

The deep-internal `confirmation_attempt_terminal_persistence` module now
accepts an already persisted prefix plus one completely joined structural
terminal and exposes the whole closed inventory by a descriptor-relative
native no-replace directory rename. It strictly reloads the manifest,
consumption, outcome, and every immutable member by exact digest, type, file
identity, and inventory. Competing attempt-scoped staging entries, uncertain
cleanup, a destination race, stage/parent descriptor drift, symlinks,
hardlinks, FIFOs, missing/extra members, and byte mutation fail closed. Member,
stage-directory, and parent-directory fsync are distinct facts; a failed final
parent fsync remains reported as durability unproved. Structural publication
does not authenticate the prefix, observe execution, or make a scientific
result eligible.

The deep-internal `confirmation_runner` module accepts only a private,
nonserializable primary-confirmation post-start handoff and a zero-argument
scientific producer callback. It validates the complete six-component bundle
and rejoins the callback's replay-target, full-inventory, aggregation, and
result-schema projection to that handoff before preparing a typed terminal.
Ordinary `Exception` objects are re-raised unchanged after best-effort
attachment of a typed in-process failed-terminal handoff; `BaseException` is
not converted into abort evidence. The runner module itself issues no private
ownership. `confirmation_fused_start` is the sole deep-internal issuer: after
durable structural-start publication, strict reload, and unchanged second-pass
observations, it constructs and consumes the handoff within the same call.
Ownership is never accepted, serialized, cached, or returned, and every exit
after its construction atomically invalidates both callback entry and terminal
publication, including a failure before runner dispatch. The runner slice
itself remains generic. A separate PR26 deep-internal surface now fixes the
zero-argument official producer and exact full-inventory, aggregation, and
full-design builders behind the callback boundary; none is officially invoked
or published as an authority artifact. If a handled ordinary exception
leaves a failed terminal visible while its final parent fsync is unproved, the
fused path makes a best-effort attempt to attach the terminal identity and
explicit durability warning to that same exception.

The deep-internal `confirmation_external_witness` and
`confirmation_terminal_operations` modules add the mechanics-only external
abort path. A canonical Ed25519 envelope contains separate observer and
verifier signatures and is persisted as a required immutable failed-terminal
member. The integrated operation accepts no preverified capability and no
caller-supplied finalization/manifest/consumption records: it verifies against
explicit runtime pins, performs the fixed live prefix and terminal-coordinate
revalidation, derives the terminal chain, consumes the one-shot witness,
publishes without replacement, and strictly reloads. It atomically consumes
both callback entry and prepared-terminal publication before verification.
Existing terminals can
also be strictly reloaded and reauthenticated to exact pins. The returned
receipt means `explicit-runtime-pins-only`; it records
`trust_root_provenance_verified=false`, `wall_clock_freshness_proved=false`,
`authoritative_start_proved=false`, `execution_observed=false`, and
`scientific_claim_eligible=false`. Caller-supplied pins are configuration, not
official SpiralLens trust-root provenance or authority.

The deep-internal `confirmation_fused_authority`,
`confirmation_authoritative_start_persistence`, and
`confirmation_fused_start` modules complete roadmap `D7-OPS-20` as mechanics only.
They reopen a committed closed nine-member descriptor at clean current HEAD,
match live canonical `origin/main`, and verify the declared observation
surface: tracked `src/spirallens/**`, `pyproject.toml`, and the required runtime
lock; exact equality of the complete installed distribution name/version
inventory; interpreter executable bytes; producer source/code identity;
selected process-envelope fields; physical
store/lane identity whose repository/store disjointness is proved from
descriptor-relative device/inode ancestry rather than path spelling; and
output/terminal absence. This is not hermetic closure
of installed package files, loaded native libraries, mutable module globals,
callable defaults or closures, unrecorded environment state, model state, or
data state.

The dedicated `d7-authoritative-start-v0/` transaction is structurally named,
not an official authority grant. Its strict loader reports
`authority_authenticated=false`, `authority_granted=false`, and
`started_unresolved_established=false`; visible start bytes with no terminal
block retry but do not by themselves establish the named lifecycle state. The
loader strictly reparses the descriptor and verification evidence and rejoins
their inventory and persisted start bindings. The official descriptor now
exists and strict-rejoins without start or producer entry; full start/reload
was exercised only in the temporary qualification namespace. Repository-HEAD,
canonical-origin, source-tree, dependency-set, callable, and process
observation digests are preserved, not recomputed or independently
reauthenticated by structural reload. Terminal lineage binds the evidence
bytes rather than those live facts.

The replay contracts and attempt records remain specifications and types. One
Level-0 replay-target instance is persisted inside the item-22 target and is
now bound by a separate full-design-freeze receipt, but no authoritative
attempt-envelope instance exists. The local prefix writer embeds
caller-supplied primary types beneath a distinct
false-authority envelope; it exposes no public supplier and grants no lifecycle
or execution authority. Isolated replay is rejected before persistence because
passed-primary consumption cannot yet be established. The seed-supply source
contract requires final-code source/runtime closure and reviewed family
admission, then live recheck → durable claim → supplier entry → atomic
full-design/target publication. The persisted transaction strict-loads and
claims that chronology, but its verification fields remain false and do not
independently establish the historical invocation or transition timing. The
distinct repository-local checkpoint and later freeze receipt are now
committed, but neither supplies launch intent or execution authority. Once its
originating operation ends, a claim left without
an atomically published target is a semantic, non-retryable abort, but its
durable state remains claim-present unless a separate valid abort receipt is
published; target absence does not prove the supplier was invoked. The
target-local claim ceiling stays exactly Level 0
and its authority vector stays all-false. C2 closes only the historical C1
source set and does not cover these modules or later persistence, terminal,
or runner code. The later exact-current source/runtime re-anchor is now tracked;
it remains an honest-local closure rather than signed authority.

`D7-OPS-22` has a deep-internal repository-local one-shot operation:
exact-current recheck, durable claim, one fixed supplier-function invocation,
frozen seed exclusions, then atomic six-member publication. Failure after claim
is non-retryable. This is honest-local same-filesystem coordination, not global
idempotency. Import and tests create no tracked artifact and use temporary
clones. Before the separate freeze receipt is considered, the tracked Level-0
transaction strict-loads at its historical `publication-complete-unfrozen`
stage; with that receipt, the historical freeze checkpoint is
`full-design-frozen`. The later committed closed descriptor advances the
current structural state to `launch-intent-present` without granting launch or
execution authority.
Its invocation artifact claims one local supplier call, while the claim,
invocation, inventory-output, and transition verification fields remain false.
Details
remain normative in [the execution design](D7_CONFIRMATION_EXECUTION_DESIGN.md)
and [`D7-OPS-22`](ROADMAP.md#d7-ops-22).

The `D7-OPS-21` chain remains historically reloadable. The reviewed
exact-current re-anchor is tracked and the target structurally binds it. The
implementation requires a strict live recheck before claim, but the persisted
verification fields are false and do not independently establish that timing.
The invocation receipt claims an honest-local single invocation but does not
independently verify it and proves neither unseen values nor global
independence.

The external-abort path now strict-reloads a `D7-OPS-20` structural start and reuses the signed no-replace terminal transaction without granting authority, execution, scientific, retry, replay, or D8 status.

This branch now contains the reviewed re-anchor, one Level-0 item-22 claim, a
receipt claiming one honest-local invocation, the
`official-seed-inventory.json` schema role, the six-member target, and the
separately committed `full-design-freeze.json`. The later closed descriptor and
distinct launch-intent member are now committed, so the current presence state
is `launch-intent-present`. Its earlier Git ancestry is the target-publication
commit
`f2c1e032f153d369eed99c1bbd467da518b5b9fb`, then the designated repository-local
checkpoint `6ea0ad761ebcf9e9aedb21319747b6489db66c52`, then the freeze-receipt
introduction commit `f07962db96c4e59020c32e1b27ae8598e69ef6d1`. The receipt
designates the middle commit through a repository-local field that contains no
human-review or authorization attestation; regardless of platform
commit-signature evidence, it establishes neither human review nor
authenticated authorization. The receipt keeps
`freeze_verified=false`; all three binding leaves keep
`authoritative_source_loaded=false` and
`identity_authenticated=false`. The item-22 target authority vector remains
all-false. In the inventory, `seed_inventory_frozen`,
`supplier_chronology_verified`, and `cryptographic_unseen_proof` remain false;
unseen status still requires external attestation, and both exclusion bindings
retain false source/identity authentication. Abort evidence, official run, D7,
and D8 remain absent or `not_run`. The separate
item-23 descriptive result introduced by
`83ed5f419ff27af0935aa84c363df64f04926cac` is present and committed, with
SHA-256 `d0d498b4fb62b38b31de063010516eb17323a4f5b96f44b3ba1f8e7d5680cf4a`.
Its operational completion does not change the item-22
historical `full-design-frozen` checkpoint or supply launch, execution,
confirmation, or scientific authority. A later non-retroactive disposition
records `item23_chronology_conformance=deviated`, grants no `D7-OPS-23`
completion credit, and retains its operational `complete` and scientific
`insufficient` axes. The later artifact-only commit
`09b0cc5c08c11e1dfea019ec13fd7a50bcc50bb4` records the descriptor at SHA-256
`0335d80cfef3e54a9dc14045b6d76d3cf0f939dfeb373203a4cce2b1df7704ac`
and its nine-member bundle at SHA-256
`b796ef191840af4ada4172f157be1e7b3e98f1380c7df47d80f4950c0388ee94`.
Descriptor/member structural rejoin remains valid at current HEAD. At
descriptor commit `09b0cc5c08c11e1dfea019ec13fd7a50bcc50bb4`, before the
disposition source changes, exact-runtime/process/store qualification passed
without producer entry. That is historical plumbing evidence; it does not
satisfy current v0.1 live-source equality, and every authority, execution,
result, retry, replay, D7, and D8 fact remains false. Commit
`897dd7c60411f5fd36c6c50fb5064802a25a471b` records the canonical
chronology disposition and blocks the v0.1 runner, canonical fused entry, and
direct producer before start or generator access. The source change
intentionally breaks equality with the old v0.1 execution-source closure.
That identity is superseded before official execution; any future invocation
requires a separately reviewed versioned successor and new coordinates.
Canonical bytes and repository ancestry do not self-promote into authority.

The package root deliberately does not re-export provisional scientific APIs.
Each provisional namespace maintains an explicit `__all__`; undocumented deep
module imports remain internal.

The ordinary `load_instrument_bundle()` API remains value-opaque: it exposes
manifest path metadata but retains no payload descriptor and returns no bytes
or decoded array. `open_numeric_payload_session()` is a separate explicit
value consumer with a trusted parent-policy digest, strict payload request,
and bounded session lifetime. This separation is part of the provisional
compatibility contract.

## Compatibility gates for PR #6 onward

Every PR that grows the research-to-library surface must include:

1. a typed Python entry point independent of `argparse`;
2. an exact schema and canonical round-trip/tamper test for persisted data;
   an intentionally in-memory-only record must instead declare that scope,
   expose no parser/writer, and test immutable fingerprint behavior;
3. an explicit `__all__` update and export snapshot test;
4. this document and the schema-change record updated for public changes;
5. a clean wheel installed into a fresh virtual environment;
6. an import and CLI smoke that proves the installed wheel, not another
   editable checkout, supplied the package;
7. confirmation that core/access import does not load Torch, Transformers,
   Hugging Face, Safetensors, or Faiss;
8. deterministic examples that require no model, network, or private data;
9. explicit failure and non-claim behavior.

Passing these gates does not establish multi-platform support. Supported
Python, operating-system, and backend matrices are updated only after those
environments actually pass.

## Pre-1.0 compatibility and promotion rule

Only explicitly listed supported pre-1.0 surfaces receive this policy from the
first release containing it; repository adoption is not a release promise and
historical `0.1.0` compatibility is not attested. Within one `0.y` line,
callable patches preserve import coordinates and signatures and keep documented
successful behavior and documented failure boundaries backward-compatible. Version
patches preserve the `spirallens.__version__` coordinate, `str` type/value
format, and release-reporting semantics while its value tracks the release.

A breaking change or removal is minor-release-only after a deprecation
announcement in at least one prior minor and a migration note. Pre-1.0
promotion to supported status is also minor-release-only and requires two
independent consumers, full compatibility tests, user-facing documentation,
and an explicit reviewed decision. Stable status is a 1.0 transition.

After any pre-1.0 `spirallens.core` promotion, all seven identities in
`spirallens.instrument_contracts.canonical` and the exact four root aliases
`CanonicalJsonError`, `canonical_json_bytes`, `canonical_json_sha256`, and
`parse_canonical_json` remain identity-preserving through `0.x`. They are
currently legacy compatibility routes, not deprecated, and emit no warning;
the whole `spirallens.instrument_contracts` namespace remains provisional.

A Python environment is supported only for an exact Python patch, OS,
architecture, and dependency-version tuple whose clean-wheel jobs pass;
`requires-python` and classifiers are metadata, not a support receipt. This
policy keeps core on HOLD and establishes no retrospective `0.1.0`, typing, or
portability fact. Scientific results do not govern software promotion.
