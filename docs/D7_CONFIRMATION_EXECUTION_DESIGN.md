# D7 Confirmation Execution Design

Status: `c1_seed_free_source_set_candidate_recorded`,
`historical_structural_rebinding_proposal_preserved`,
`successor_rebinding_review_contract_encoded`,
`c2_declared_historical_git_source_set_closed`,
`replay_target_contract_spec_defined`,
`attempt_envelope_contract_spec_defined`,
`launch_authority_input_schema_candidate_defined`,
`fused_launch_descriptor_schema_defined`,
`authoritative_start_transaction_schema_defined`,
`strict_verification_evidence_replay_rejoin_implemented_not_officially_exercised`,
`fused_verify_and_exclusive_start_mechanics_implemented_not_officially_invoked`,
`d7_runtime_lock_exact_tracked`,
`fixed_official_zero_argument_producer_implemented_deep_internal`,
`exact_full_inventory_aggregation_and_full_design_builders_implemented_deep_internal`,
`installed_inventory_exact_equality_enforced`,
`item21_three_artifact_chain_fixed_in_source_commit`,
`item21_source_commit_artifacts_absent`,
`item21_final_corrected_tip_artifacts_tracked_and_strictly_reloaded`,
`item21_complete_at_final_corrected_tip`,
`item22_seed_supply_transaction_instance_absent`,
`item22_live_readiness_blocked_pending_reviewed_reanchor`,
`canonical_d7_launch_descriptor_absent`,
`official_authoritative_start_instance_absent`, `official_d7_run_absent`,
`not_frozen`, `seed_bearing_target_not_admitted`, `not_run`.

This document is the single detailed anchor for the spectral-moment D7
execution topology added after the PR #12 construction foundation. It records
what is now implemented, what the implementation revealed about the D6 v0.1
admission contract, and which obligations still block a claim-bearing
confirmation.

The foundation and execution design remain unpersisted as standalone/public
draft artifacts. C1 now preserves their exact canonical `v0.2` historical
bodies inside one Level-0 wrapper. Those schemas supersede the earlier
internal `v0.1` drafts; there is no standalone `v0.1` artifact to migrate. The
version change removes validation-time current-loader HEAD and source-surface
digests from canonical D7 identity so that an unchanged parent decision and
unchanged design produce commit-stable bytes. Ordinary or novel construction
still requires the authoritative typed D6 loader receipt and validates that
receipt before projecting its stable historical identity.

PR26 adds one private, recorded-C1-only archival reconstruction route for the
fixed producer. It first verifies pinned C1/C2, loads the exact parent protocol,
reconstructs the typed design from the C1-embedded binding, and requires
whole-document equality with the design recorded in C1. It is not a general
alternate construction path or a historical reinterpretation of D6 or C1, and
it accepts no caller-authored design.

## 1. Scope

The new internal design closes the execution topology before any official
confirmation seed is selected:

- two abstract confirmation seed slots;
- the four D6-required joint core/loop semantics;
- boundary, state-geometry-warp, and structured-observation-perturbation
  factors;
- the exact three field-estimation graphs A;
- the exact three cycle-construction graphs B;
- primary-boundary and off-core loop roles;
- the current development field estimator, blind core kernel, and continuous
  sampled-loop kernel; and
- the same `GraphInput` and A-bound field-estimate join between core and loop
  predictions.

The separate internal `confirmation_rebinding` contract types and strictly
reloads the historical proposed successor-only cells/stress fulfillment rule.
C1 now preserves that proposal and records a separate successor review
contract, declared static-bounded construction review, D7 registry,
aggregation application, and source-set manifest in one canonical candidate.
C1 cannot attest its own future commit, but the separate committed C2 now
verifies its declared historical Git source set. Neither artifact implements
repository-review attestation, D7 admission, full-design freeze, official seed
supplier, authoritative lifecycle, terminal writer, D8 replay, model
access, or scientific promotion. Runtime and transitive dependency closure
are outside the C2 receipt's scope and remain unattested.

The internal `confirmation_replay_contracts` module now adds two canonical,
unpersisted specifications after revalidating that pinned C1/C2 history:
`D7ReplayTargetContractSpec`
(`spirallens.d7-replay-target-contract-spec.v0.1`) defines the future immutable
seed-bearing target independently of attempt-local state, and
`D7AttemptEnvelopeContractSpec`
(`spirallens.d7-attempt-envelope-contract-spec.v0.1`) defines one future
attempt as append-only stage records. These are schema contracts, not
instances. `LoadedD7ReplayAttemptContractFoundation` remains in memory. A
separate deep-internal persistence-only writer can record and strictly reload
caller-supplied primary declaration-through-start records only beneath an
immutable false-authority store scope and predecessor-chained evidence
envelopes. Raw lifecycle bytes are not top-level persisted stages, in-place
promotion is forbidden, and isolated replay is rejected before persistence.
The writer cannot create the replay target, authorize or observe execution,
establish `started_unresolved`, or publish a terminal. D7/D8 remain `not_run`,
and every authority field remains false. Both specifications record
`status=schema-defined-instance-absent`.
An interrupted pre-rename staging file blocks reload/retry and is never a
lifecycle stage. Writers must first quiesce; only a confirmed orphan may enter
separate offline recovery.

