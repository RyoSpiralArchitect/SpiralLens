# API Maturity and Compatibility Status

- **Package version:** `0.1.x`
- **Software maturity:** experimental, pre-1.0
- **Scientific maturity:** tracked separately by the claim ladder

This document declares which Python surfaces downstream users may treat as
supported, which ones are compatibility candidates, and which ones remain
provisional research APIs. A scientific result cannot stabilize an API, and a
stable software contract cannot promote a scientific claim.

## Maturity labels

- **Supported root surface:** intentionally tiny and covered by the package
  versioning policy. At present this is only `spirallens.__version__`.
- **Stable candidate:** framework-neutral functionality whose compatibility
  tests have started, but which has not met the two-independent-consumer rule
  for a stable API.
- **Provisional:** documented and tested, but allowed to change between minor
  pre-1.0 releases with migration notes.
- **Internal:** repository or experiment implementation detail. Import paths,
  call signatures, and persistence behavior are not public contracts.

## Current surface

| Namespace or symbol | Status | Compatibility boundary |
| --- | --- | --- |
| `spirallens.__version__` | supported root surface | single package version |
| `spirallens.core.canonical` | stable candidate | canonical bytes and legacy `instrument_contracts.canonical` compatibility |
| `spirallens.access` | provisional | typed access, value lineage, pre-observation descriptor, and execution-lifecycle contracts |
| `spirallens.referents` | provisional | canonical F0-F4 pointwise definitions and model-free same-object numeric relations; no substrate field |
| `spirallens.instrument_contracts` | provisional | versioned v0.x artifacts plus an explicit lineage-gated numeric payload session |
| `spirallens.contracts`, `loops`, `holonomy`, `topology` | provisional | framework-neutral mathematics; scientific meaning remains artifact-bound |
| `spirallens.synthetic`, `spirallens.graphs` | provisional | model-free generator-family controls plus exact graph/domain fingerprints; `CartesianFourierEstimatorInputs.from_observable_arrays()` is the owner boundary for deriving label-free content IDs; scientific qualification remains artifact-bound |
| `spirallens.qualification` | provisional | frozen model-free D0-D5 protocol and terminal chronology, read-only historical terminal binding, plus a scope-limited D6 decision; deep internal surfaces now also include C1/C2, unpersisted replay-target/attempt-envelope specifications, D7 record/evidence/result joins, a caller-prefix evidence lane, non-authorizing launch-prerequisite inputs, atomic structural terminal persistence, runtime-pin-relative signed external-witness verification, a typed post-start runner handoff, current-HEAD closed-descriptor reopening, a dedicated structural start transaction, and same-call fused verify/start/callback/terminal-attempt mechanics; none is a public export or an official descriptor, target, start/run instance, trusted pin root, admission, seed, exact executor, scientific result, or D7/D8 authority |
| future subject APIs | provisional | no subject execution surface is stabilized or authorized by this table |
| `spirallens.adapters`, capture-side `atlas`, `factors`, `interventions` | provisional/model extra | no framework types may define core artifact schemas |
| CLI handlers, workers, frozen one-experiment runners | internal | CLI is a thin adapter, never the Python API |

The PR #11 post-D6 descriptive plan and value-blind D7 gap matrix are canonical
research artifacts, not Python APIs. They intentionally add no analysis
runner, writer, generic mapping validator, family-admission helper, or
promotion surface. The descriptive artifact is also non-executable until a
committed full-D7-design freeze receipt exists. Reusable analysis primitives
remain extraction candidates until a second independent consumer exists.

The spectral-moment four-case generator and
`spirallens.qualification.confirmation_protocol` foundation are internal
development surfaces. Its builder and strict reader accept only an
authoritative committed-D6 loader receipt, but it deliberately exposes no
full-design freeze, source-closure, admission, lifecycle, execution, result, or
promotion surface. `D7ParentD6Binding` and the foundation are now internal
`v0.2` drafts. They remain unpersisted as standalone/public artifacts, while
C1 preserves their exact canonical historical bodies inside its Level-0
wrapper. Their canonical identity excludes the ephemeral current-loader HEAD
and source-binding digest, while construction still requires and validates the
typed authoritative loader receipt. The prior internal `v0.1` drafts have no
standalone artifacts or migration surface.

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
inventory and seed values, case/stratum membership, graph nonvacuity,
aggregation thresholds, gate definitions, and gate-evidence semantics
therefore remain unverified. Event-stage hashes bind declared structure; they
do not prove that execution occurred or establish producer chronology.

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
publication, including a failure before runner dispatch. The official
producer and exact aggregation remain separately auditable behind the callback
and are not implemented by this runner slice. If a handled ordinary exception
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
`confirmation_fused_start` modules complete roadmap item 20 as mechanics only.
They reopen a committed closed nine-member descriptor at clean current HEAD,
match live canonical `origin/main`, and verify the declared observation
surface: tracked `src/spirallens/**`, `pyproject.toml`, and the required runtime
lock; installed distribution names/versions; interpreter executable bytes;
producer source/code identity; selected process-envelope fields; physical
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
their inventory and persisted start bindings; no official descriptor instance
exists yet. Repository-HEAD, canonical-origin, source-tree, dependency-set,
callable, and process observation digests are preserved, not recomputed or
independently reauthenticated by structural reload. Terminal lineage binds the
evidence bytes rather than those live facts. The
fused call performs at most one terminal-publication attempt. Hard exit or
`BaseException`, post-start drift, unproved start-parent fsync, or success/
failure publication error can leave a visible start with no terminal. The
item-19 external finalizer remains typed to its evidence-only prefix and does
not accept this authoritative-start transaction, so authoritative-start-
compatible external-abort integration remains open.

