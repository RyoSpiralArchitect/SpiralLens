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
| `spirallens.qualification` | provisional | frozen model-free D0-D5 protocol and terminal chronology, read-only historical terminal binding, plus a scope-limited D6 decision; deep internal surfaces now include a persisted Level-0 C1 seed-free source-set candidate, its committed receipt-only C2 historical-Git-source-set closure, canonical unpersisted replay-target/attempt-envelope contract specifications, D7 attempt/evidence/result schemas and joins, a no-replace caller-supplied primary-prefix evidence lane, and a non-authorizing structural candidate for a concrete subset of later launch-authority prerequisites; none is a public export, authoritative target, admission, seed, execution capability, terminal publication, or D7/D8 authority |
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

The physical input binds the exact attempt key, normalized store/lane/output/
terminal paths, positive store/lane/parent device/inode coordinates, and the
lane-parent-to-store relationship. It excludes persistence-reserved evidence,
attempt-envelope, and chronology paths, and rejects double-slash aliases,
embedded NUL, and overlong declared paths. The artifact-binding API has no raw
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
identity record describes normalized paths, the exact attempt key, and
declared device/inode coordinates; it is not a live filesystem observation,
reservation, or exclusive claim. “Complete” seed registries mean complete
relative to the explicitly bound registry sources and counts in this
candidate, not proof that an authoritative supplier, parent history, or
unopened-seed boundary has been verified. The typed invocation is likewise a
caller-claimed structural input, not evidence that a supplier ran. No
reusable capability is emitted.

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
of canonical byte equalities. In the future authoritative lane, a
verifier-established visible start without terminal remains
`started_unresolved`; it blocks retry, replay, and D8 until a later append-only
finalization binds external abort evidence. The present evidence-only lane
cannot establish that state.

Family admission, full-design freeze, official seeds, authoritative lifecycle,
execution, result/failure publication, terminal publication, D7, and D8 remain
absent or `not_run`. The next sequence is deliberately operational rather
than token-based:

1. finish terminal-transaction, external-witness, and runner mechanics without
   invoking the supplier or performing an official run;
2. implement one fused verify-and-exclusive-start operation that reopens and
   verifies the authoritative inputs, reobserves physical identity and
   absence, and transitions directly into the exclusive start; it must emit no
   reusable serialized or caller-returnable authorization token;
3. only after those final code surfaces exist, issue exact current
   execution-source/runtime closure and reviewed family admission;
4. claim seed supply, invoke the supplier once, publish the exact target and
   full design, commit the freeze, and only then persist launch intent; and
5. invoke the fused start operation.

The directly constructible records remain insufficient throughout this
sequence. Evidence envelopes cannot be promoted in place.
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