PR #23 adds a third, deliberately non-authorizing layer:
`confirmation_attempt_authority` gives canonical shape to a concrete subset of
inputs that a later operational launch boundary must obtain and verify. The
bundle's replay-target record uses dedicated caller-claimed admission,
exact-full-design, and exact-source/runtime candidate leaf types. Each positive
leaf field is explicitly a caller claim and every leaf and nested artifact
binding records `identity_authenticated=false`. The admission candidate keeps
the complete construction-review and admission-spec binding identities rather
than digest-only projections. Typed exclusive-supply-claim
and single-supplier-invocation records causally join the supplier, development
and parent registries, readiness, caller-alleged admission and source/runtime
receipt bindings, official inventory, and atomic
inventory/full-design/target publication. The corresponding claim,
invocation, chronology, inventory-output, and atomic-publication verification
fields all remain false; no supplier invocation is performed.

The physical input fixes the `primary-confirmation` role and derives the exact
attempt key from the canonical replay-target digest with the existing attempt
record function. It binds normalized store/lane/output/terminal paths,
positive store/lane/parent device/inode coordinates, and the
lane-parent-to-store relationship while requiring distinct store and lane
identities. It excludes the persistence-reserved lane, evidence directory,
attempt-envelope leaves, and chronology leaf by lexical and known declared
physical identity. The artifact-binding surface intentionally has no raw
`from_bytes` factory. Double-slash aliases, embedded NUL, and overlong declared
paths are rejected before the persistence boundary. The strict loader applies
the input-size cap before hashing, verifies the expected bundle digest before
parsing, translates malformed, deeply nested, and oversized-numeric JSON
parser failures into `D7AuthorityInputError`, and checks only
canonical shape and declared joins. It neither authenticates the issuers nor
observes the filesystem, process, runtime, Git state, seed supplier, or
chronology.

Canonical serialization does not confer authority. A caller can construct the
records and their digests, so neither the bundle nor any serialized
“capability” or token may be accepted as permission to start. The loaded
candidate permanently leaves source/runtime verification, admission,
claim/invocation/publication verification, freeze verification, path absence,
physical reobservation, exclusive start, execution, and scientific authority
false. “Complete registry” below means
complete with respect to its explicitly bound registry source and declared
cardinality; it is not an independent proof that no historical or development
seed was omitted.

## 2. Exact repeated-measures inventory

The canonical seed-free factory uses seed slots rather than numeric seed
values:

| Grain | Exact count |
| --- | ---: |
| Primary units | `2 × 4 × 2 × 2 × 2 = 64` |
| Core cells | `64 × 3 A = 192` |
| Loop cells | `64 × 3 A × 3 B × 2 roles = 1,152` |
| Total event lanes | `1,344` |
| Required stress strata | `6`, with `32` primary units each |
| D2 units after boundary collapse | `32` |
| D4/D5 scientific execution units | `64` |
| Non-prerequisite primary denominator | `48` |
| Prerequisite-failure primary units | `16` |

Graph cells, loop roles, and stress variants are repeated measures. They are
not independent samples. The two seed slots are blocks; this design does not
claim that their statistical independence has been proved.

## 3. Full parent-design reconstruction

The D6 decision stores hashes, not enough typed bytes to reconstruct all
runtime choices. The ordinary or novel D7 builder therefore requires both:

1. an authoritative `LoadedScopeLimitedD6Decision`; and
2. the strict `LoadedQualificationProtocol` whose canonical identity is bound
   by that decision.

It reconstructs the five full design bodies with the same body builder used by
the D6 sealer and verifies every hash:

| Parent body | SHA-256 |
| --- | --- |
| D6 decision | `c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07` |
| D6 admission | `2e4aa2a272a38ed68b61f612d8a3a261cc6376f3d9a8097f5dce701a2c3f5aa4` |
| Protocol | `9908bb83bb5ff5642416aa09d9e468e0a9499185cec9305e69a54143f2578bd1` |
| Graph axes | `71e7e1a128d4bfb4473b1b809fc16dde58971d38ab0d5b3b1ec8794150e05247` |
| Required cells | `4d243f9ba2c0029480bd98e002914f5a100aa93ac981aae5517142eee0dae7ff` |
| Required stress strata | `cabe0827e0dc74f4d118fa3453f6e887eec553a7005fcba3c30e6fea976b982f` |
| Thresholds | `17b4fc193c4d02ab5526dc2f4502832701480ef01deaf3acd01a6e06458cf271` |
| Aggregation | `300c3b63f3897fe808b418369d2dbeac76df41160b456f6e5feec6d3995dcef3` |