The replay contracts and attempt records are specifications and types, not
official replay-target or authoritative attempt-envelope instances. The local
prefix writer embeds those supplied primary types beneath a distinct
false-authority envelope; it exposes no official seed supplier and grants no
lifecycle or execution authority. Isolated replay is rejected before
persistence because passed-primary consumption cannot yet be established. The seed-supply contract requires
final-code source/runtime closure and reviewed family admission before a
future exclusive seed-supply claim and single supplier invocation. It then
requires atomic full-design/target publication and a committed freeze receipt
before launch intent. A claim left without an atomically published target is
terminally aborted and non-retryable; absence of the target does not prove the
supplier was invoked. The target-local claim ceiling stays exactly Level 0
and its authority vector stays all-false. C2 closes only the historical C1
source set and does not cover these modules or later persistence, terminal,
or runner code. A later exact closure of the then-current execution source and
runtime is required after those surfaces are final.

Target, authorization, start, and result fields are joined by a closed table
of canonical byte equalities. Neither the evidence-only prefix lane nor the
new structural-start lane establishes `started_unresolved` from bytes alone.
A future official reauthentication must bind the exact authority evidence and
durable start before assigning that lifecycle interpretation. The current
evidence-only external finalizer cannot perform that rejoin for the item-20
start type.

Family admission, full-design freeze, official seeds, authoritative lifecycle,
execution, official result/failure publication, scientific eligibility, D7,
and D8 remain absent or `not_run`. Structural terminal publication is now a
deep-internal mechanics surface only. The next sequence is deliberately
operational rather than token-based:

1. retain the completed terminal-transaction, external-witness, and typed
   runner mechanics as non-authorizing and non-scientific;
2. retain the completed deep-internal fused transition mechanics without an
   official descriptor or invocation. They accept only a raw current-HEAD
   descriptor and zero-argument producer, match the declared source/runtime,
   callable/process, physical, and absence surfaces, publish one no-replace
   start, require its parent fsync to be proved, repeat those observations, and
   consume private ownership before callback; they emit no reusable
   authorization token;
3. for item 21, add and freeze `requirements-d7-runtime-lock.txt`, name the
   exact official producer and aggregation, issue the exact-current source and
   runtime artifacts, and complete reviewed family admission plus seed-free
   readiness;
4. for items 22-23, claim and invoke seed supply once, publish the exact target
   and full design, commit the freeze, persist launch intent, and execute the
   already separated descriptive result without changing D7 design bytes;
5. before item 24, create and commit the closed nine-member descriptor and
   pass strict verification-evidence replay/rejoin, temporary Git/runtime
   end-to-end validation, and authoritative-start-compatible external-abort
   integration; and
6. make item 24 the first official fused invocation, requiring an exact
   terminal outcome and complete isolated byte replay.

The directly constructible records remain insufficient throughout this
sequence. Evidence envelopes cannot be promoted in place.
The fused module is also deep internal and has an empty `__all__`. No official
descriptor, fixed runtime lock, exact-current closure, admission/readiness,
target/freeze/intent instance, start, terminal, or run has been created.
Canonical-origin equality is a scoped live Git-transport trust rule, not
signed trust-root provenance or hostile-local-operator resistance.
Committed C2 closes only the declared historical Git source set; it does not
execute historical code or attest Python/native runtime, transitive
dependencies, in-process identity, hostile-local-mutation resistance, or
current compatibility.

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

## Promotion rule

A provisional symbol becomes stable only after at least two independent
consumers, full compatibility tests, user-facing documentation, and an
explicit reviewed promotion decision. Negative or inconclusive scientific
results do not block promotion of a generally useful software primitive.