The authoritative D6 loader has already loaded and verified the historical
terminal result, manifest, and consumption companions. Their raw bytes are not
direct arguments to, reread by, or retained in the seed-free design. The
`v0.2` `D7ParentD6Binding`, foundation, and execution-design bytes bind the
stable historical decision and admission identities but deliberately exclude
the ephemeral current-loader HEAD and source-binding digest. That ordinary or
novel builder still requires `LoadedScopeLimitedD6Decision` and reruns its typed
receipt validation; the current-loader surface is therefore a validation-time
prerequisite, not a component of canonical D7 identity. This keeps unchanged D7
design bytes stable across later clean descendant commits without weakening the
authoritative loader boundary. The PR26 archival route described above is the
recorded-C1-only exception; it does not weaken or replace this construction
contract.

## 4. D6 v0.1 manifest incompatibility

Implementation exposed a contract problem that the hash-only foundation could
not resolve.

The D6 required-cells body contains:

- numeric selection seeds;
- selection control identifiers;
- seed-bearing primary-unit identifiers; and
- seed-bearing core and loop cell identifiers.

The D6 required-stress body also contains the selection primary-unit
identifiers inside each stratum membership. A new-seed, construction-diverse
D7 inventory therefore cannot be byte-identical to either parent body without
reusing selection identities and weakening evidence disjointness.

The design records two separate facts:

- a typed structural projection from parent seed ordinal, control semantics,
  stress tuple, A graph, B graph, and loop role is exactly equal to the D7
  seed-slot projection; and
- exact parent cells/stress hash satisfaction remains `false`.

Structural equality is not silently reinterpreted as D6 v0.1 admission. The
internal `spirallens.d6-d7-structural-rebinding-amendment.v0.1` contract now
encodes the narrower proposed successor-only rule:

- graph-axis and threshold bodies must retain exact byte identity;
- cells and stress bodies must have different successor identities;
- their typed structural-projection digests must match exactly;
- parent selection identities may not be reused; and
- the mapping grants neither admission nor execution authority.

Its factory reconstructs the seed-free design from the authoritative D6
receipt and strict parent protocol. Its strict reader requires the expected
SHA-256, canonical JSON, bounded bytes, and whole-document equality with that
reconstruction. The encoded rule remains unreviewed, unpublished, and
ineffective for admission. This is an implemented internal type and reader,
not a published amendment artifact.

The historical D6 v0.1 decision and admission bytes remain unchanged. Their
literal cells/stress requirements are still unsatisfied, so
`d6_admission_spec_satisfied=false`. The successor rule supplies no retroactive
pass and no migration of D6 history.

The parent aggregation body also names a `selection-seed-block`, and the
selection implementation registry cannot become the D7 registry because the
generator construction must differ. Their D7 application remains a separate
review obligation.

## 5. Stress translation

Every stress value is explicit. The generator spec has no nominal defaults.

| Axis | Nominal | Stressed | Translation |
| --- | ---: | ---: | --- |
| Boundary | central `(2,2)-(4,4)` | wide `(1,1)-(5,5)` | selects matched cycle support; does not change generator arrays |
| State geometry | `0.0` | `0.1` | `q_w = q + w sin(πq)/π`; changes states only |
| Observation perturbation | `0.0` | `0.01` | D6 nuisance operator `a cos(√2 α + phase(seed,row))`; changes fit/evaluation values only |

The prerequisite-failure unit remains in its requested perturbation stratum,
but its effective perturbation scale is zero. Both requested and effective
values, plus the suppression flag, are retained.

The spectral state vector is normalized by
`1 / sqrt(ambient_dimension) = 1 / sqrt(12)`. This is a construction rule, not
a learned threshold. Without normalization the locked radius `0.48` graph has
no edges. With the declared rule, the seed-free maximum axis-adjacent
distances remain below `0.48` under both warp levels with an explicit margin.
The full development inventory additionally exercises actual graph and cycle
construction rather than treating that distance check as sufficient.

## 6. Prediction path and oracle boundary

The implemented development path is:

```text
explicit stress spec
  -> label-free prepared estimator inputs
  -> GraphInput
  -> exact 3A / 3B matched-support executions
  -> current development Cartesian first-harmonic field estimator
  -> blind core inputs and sealed core predictions
  -> blind loop inputs and sealed continuous sampled-phase predictions
```

The blind core and loop kernels have no oracle parameter. The preparation API
does not construct an oracle-truth record, and no oracle record is supplied to
graph, field, core, or loop kernels. The orchestration layer still carries
case and unit identity in order to select a synthetic control and is not
claimed to be label-blind. The generator necessarily constructs the latent
signal used to synthesize observations; the narrower and testable statement is
that no oracle-truth record reaches the blind prediction kernels.

The field estimator remains the current development implementation. C1 binds
its D7-specific implementation registry and aggregation application and
declares the Git source set. The separate committed C2 receipt verifies that
declared historical Git-tree source set; it does not execute historical code
or attest Python/native runtime, transitive dependencies, in-process identity,
hostile-local-mutation resistance, or current compatibility. Admission and
freeze remain separate later contracts.

The path stops before scoring and aggregation. It does not call D4/D5 collapse,
create a `GateResult`, create a `QualificationResult`, or publish a terminal.

## 7. Development-only conformance

Permanently excluded development seeds `9001` and `9002` were run through the
complete inventory:

- `64` primary predictions;
- `192` sealed core predictions;
- `1,152` sealed loop predictions;
- zero unmatched cycle representatives; and
- the expected development prediction-class distribution for all four
  controls.

This is implementation conformance only. The receipt is explicitly
claim-ineligible, produces no D7 result, and cannot be substituted for a
future unopened-seed confirmation.

## 8. Freeze chronology

The official seed values remain absent. Both deliberately separated
source-only commits are now recorded:

1. **C1 — stable design and declared source set, recorded:** one canonical
   candidate binds the seed-free design, historical proposal plus successor
   review contract, declared static-bounded construction review, complete
   Python source manifest, D7 implementation registry, and aggregation
   application. C1 contains no self-referential commit or source-closure
   receipt; `source_closure_verified=false`.
2. **C2 — declared historical Git source-set closure receipt, recorded:** the
   choice-free receipt is the unique receipt-only child of exact clean
   post-merge C1 `e58a8169b41be688628ab7dda583e68088d3affc`; its
   introduction commit is `2f4e715a951211af8ca0ca4f6b2f7473134bf92b`.
   The committed loader verifies Git ancestry and the exact declared C1 source
   blobs. It does not execute historical code or attest Python/native runtime,
   transitive dependencies, in-process identity, hostile-local-mutation
   resistance, or current compatibility.
3. **Replay/attempt contract specifications, implemented but unpersisted:**
   `load_d7_replay_attempt_contract_foundation()` internally reruns the pinned
   committed-C2 verifier and choice-freely reconstructs both canonical specs.
   It does not accept a caller-provided source-closure wrapper or expected
   digest. The replay-target spec remains outcome- and attempt-path-free. The
   attempt-envelope spec binds the target contract but creates no target or
   attempt instance.

The attempt contract rejects a mutable nullable envelope. Its future records
are append-only and ordered: attempt declaration, launch authorization,
exclusive attempt claim, execution start, exactly one scientific result or
failed-attempt record, terminal manifest, and terminal consumption. Attempt
records bind but may not redefine the concrete target's seed inventory,
thresholds, graph/cycle inventory, aggregation, result schema, construction
family, or identity.

The separate seed-supply chronology is also closed before values exist: the
lifecycle/result/terminal/witness/runner and fused verify-and-exclusive-start
mechanics are now implemented without an official execution. The fused path
accepts only a raw current-HEAD descriptor and zero-argument producer, derives
live canonical-origin facts and matches the declared source/runtime,
callable/process, physical, and absence observation surfaces inside the call,
publishes a no-replace structural start, requires the start-parent fsync to be
proved, repeats those observations, and consumes private ownership before
callback without emitting a reusable token. PR26 now completes the code-side
portion of item 21: it tracks the exact `requirements-d7-runtime-lock.txt`,
fixes the deep-internal zero-argument official producer and exact
full-inventory, aggregation, and full-design builders, and enforces exact
equality of the complete installed distribution name/version inventory. It does
not itself issue positive authority. The corrected item-21 source anchor defines three
separate tracked item-21 artifacts in fixed order: exact source/runtime receipt,
seed-free readiness, then scoped reviewed successor-family admission. It issues
none of them and freezes all item-21 documentation. The source/runtime receipt is
the only addition in its direct-child commit; readiness is the only addition in
the next direct child; and admission is the only addition in the next direct
child. A merge, intervening change, combined artifact or documentation commit,
or embedded future-child identity fails this receipt-only chronology. Item 21
is partial at the source commit. The three artifact-only children strictly
reload/rejoin the chain and complete item 21 at the final corrected tip. The later
historical loader reconstructs source and lock bytes from that source commit,
while the live verifier rejects any later execution-source or runtime change.

That chronology check is graph-sensitive, not endpoint-only. The loader scans
full HEAD-reachable path history, derives exactly one direct-child introduction,
and permits later path events only on its descendant lineage with the identical
`100644` blob. A merged-away mutation, deletion/re-addition, or parallel
introduction fails, while a preserving merge with an artifact-absent unrelated
parent remains valid. Historical reconstruction enforces the issuer's
per-member and aggregate source caps. Live source verification checks every
bounded source-path event on the anchor-to-HEAD descendant ancestry, together
with both endpoints, so an edit followed by a revert or merge resolution still
requires a reviewed re-anchor.
The deep-internal item-22 operation is repository-root-only and accepts no caller supplier, seed, claim key, layout, or authority object. It strictly reloads the historical item-21 chain and reviewed exact-current re-anchor, then rechecks live state, durably claims, calls the fixed honest-local OS-CSPRNG supplier once, excludes both frozen seed registries, and atomically publishes two unique sorted nonnegative signed-int64 seeds with the closed target.
Import, loading, and tests create no official transaction artifact.

The fixed layout retains
`item22-current-source-runtime-reanchor.json` outside the
`item22-seed-supply/` transaction root. That root contains
`exclusive-seed-supply-claim.json` and `seed-supply-abort.json` leaves, the
atomic `published-target/` directory, and, only after complete publication, the
later `full-design-freeze.json` leaf. The exact `published-target/` members are
`official-seed-inventory.json`, `full-inventory.json`, `full-design.json`,
`replay-target.json`, `single-supplier-invocation.json`, and
`transaction-manifest.json`. Launch intent remains the existing external
`launch.json` and is not a transaction-root member.
All six publication members must be canonical regular unaliased files;
unknown members, partial visibility, replacement, and publication retry are
forbidden. The manifest binds the other five members, never itself. This durable
six-member layout is distinct from the chronology publication subject set of
official seed inventory, full design, and replay target. The exact internal
digest graph also rejoins full inventory to seed inventory, full design to both
inventories, replay target to those same exact member bytes, and the invocation
receipt to the same seed inventory. Each chronology-subject binding must equal
its published member; merely hashing six mutually inconsistent canonical files
into the manifest does not satisfy the contract.

The state names are `preclaim`,
`claim-present-publication-absent-nonretryable`,
`seed-supply-aborted-established`, `publication-complete-unfrozen`,
`full-design-frozen`, and `launch-intent-present`. The live pre-call claim
interval is immediately non-retryable and permits no restarted supplier entry.
It becomes a semantic abort only when that operation ends without publication.
The distinct durable `seed-supply-aborted-established` state
requires an evidence receipt at `seed-supply-abort.json`; target absence alone
does not establish it or prove that the supplier was never invoked. This later
item-22 specification explicitly refines the historical replay-target field
`seed_supply_chronology_contract.claim_without_target_is_seed_supply_aborted`
without mutating its canonical bytes (SHA-256
`d8387e29601a85df54513669919c591964b8fc99f3c8ec1126d527a854763ffa`, 6,550
bytes). The older blanket flag grants no future behavior; operational code must
use this specification's active/ended-origin and semantic/durable-evidence
split. The fixed supplier identity is
`d7-item22-honest-local-os-csprng-v0-1`; its declared entropy API is
`secrets.randbits(63)` and it makes no cryptographic unseen-value proof. The
`spirallens.d7-item22-exclusive-seed-supply-claim-key.v0.1` scheme uses SHA-256
over canonical JSON with domain separator
`spirallens:d7:item22:exclusive-seed-supply-claim:v0.1`. Its ordered inputs bind
the fixed claim path, historical item-21 receipt/readiness/admission triple,
reviewed re-anchor, supplier identity, and development and parent exclusion
registries. The preimage is one exact-key top-level object; every dynamic
artifact uses the exact five-field authority-artifact identity projection.
Alternate arrays, role-keyed objects, extra fields, authority/provenance flags,
and caller-supplied key values are excluded.

The closed transition graph requires the fixed supplier identity, derived key,
internally live-verified re-anchor, and durable claim before supplier entry.
From the claim-present state, only the same originating operation
may atomically publish the target or durably record abort; a restarted entrant
cannot invoke the supplier. Abort-established is terminal. Failure to persist
abort evidence leaves the claim-present/non-retryable state, while failure after
publication leaves `publication-complete-unfrozen`, is not seed-supply abort,
and authorizes no supplier retry. The exclusive reservation is scoped to
repository-local, cross-process operation on the same filesystem. It proves no
cross-host or distributed-filesystem exclusivity and no supplier-global
idempotency; external coordination remains a future requirement.
The durable pre-call claim is necessarily observable before supplier entry, but
that interval is not a restart-resumable waiting state and persisted claim bytes
alone authorize no continuation. The operation fsyncs the claim
file and parent before the supplier call. Because the seed-supply namespace is
initially absent, its owning experiment directory must also be fsynced after
namespace creation and before the claim. Every staged target member and the
staging directory must be fsynced before no-replace rename, the publication
parent before success, and abort evidence and its parent before returning abort
established. These are required operations, not proof of power-loss survival or
authenticated filesystem semantics. Crash recovery uses one mutually exclusive
presence table in `(claim, target, abort, freeze, launch)` order: `00000` is
preclaim, `10000` claim-present/nonretryable, `10100` abort-established,
`11000` publication-complete/unfrozen, `11010` full-design-frozen, and `11011`
launch-intent-present. A present bit means the artifact passes canonical strict
reload. Every unlisted combination—including target plus abort, downstream
evidence without claim, or any invalid/partial artifact—is a fail-closed
contract error. Recovery applies no precedence and permits no supplier retry.

The item-21 artifact chain remains historically valid, but live readiness is blocked until all pre-claim source is final and the separate reviewed re-anchor is committed. The operation re-verifies immediately before its no-replace claim and accepts no cached readiness snapshot.
This branch contains no official claim, supplier invocation, seed, target, freeze, launch descriptor, or execution. Freeze and the closed descriptor remain distinct later steps; item 24 remains the first official fused invocation.

The evidence-only local persistence writer performs path-coordinate
reobservation before exposing a caller-supplied start record, but it does not
verify the target, execution identity, source/runtime authority, or execution.
Its terminal-absence observation is
`caller_supplied_start_record_present_terminal_absent`, not
`started_unresolved`. The separate item-20 fused mechanic now reopens a closed
descriptor, rejoins exact target/authorization/claim inputs, matches the
declared live observation surfaces, and publishes a dedicated structural start
before its second-pass checks and possible producer entry. Its strict loader
still reports `authority_authenticated=false`, `authority_granted=false`, and
`started_unresolved_established=false`; a visible start directory is not a
reusable authority capability. A scientific result payload is
attempt-independent but still binds the exact
target, full inventory, aggregation, and result schema. The isolated-replay
role is derived from an already persisted passed-primary terminal and
consumption receipt, not from a caller label. Result or failed-attempt,
manifest, and consumption records are staged and exposed only as one atomic
no-replace terminal transaction.

That terminal transaction is now implemented as a deep-internal structural
mechanic. It writes every bounded canonical member into one same-parent private
directory, fsyncs files and the staging directory, revalidates the persisted
prefix and complete file identities, and exposes the directory with a native
descriptor-relative no-replace rename before strict reload. Competing
attempt-scoped staging entries, destination races, symlink/hardlink/FIFO or
unknown-member substitution, descriptor/identity drift, and uncertain cleanup
fail closed. A final parent-directory fsync failure is retained explicitly as
durability unproved rather than turned into success. None of those structural
facts authenticate the caller-supplied prefix or prove execution.

The post-start runner mechanic is also implemented behind a private,
nonserializable ownership handoff. The runner itself supplies no issuer; the
fused operation is the sole deep-internal issuer and constructs and consumes
ownership only after durable start publication, strict reload, and unchanged
second-pass observations. It is primary-confirmation-only and accepts no seed,
supplier, or independent start record. A zero-argument producer callback must
return all six components plus the outer payload; the runner validates the
complete bundle and requires its replay-target/full-inventory/aggregation/
result-schema projection to match ownership before preparing a typed terminal.
The runner remains generic; a separate PR26 deep-internal surface fixes the
zero-argument official producer and exact full-inventory, aggregation, and
full-design builders behind this callback boundary. Their implementation is not
an official invocation or artifact publication.
The shared PR26 producer/validator path also mechanically rederives the exact
six stratum memberships from canonical joined-primary stress assignments and
reconstructs the exact four-gate manifest, definitions, states, reasons,
evidence digests, and outer-result reasons. This closes code-side structural
consistency only. It is not authority, invocation, execution evidence,
publication, or a D7 run.
Every exit after ownership construction atomically invalidates callback-entry
and terminal-publication authority, including failure before runner dispatch.
Ordinary exceptions retain their identity and may trigger a failed-terminal
publication attempt before being re-raised. A visible failed terminal whose
final parent fsync is unproved causes a best-effort attempt to attach its
terminal identity and durability warning to that original exception; hard
crash or `BaseException` is not reclassified as an abort.

The target, authorization, start, and scientific payload fields are related by
an explicit closed table of canonical byte-equality constraints. Independently
well-formed digests are insufficient. A visible structural start without a
terminal blocks retry, replay, and D8, but the bytes alone do not establish
the named `started_unresolved` state. Only a future official reauthentication
of the exact authority evidence and durable start could assign that lifecycle
interpretation. A hard crash cannot publish an in-process failure record.

The external-abort mechanics now bind that path to a canonical Ed25519
observer-plus-verifier envelope in the closed failed-terminal inventory. The
integrated operation verifies the two signatures against explicit runtime
pins after atomically consuming both callback entry and prepared-terminal
publication. It performs one fixed live revalidation of the exact prefix,
terminal path, parent identity, and absence state, derives the
finalization/outcome/manifest/consumption chain internally, consumes the
witness value, publishes once, and strictly reloads. Reload can independently
reauthenticate the exact visible
terminal to the supplied pins. This is signature authentication relative to
those pins only: pin provenance, official trust-root authority, wall-clock
freshness, authoritative-start issuance, execution observation, scientific
eligibility, retry/replay authority, D7, and D8 remain false.
Structural reload preserves, but does not recompute or independently
reauthenticate, the repository-HEAD, canonical-origin, source-tree,
dependency-set, callable, and process observation digests. Terminal lineage
binds the exact evidence bytes only.

The future target itself remains exactly Level 0 and carries the closed
all-false local authority vector. Admission, launch, result, and D8 authority
are established only by later exact typed joins; they cannot be nested into or
inferred from the target record.

Now that the lifecycle, result, failed-attempt, terminal, runner, and fused
mechanics are final, the corrected source anchor fixes the formerly open
item-21 boundary as the strict
three-artifact chain above. Its source commit is only the anchor and has none of
the artifacts. The three tracked, receipt-only direct-child commits add and
strictly reload/rejoin exact source/runtime receipt, seed-free readiness, and
scoped reviewed successor-family admission in that order, completing item 21
at the final corrected tip. C2 cannot do that: it closes only the historical C1 Git
source set and covers none of these later surfaces.
Existing caller-constructible admission, readiness, and source/runtime records
keep their false verification state and are not promoted into any of the three
artifacts. A later seed-bearing target must
bind that new receipt, exactly two unique, sorted, nonnegative signed-int64
seeds, rejection of every development and parent selection seed, the
`confirmation-seed-slot-00` and `confirmation-seed-slot-01` mapping, the
admission receipt, and the complete frozen design. Seed values may be public
after freeze; the controlled fact is chronology, not permanent secrecy.

Terminal design must not manufacture a placeholder result merely to reserve
an output shape. The two contract specifications now type the separation, but
the actual immutable replay target and attempt envelope still do not exist.

## 9. Current boundary and next PR sequence

Committed C2 closes the declared historical Git source set, the two canonical
contract specifications fix target/envelope separation, and the
caller-supplied prefix evidence lane carries a byte-level false-authority
boundary. PR #23 now records the next prerequisite as a non-authorizing
structural bundle. Dedicated caller-claimed target admission, full-design, and
source/runtime leaves remain unauthenticated. The typed exclusive claim and
single invocation causally connect supplier, registries, readiness,
caller-alleged receipts, official inventory, and atomic publication, while the
physical input binds the primary-role target-derived attempt key and positive,
distinct store/lane identities
and excludes persistence-reserved paths. The loader has no raw artifact
`from_bytes` path; it applies a size cap, verifies the digest before parsing,
and translates canonical parse errors. These requirements are concrete enough
to test without claiming that the records came from trusted issuers. This is a
newly exposed prerequisite, not an amendment to the meaning or historical
status of C1, C2, D6, or earlier persisted attempts.

The item-22 module now implements the closed six-state observer and the one-shot
transaction through abort or `publication-complete-unfrozen`, without creating an official instance on this branch. The historical item-21 chain
still reloads, while exact-current live readiness remains blocked until the
final reviewed re-anchor is published separately.

Roadmap items 19 and 20 are now mechanics-complete. The structural terminal, typed
primary-only runner handoff, two-signature witness inventory member, and
integrated pin-relative external-abort publish/reload path exist only as
deep-internal surfaces. The fused path is the ownership issuer only within one
exact same-call transition rooted in a live canonical `origin/main`
observation. It adds a closed Git inventory, declared source/runtime plus
callable/process observation matching, a repository-disjoint physical store
proven from descriptor-relative device/inode ancestry rather than path
spelling, two-pass absence checks, a closed structurally named
authoritative-start transaction, and at most one callback. Here
“source/runtime” is only the declared surface:
tracked `src/spirallens/**`, `pyproject.toml`, the required runtime lock, exact
equality of the complete installed distribution name/version inventory,
interpreter executable bytes, producer source/code identity, and selected
process-envelope fields. Installed package
files, loaded native libraries, mutable module globals, callable defaults or
closures, unrecorded environment state, model state, and data state are not
closed. The structural start loader alone grants no
authority and does not establish `started_unresolved`; hard exit, unproved
start-parent durability, post-start drift, or success/failure terminal
publication error may leave those start bytes visible without a terminal. The
fused path makes at most one terminal-publication attempt, not a terminal
durability guarantee. PR26 provides the fixed producer and exact full-inventory,
aggregation, and full-design builders as code-side ingredients only. It does
not provide signed trust-root provenance, wall-clock freshness, an official
descriptor or invocation, official supplier or seeds, any of item 21's three
tracked positive artifacts, an execution-observation receipt, scientific
eligibility, D7, or D8. The final corrected chain supplies and strictly reloads the
three item-21 artifacts, but it supplies none of those later execution items.
The item-21 implementation also does not widen the declared honest-local
source/runtime surface
described above or turn canonical-origin equality into a signed trust root or
hostile-local-operator defense.

The reviewed successor order is:

1. retain PR #23 as a schema/loader candidate only; it must not mint
   authorization;
2. retain the implemented terminal, authenticated-witness-relative-to-pins,
   and typed runner mechanics without invoking the official supplier or
   performing an official execution;
3. retain the implemented fused verify-and-exclusive-start mechanics without
   creating an official descriptor or officially invoking them; they serialize,
   return, cache, and accept no reusable authorization token;
4. retain item 21's exact runtime lock, fixed zero-argument official producer,
   exact full-inventory, aggregation, and full-design builders, and
   installed-inventory equality check as code-side ingredients only; after all
   item-21 source is final, add only the exact source/runtime receipt in its
   direct-child commit, only seed-free readiness in the next direct child, and
   only scoped reviewed successor-family admission in the next direct child;
   strictly reload and rejoin all three before item 21 is complete;
5. retain the item-22 one-shot operation without invoking it or publishing its
   re-anchor;
6. because this source changes the exact-current surface, first publish
   and review the fixed-path exact-current re-anchor bound to item 21; only then
   acquire the
   seed-supply claim, invoke the supplier once, atomically publish the
   seed-bearing full design and target, commit the freeze, and persist launch
   intent; execute item 23's separate descriptive result without changing any
   D7 design byte; and
7. before item 24, create and commit the closed nine-member fused descriptor
   and pass strict verification-evidence replay/rejoin, temporary Git/runtime
   end-to-end validation, and authoritative-start-compatible external-abort
   integration. Item 24 is the first official fused invocation and must yield
   the exact terminal outcome before isolated byte replay can qualify.

Evidence envelopes, existing caller-constructible authority records, and the
item-22 contract specification cannot
be promoted in place; their verification fields remain false. The item-22
supplier claim and invocation, official seeds, atomic seed-bearing
target/full-design publication, committed freeze, launch intent, canonical
nine-member descriptor, official invocation/start/run/terminal/result, D7, and
D8 remain absent or `not_run`. None may be represented by a placeholder
result, inferred from C2 source closure, or authorized by caller-constructible
records.

After the item-22 source implementation, while its artifact and execution
obligations remain open, the canonical state is:

```text
c1_seed_free_source_set_candidate_recorded
historical_structural_rebinding_proposal_preserved
successor_rebinding_review_contract_encoded
c2_declared_historical_git_source_set_closed
replay_target_contract_spec_defined
attempt_envelope_contract_spec_defined
launch_authority_input_schema_candidate_defined
replay_target_instance_absent
attempt_envelope_instance_absent
not_frozen
seed_bearing_target_not_admitted
not_run
d6_v0_1_exact_admission_unsatisfied
historical_git_source_set_closure_verified
c2_runtime_and_transitive_closure_unattested
c2_current_source_compatibility_not_verified
item21_exact_source_runtime_receipt_tracked_strictly_reloaded
item21_exact_installed_inventory_and_runtime_observed_honest_local
item21_seed_free_readiness_tracked_strictly_reloaded
item21_scoped_successor_family_admission_tracked_strictly_reloaded
item21_complete
item22_seed_supply_transaction_instance_absent
item22_historical_item21_chain_valid
item22_exact_current_live_readiness_blocked_pending_reviewed_reanchor
terminal_witness_runner_mechanics_implemented_non_authorizing
fused_verify_and_exclusive_start_mechanics_implemented_not_officially_invoked
canonical_d7_launch_descriptor_absent
d7_runtime_lock_exact_tracked
fixed_official_zero_argument_producer_implemented_deep_internal
exact_full_inventory_aggregation_and_full_design_builders_implemented_deep_internal
installed_inventory_exact_equality_enforced
official_authoritative_start_instance_absent
official_d7_run_absent
strict_verification_evidence_replay_rejoin_implemented_not_officially_exercised
temporary_git_runtime_end_to_end_validation_pending
authoritative_start_external_abort_integration_pending
```
