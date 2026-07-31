# SpiralLens

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)

SpiralLens is an auditable instrument for asking whether transformer
representations contain geometric transport structure or a substrate-bound
field/defect structure that is missed by static, one-direction-at-a-time
feature descriptions.

> **Project status:** experimental research software. The repository is being
> designed toward a reusable library, but the public API and artifact schemas
> remain pre-1.0 and may change.

The project now separates two deliberately narrow questions:

> Can we detect reproducible loop or relative-holonomy structure after
> separating norm changes and accounting for known architectural factors?
>
> Separately, can we define a model-derived order parameter whose amplitude,
> direction, singular set, and sampled charge survive the controls required for
> a topological-defect candidate?

SpiralLens does **not** assume that a model contains literal optical vortices.
It does not call a large drift “phase,” does not treat projected curl as a
physical quantity, and does not label a structural candidate as semantic until
held-out prediction and causal intervention succeed.

No real-model order parameter, verified core, sampled model winding, or
topological-defect candidate currently exists. Local anisotropy, effective
rank, projected norm, and spectral gaps remain possible diagnostics, not
order parameters by themselves.

## Scientific interpretation anchors

The project adopted an order-parameter-first fundamental interpretation after
the frozen Pythia-70M retrieval audit. This is explicitly a post-outcome change
to the future research question, not a rewrite or explanation of that audit.
Frozen protocols and outcomes retain their original meaning.

Read these documents before adding a field, graph, loop, or claim:

- [Order-Parameter-First Fundamental Frame](docs/FUNDAMENTAL_FRAME.md)
- [Experiment Interpretation Ledger](docs/EXPERIMENT_INTERPRETATION_LEDGER.md)
- [Branched Claim Taxonomy](docs/claim_ladder.md)
- [Next Experiment Preparation](docs/NEXT_EXPERIMENT_PREPARATION.md)
- [D0–D5 Closed Cartesian One-Shot Runbook](docs/D0_D5_ONE_SHOT_RUNBOOK.md)
- [P0 Hypothesis and Artifact Contracts](docs/P0_HYPOTHESIS_AND_ARTIFACT_CONTRACTS.md)
- [Research-to-Library Roadmap](docs/ROADMAP.md)
- [Access, Provenance, and Lifecycle Boundary](docs/ACCESS_BOUNDARY.md)
- [Pointwise Referents and Numeric Payload Boundary](docs/REFERENT_AND_NUMERIC_BOUNDARY.md)
- [API Maturity and Compatibility Status](docs/API_STATUS.md)
- [Schema and Compatibility Change Record](docs/SCHEMA_CHANGELOG.md)

## Research pipeline

1. Validate the instrument on analytic rotation, winding, stretch, radial,
   shear, and opposite-sign dipole phantoms, then measure an end-to-end
   detection-limit surface through atlas-form storage, ANN retrieval, exact
   reranking, graph construction, and cycle readout.
2. Stream a fixed-context Pythia model-input-row activation atlas to
   memory-mapped arrays.
3. Emit a schema-validated, provenance-bound structural candidate ledger
   without semantic labels.
4. Bind an explicit substrate and choose one of two typed paths:
   geometry/transport, or a preregistered order-parameter field.
5. Construct semantics-free graph families and matched cycles.
6. Run protocol-declared gauge, architecture, graph-family, radius,
   orientation, sampling, and matched nulls.
7. Add semantic and causal evaluation only after structural promotion.

Pythia-70M is a plumbing smoke and cannot turn an unqualified instrument into
scientific evidence. Pythia-160M remains the historically intended first
scientific model family, but M1 qualification must complete before its M2
protocol can be frozen, and this frame does not authorize that run.
SAE annotation, training-checkpoint trajectories, transfer operators, and
natural-language interpretation are intentionally deferred.

The subject-data executable path currently reaches step 3 through a state-only
neighbor backend contract, a deterministic exact reference, and shared exact
reranking. Separately, the P0 contract layer now validates the F0-F4
hypothesis registry and individual canonical instrument-artifact manifests.
The first P1 development generator now emits one paired
representation-shaped positive/null substrate through F0, F1, and F2 into a
canonical closed bundle. It uses a model-free
`SyntheticLatticeContextBinding` embedded in each
`SyntheticLatticeSubstrateBinding` and the instrument-development-only
`synthetic_lattice` axis. Its bundle indexes no ContextBank
(`context_banks=()`), creates no `ModelBinding` or tokenizer binding, and does
not load Pythia or reuse a model ContextBank.
Its closed-integrity bundle validator additionally resolves exact
content-addressed artifact references, rejects missing, extra, unreachable, or
cyclic members, verifies opaque payload byte lengths and SHA-256 digests, and
checks selected cross-manifest metadata joins. It does not decode payload
values, recompute row identities from array contents, run an estimator or graph
constructor, load a model, or access subject data.
The separate, explicitly authorized numeric consumer now retains only requested
payload descriptors from the same secure bundle-validation transaction,
re-hashes those exact descriptors, strictly decodes bounded numeric NPY v1/v2
snapshots, derives row identity from content, and can verify a frozen L2
amplitude relation. Calling the ordinary bundle loader still retains no
payload descriptor and returns no payload bytes or decoded array. Bundle
member paths remain visible as manifest metadata and are not an access-control
boundary.

The provisional `spirallens.referents` namespace now fixes the F0-F4
pointwise-referent contract. F0 support diagnostics and the F1 projector are
explicitly not order parameters. F2 and F3 derive amplitude and direction from
the same pointwise vector, while F4 derives both from the same pointwise
traceless spin-two tensor. No substrate field or interpolation is bound, so
these formulas are not yet order parameters.
The tracked P0 registry produces referent-contract digest
`4108ccda4f2a76920091bf2bf422b97297fe4d91ee54f14e2b03362e53e358f2`.
This is a software and construct-definition identity, not evidence that any
model contains the referent.

A typed generator-family identity now distinguishes a mathematical
construction from a seed, source digest, or implementation label. The
spectral-moment quadrature family declares a separate mathematical
construction from the existing representation phantom. Its current draft
confirmation foundation supplies the exact four development cases
(nonzero-with-core, null-with-core, null-without-core, and
prerequisite-failure) and a closed typed draft reconstructed only from the
authoritative committed-D6 loader receipt. Identifier difference and
development-path conformance are necessary but do not prove construction,
epistemic, or implementation independence. This foundation freezes no
confirmation seed or execution inventory, persists no full-design receipt,
admits no family, exposes no D7 runner or terminal result, and does not advance
D0-D8. The parent binding and foundation are now `v0.2`. They remain
unpersisted as standalone/public artifacts, while C1 preserves their exact
canonical historical bodies inside its Level-0 wrapper. They omit the
validation-time current-loader HEAD and source-binding digest from canonical
identity while still requiring and validating the authoritative typed loader
receipt. Unchanged historical inputs therefore produce commit-stable draft
bytes; no standalone `v0.1` artifact is migrated.

The internal `v0.2` seed-free D7 execution draft remains unpersisted as a
standalone/public artifact; C1 preserves its exact canonical historical body
inside the same Level-0 wrapper. It reconstructs the full authoritative D6
parent protocol, binds explicit stress translations, and closes the exact
`64` primary / `192` core / `1,152` loop repeated-measures topology. A
development-only path runs the exact 3A-by-3B graph, core, and continuous-loop
pipeline using permanently excluded seeds and stops at sealed predictions
without constructing an oracle-truth record or producing a gate/result.
Implementation also exposed that the D6 v0.1 required-cell and required-stress
bodies contain selection seeds and seed-bearing IDs. A new-seed confirmation
can match their typed structural projection but cannot be byte-identical.
Accordingly the draft records structural equality separately while leaving
exact parent-manifest satisfaction, D6 admission, freeze, and D7 execution
false.

The new internal
`spirallens.d6-d7-structural-rebinding-amendment.v0.1` contract encodes only a
proposed successor fulfillment rule: graph axes and thresholds remain byte-exact,
whereas cells and stress manifests receive distinct successor identities whose
typed structural-projection digest must equal the parent projection. Its
factory and strict canonical reader reconstruct all authority-bearing inputs;
it publishes no artifact and grants no admission or execution authority.
Historical D6 v0.1 bytes remain unchanged and its exact admission remains
unsatisfied. See the
[D7 Confirmation Execution Design](docs/D7_CONFIRMATION_EXECUTION_DESIGN.md).

The mathematical loop/holonomy tools and architecture-factor/null primitives
exist, and the sampled-winding primitive accepts caller-supplied complex
values, but no Pythia candidate is wired to a model-derived order parameter,
matched graph-cycle family, Level 2G result, or Level 2T result.

## D0-D5 qualification engine

The experimental `spirallens.qualification` namespace implements a
model-free, source-bound D0-D5 **calibration-selection engine**. The one
official frozen Cartesian-surrogate attempt is now terminally recorded. All
six scoped gates passed, and the exact canonical result is
`44749d8d237b8b35874099c605f8de3d76130691ce8beb92e1ccf80fa368c13a`.
That outcome is Level 0 and Cartesian-surrogate-only: its own immutable result
still has `d6_d8_advanced=false`, `synthetic_qualified=false`, and every
subject, semantic, integer/topology, P0-winner, representation-transfer, and
localized core-loop-join authority set to false.

Its scope is deliberately narrower than P0-wide instrument selection. The
D2-D5 primary matrix qualifies the F2/Cartesian surrogate lane; the
representation estimator appears only in fixed-development-seed D1/D3
construct and transformation checks. Consequently the protocol and result
keep P0-winner selection, representation D2-D5 transfer, and a localized
core-loop join explicitly unauthorized/false. A later D6 bridge must not
advance the representation instrument until representation-native D2-D5 or an
independently reviewed construct-equivalence contract exists.

The engine keeps two questions separate all the way through aggregation:

- D2 localizes or rejects a core from charge-blind core evidence and seals that
  decision without reading a loop total. Its candidate predicate is localized
  same-section low amplitude alone: at an exact zero the normalized direction
  is undefined as a consequence, not as a second predicate. Identifiability,
  coherence, and support qualify measurements on non-core support, while
  candidate-site degree support is checked independently.
- D4 evaluates only an unrounded, integrated signed sampled-phase total on the
  declared loop representatives. It never emits an integer winding or a
  topology claim.

The Cartesian selection family supplies four joint controls without collapsing
those axes: nonzero-with-core, null-with-core, null-without-core, and a
prerequisite-failure control. The positive control is also the frozen
field-sensitivity sentinel. Its crossed A-by-B graph receipt must show an
actual minimum effect size in estimator-consumed field output; different graph
IDs or one-bit digest changes alone cannot satisfy nonvacuity.

The serialized gate scope is positive and exact: D0 qualifies only engine and
protocol contracts; D1 and D3 qualify the Cartesian surrogate plus the
fixed-development representation checks; D2, D4, and D5 qualify the Cartesian
surrogate only. No D2-D5 gate result can be read as representation evidence.

The closed factory contains two declared seed blocks, four matched controls,
and eight paired stress variants per seed/control, hence 64 execution variants.
Those 64 executions are paired repeated measures, not 64 independent
replicates; seed-block independence is not proved and no inferential sample
size is claimed. Boundary is a loop construction variant, so D2 collapses its
central/wide repeats to 32 unique scientific input units only after their
identity-free estimator-input fingerprint and core observations agree exactly.
A disagreement or missing repeat fails closed. D4/D5 retain all 64 loop
execution variants.

D5 scores the exact frozen `boundary`, `state-geometry-warp`, and
`structured-observation-perturbation` strata at the phantom-instance level.
`state-geometry-warp` is a deterministic warp of the fixed grid coordinates
used to construct state features, with strength `0.0` or `0.1` and coordinate
map `x + s*sin(pi*x)/pi`; it does not change row count and is not a
sample-density intervention. `structured-observation-perturbation` has scale
`0.0` or `0.01` and adds the deterministic term
`a*cos(sqrt(2)*angle + seeded_row_phase)` to observations; it is not
stochastic noise. Graph cells are repeated nuisance measurements, not
independent replicates. Prerequisite failures are excluded from
recall/specificity rate denominators but remain mandatory all-unit controls.

D2 also executes a selection-seed-free core-only falsifier matrix, separate
from the joint loop controls, across every A graph. A high-amplitude
off-center point with local identifiability loss must emit evaluable
`no_core`; a low-amplitude point with missing candidate-site measurement
support must abstain with the exact frozen support reason. Every D2 core input
inherits and binds its field-estimation graph.

The D2 output remains a Level-0 localized zero/core **candidate**. It is not
proof of a vortex, a topological defect, quantized charge, or a successful
core-loop join.

Selection chronology is a separate fail-closed contract:

1. commit the engine, including the three official executable scripts;
2. verify the seed-free declared Git source-set closure (which does not attest
   runtime or transitive dependency closure), publish and strictly reload a
   no-overwrite pre-seed readiness artifact, and only then invoke the official
   seed supplier;
3. publish an unopened protocol and freeze binding the earlier readiness
   path/digests, source identities, and the
   unopened seed-family commitment;
4. commit the readiness artifact, protocol, and freeze as the exact clean
   tracked F artifacts;
5. after fully revalidating F and the terminal-publication capability, persist
   a canonical launch intent before acquiring the one exclusive attempt claim,
   then publish the launch descriptor;
6. commit the store freeze, launch intent, attempt claim, and descriptor as the
   exact clean tracked G artifacts;
7. in a fresh process, derive an in-memory launch authorization only after all
   four G artifacts and the unchanged G HEAD have been reverified, then
   live-reverify that authorization at the official runner entrance and
   atomically publish one freeze-keyed execution-start transition, binding the
   authorization digest and authorized G HEAD, before entering a generator;
   and
8. atomically publish either the fully revalidated terminal result or a typed
   failed-attempt artifact together with its consumption receipt and manifest.
   Both terminal kinds bind the same authorization digest, and terminal
   publication and reload require the typed authorization, revalidate
   `engine commit -> authorized G -> current HEAD`, require all four G blobs to
   remain exact at G/current/worktree, prove that start and terminal paths were
   absent from G, and require its digest to equal the persisted start lineage.

The official package entry point owns steps 7-8 as one call:
`run_and_publish_calibration_selection`. The in-memory
`runner.run_calibration_selection` function remains a module-level development
primitive and is deliberately absent from the package export surface. Once
the start marker has been created, an execution or result-publication
exception is conservatively closed as a typed failed attempt with
`attested_selection_values_observed=true`, then strictly reloaded. A typed
terminal-publication receipt is attached to the unchanged original exception
before it is re-raised; retry authority remains false. If either a result or
failed terminal became visible before a final parent-directory fsync raised,
the exact expected terminal is strictly reloaded and the receipt separately
records `publication_call_returned=false` and
`parent_directory_durability_fsync_proved=false`.

Raw provisional record constructors can represent non-authoritative in-memory
objects. Authority begins only at the validated persistence boundary: the
standalone qualification-result writer and loader reject the official
protocol ID, whose result may be persisted and reloaded only through the
start-lineage-bound terminal transaction. Custom/development protocols retain
standalone persistence and require launch authorization to be `None`.

The readiness chronology claim is `official-process-attested` only:
cryptographic pre-seed proof and human/external-process unseen proof are both
false. The direct seed-first protocol builder is a module-level development
helper and is absent from the curated package export surface; official-ID
launch and execution require the persisted earlier readiness artifact.

An official one-shot is launched in a fresh interpreter at clean G, after the
engine, F, and G artifacts are committed; a long-lived process with
pre-imported, mutable module state is outside the claim. The in-process
callable check is an accidental-replacement tripwire, not hostile-process
attestation. Atomic terminal publication uses Darwin `RENAME_EXCL` or Linux
`RENAME_NOREPLACE` and fails closed on unsupported platforms.

The ordinary successor-aware terminal validator preserves the exact
execution-time source receipt after a later artifact-only commit. It proves
`engine.commit -> stored execution HEAD -> current HEAD`, rechecks every bound
module, official executable, registry, and referent blob at the execution
HEAD, performs the full clean live-source verification at current HEAD,
reconstructs the historical receipt, and requires its canonical digest to
equal the result's stored source summary. A sibling/non-ancestor HEAD,
execution-time blob mismatch, or current bound-path/content drift is rejected.

The D6 sealer uses a separate read-only archival loader. That route reconstructs
committed-G authorization and the H terminal from clean tracked Git blobs,
rejoins the historical source receipt, and runs the current strict schema and
serialized companion checks. It deliberately does **not** run the current D1
implementation, establish current-engine compatibility, or reproduce the
historical execution. These two routes permit the intended
engine-commit → one-shot → terminal-artifact-commit sequence without replacing
the execution HEAD with the later commit in provenance or laundering an
archival read as a rerun.

This pre-run `SelectionFreezeArtifact` froze the D0-D5 attempt; it is not the
later D6 decision that controls independent confirmation.

The post-selection D6 boundary is now scope-explicit. It may seal only the
exact `f2-cartesian-surrogate-d2-d5-v0-1` profile for a future independent
construction-family confirmation. It does not select F2 as a P0 representation
instrument, transfer D2-D5 to the representation estimator, or establish a
localized core-loop join. The decision embeds its admission specification in
one canonical no-overwrite bundle. That specification requires a
genuinely distinct mathematical construction family, the same locked cells,
thresholds, graph axes, surrogate estimator and trivialization,
implementation registry, core/loop separation, stress strata, and
aggregation, plus evidence disjointness and no policy override or
post-selection exclusion.

The authoritative bundle is recorded at
[`experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/d6-surrogate-advancement-decision.json`](experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/d6-surrogate-advancement-decision.json).
Its canonical SHA-256 is
`c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07`;
the embedded admission-spec SHA-256 is
`2e4aa2a272a38ed68b61f612d8a3a261cc6376f3d9a8097f5dce701a2c3f5aa4`.
The bundle binds source commit
`7673ef81bbd67afce5d20255cc6ca6d68e453c3f` and was first tracked by
artifact commit `1fcff8bfedc7d3ae8386bc409595607b5b57b8c4`. A clean
tracked reload rejoined the historical terminal, complete source surface, and
embedded spec with `committed_artifact_verified=true`. The authoritative
loader now also requires the complete current loader source surface to be the
clean tracked blobs of one stable current HEAD and records that commit and
source-binding digest in its receipt. This verifies the code surface executing
the archival checks; it does not claim compatibility with the historical
decision source. Current-source compatibility, historical reexecution, and
historical D1 recomputation therefore remain false.

Downstream D7 `v0.2` draft identity does not serialize that ephemeral
validation HEAD or digest. It still accepts only the typed authoritative
receipt and validates it before deriving the stable historical parent
projection. Thus the loader check remains mandatory while the unchanged draft
identity no longer changes merely because validation occurs at a later clean
descendant commit.

The recorded bundle is also lineage-bound: its source commit must remain an
ancestor of the loading HEAD. This PR must therefore be integrated with a
history-preserving merge commit; squash or rebase integration invalidates the
authoritative reload and is intentionally rejected. The end-to-end recorded
reload test runs only in its declared `absolute_local_paths` layout. Other
checkouts exercise the portable loader contracts but skip that local archival
evidence instead of pretending to relocate it.

D7 and D8 remain explicitly `not_run`. New seeds from the Cartesian closed
form are replication, not independent-family confirmation. The tracked C1
artifact at
[`experiments/qualification/d7_spectral_moment_confirmation_v0_1/c1-seed-free-source-set.json`](experiments/qualification/d7_spectral_moment_confirmation_v0_1/c1-seed-free-source-set.json)
is one canonical `spirallens.d7-c1-seed-free-source-set.v0.1` candidate with
claim ceiling `level_0`; its canonical SHA-256 is
`b7b3b416738c9d02ed76764e35bb131f6bcc6df2948bff200b51df83aee33a5d`.
It binds the stable seed-free design, a declared
construction-diversity review limited to static direct source/dependency
evidence, the D7 implementation registry, the seed-slot aggregation
application, a successor-rebinding review contract that preserves the
historical proposal unchanged, and the declared C1 source-set manifest.
Dynamic/transitive and epistemic independence remain unproved.

C1 embeds neither its post-merge commit identity nor repository-review
attestation nor a C2 receipt; its own `source_closure_verified=false` remains a
historical C1 fact. The separate tracked C2 receipt at
[`experiments/qualification/d7_spectral_moment_confirmation_v0_1/c2-source-closure-receipt.json`](experiments/qualification/d7_spectral_moment_confirmation_v0_1/c2-source-closure-receipt.json)
has canonical SHA-256
`d28a87bce5ec80c3388df1e21bccbc052f34beb637ff86f81f4f502d9fdd71a3`.
It binds exact post-merge C1 commit
`e58a8169b41be688628ab7dda583e68088d3affc`; its unique receipt-only
introduction commit is `2f4e715a951211af8ca0ca4f6b2f7473134bf92b`.
This records declared historical Git source-set closure only. It does not
execute historical code or attest runtime/transitive dependencies,
in-process identity, hostile-local-mutation resistance, or current-source
compatibility.

The deep-internal
`spirallens.qualification.confirmation_replay_contracts` module now
reconstructs two canonical but unpersisted Level-0 specifications:
`D7ReplayTargetContractSpec`
(`spirallens.d7-replay-target-contract-spec.v0.1`) defines what a future
immutable, seed-bearing replay target must bind, while
`D7AttemptEnvelopeContractSpec`
(`spirallens.d7-attempt-envelope-contract-spec.v0.1`) defines the separate
append-only chronology for one future attempt. The choice-free
`load_d7_replay_attempt_contract_foundation()` entry point internally reruns
the pinned committed-C2 verifier; it accepts neither a caller-supplied source
closure nor expected digest. Both specification bytes are canonical, but no
specification artifact is written and neither an actual replay target nor an
attempt envelope exists.

Step 18 is now partially implemented in the separate deep-internal
`spirallens.qualification.confirmation_attempt_records` and
`spirallens.qualification.confirmation_attempt_validation` modules, with
separate `confirmation_attempt_evidence`,
`confirmation_attempt_evidence_validation`,
`confirmation_attempt_persistence`,
`confirmation_result_components`, and
`confirmation_result_component_validation` payload layers. They define closed
canonical schemas for the future declaration, authorization, claim, start,
scientific-result or infrastructure-failure outcome, terminal manifest,
terminal consumption, the six result components, path-absence receipts,
failure payload, and external-abort receipt, together with pure structural
joins between those values. The persistence slice can now write and strictly
reload a caller-supplied Level-0 primary declaration → authorization → claim
→ start record prefix as evidence only. Raw lifecycle records are never the
top-level persisted files. An immutable store-scope record and four chained
`spirallens.d7-prefix-persistence-envelope.v0.1` files live under the distinct
`d7-prefix-evidence-only-v0/` lane; their canonical bytes bind the embedded
record, predecessor envelope, store/lane identity, and
`authority_granted=false`, `authoritative_lifecycle_eligible=false`, and
capability-false constants. In-place promotion is forbidden. The slice
content-addresses the four absence receipts, reobserves their parent inode and
absent leaf, and publishes with descriptor-relative native exclusive rename
plus file and parent-directory fsync. Darwin `renameatx_np(RENAME_EXCL, ...)`
or Linux `renameat2(RENAME_NOREPLACE)` is selected and other platforms fail
closed. This slice is validated only on the current Darwin host; it does not
claim cross-platform qualification. Existing envelope paths are never
replaced.
If a process or host dies after staging-file fsync but before rename, a
dot-prefixed `.tmp` entry can remain. Lane/evidence opens then fail closed:
the orphan is never loaded as a stage or authority and retry is blocked until
writers are quiescent and, only if the entry is confirmed orphaned, an offline
operator recovery protocol removes the exact staging entry.
Automatic scavenging is intentionally absent because it would be unsafe
against a still-running concurrent writer.

The attempt envelope is not one mutable nullable record. Its stage order
remains attempt declaration, launch authorization, exclusive attempt claim,
execution start, exactly one scientific-result or infrastructure-failure
record, terminal manifest, and terminal consumption. The structural identity
graph is acyclic: the manifest binds the typed outcome, and consumption binds
the manifest; the manifest does not bind consumption back to itself. Attempt
records may bind the future concrete replay-target digest but may not redefine
its seeds, design, thresholds, graph/cycle inventory, aggregation, result
schema, construction family, or identity. Scientific `pass`, `fail`, and
`insufficient` are result outcomes that consume the future attempt.
Infrastructure failure is a distinct non-scientific outcome, and `not_run`
cannot be used as a placeholder result. A separate exact closure of the
then-current execution source and runtime remains mandatory after the
lifecycle, result, terminal, and runner code are final; the historical C2
receipt does not close any of those later surfaces.

An authoritative future execution-start operation must rejoin the observed runtime to the
target's frozen source/runtime receipt, bind an external execution identity,
and recheck namespace absence. The persistence writer reobserves the declared
parent device/inode and absent output/terminal leaf, but it can only join the
already supplied source/runtime and execution-identity digests; it cannot
establish their authority. Every scientific payload must bind the exact target and
full inventory. Isolated replay derives its role from an already consumed,
passed primary terminal; a caller label is insufficient. A complete isolated
attempt, whether scientific or failed, is accepted only by a combined
validator that rejoins both the full passed-primary chain and the full replay
chain. Because alternate-store global one-shot behavior is unproved, both
chains must bind the same store identity. Across primary and replay, the five
execution/intent/key/namespace/path identifiers and four absence-receipt
digests must form disjoint sets. The schema-only
outcome-to-manifest-to-consumption joins are an explicit closed table of
canonical byte equalities, not independently named digests. In the future
authoritative lifecycle, a verifier-established visible start without terminal
is `started_unresolved`, never inferred aborted from elapsed time, process
absence, or a caller assertion. It remains unresolved, with retry, replay, and
D8 blocked, unless a later finalizer verifies an external witness bound to that
exact start and execution identity. Pin-relative observer/verifier signature
and terminal-finalization mechanics now exist, but no authoritative-start
issuer or official trust-root provenance connects them to an official attempt.
Likewise, the six result-component payloads,
authorization/pre-start absence receipts, failure evidence payload, and
external-abort verification receipt now have deep-internal canonical byte
schemas. Expected SHA-256 is checked before parsing, exact local types and byte
counts are enforced, and pure joins connect those bytes to the existing
attempt/result envelopes. The result-component join closes 1,344 event lanes
(192 core and 1,152 loop), 64 cell-derived joined primaries, six required
strata, four-state gates, and the outer result bindings. It cannot establish
target-inventory or gate-definition authority without a concrete loaded
target. The directly constructible path receipts remain point-in-time
assertions when used outside the persistence writer. Inside that writer,
their filesystem coordinates are reobserved before the enclosing stage becomes
visible. The observation acquires no reservation and proves neither
hostile-process TOCTOU resistance nor post-publication inode disjointness. A
schema-valid external receipt likewise does not authenticate its observer or
verifier and cannot authorize finalization.

PR #23 exposes the next missing boundary without pretending to complete it.
The deep-internal `confirmation_attempt_authority` module defines one
canonical, non-authorizing structural candidate for a concrete subset of
later launch-authority prerequisites. Its replay-target input uses dedicated
caller-claimed admission, exact-full-design, and exact-source/runtime
candidate leaves instead of generic opaque bindings. Each leaf records
`identity_authenticated=false`; its positive semantic field is explicitly a
caller claim, not a verified fact. The admission leaf preserves the complete
construction-review and admission-spec binding identities, not digest-only
projections. Typed exclusive-supply-claim and
single-supplier-invocation records causally join the supplier, development and
parent registries, readiness, caller-alleged admission and source/runtime
receipts, official inventory, and atomic target/full-design publication. Every
claim, invocation, chronology, inventory-output, and publication verification
field remains false, and no supplier is invoked.

The physical input fixes the `primary-confirmation` role and derives the exact
attempt key from the canonical replay-target digest with the existing attempt
record function. It binds normalized store, evidence-lane, output, and terminal
paths; requires positive store/lane/parent device/inode coordinates; binds the
lane parent to the store while requiring the lane identity to differ; and
rejects both lexical and declared-physical-key aliases to the
persistence-reserved lane, evidence, attempt-envelope, and chronology paths.
These are still declared coordinates, not observations.
Double-slash aliases, embedded NUL, and overlong declared paths are rejected
before they can diverge from the persistence realpath boundary.
The generic artifact binding intentionally has no raw `from_bytes` factory.
Strict loading enforces the byte-size cap before hashing, checks the expected
SHA-256 before parsing, translates malformed, excessively nested, and
oversized-numeric canonical-JSON parser failures into the module's input
error, and rejoins only the supplied records. The loaded
candidate's authority, admission, closure, live-filesystem, absence, freeze,
and execution claims remain false.

This is a positive description of missing inputs, not a retroactive change to
C1, C2, D6, or the existing replay/attempt schemas. A caller-created record,
matching digest, serialized “capability,” or token cannot become authority by
being canonical. Declared device/inode and path coordinates are not a live
reobservation or reservation. Registry completeness is only relative to the
explicitly bound sources and counts in this candidate; it does not prove
supplier chronology or seed secrecy. No reusable authorization object is
issued.

Family admission, full-design freeze, official seeds, authoritative
target-bound lifecycle instances, launch/execution capability,
official result/failure publication, authoritative terminal publication,
official abort finalization, an official runner, and replay comparison remain
absent. The local prefix store is a
persistence-only evidence mechanism: a strictly loaded caller-supplied start
record with an absent terminal entry is only
`caller_supplied_start_record_present_terminal_absent`; any file, directory,
symlink, or malformed terminal entry is
`terminal_path_present_unverified`. Neither establishes execution or
`started_unresolved`, and both keep retry, replay, and D8 unauthorized.
Isolated-replay declarations are rejected before persistence because this
slice cannot load and consume an authoritative passed-primary terminal.
The historical D6 decision and exact-admission status remain unchanged: the
successor rule does not satisfy the historical exact D6 v0.1 hashes. The D6
decision therefore seals the only admissible entrance without pretending that
an independent confirmation or replay has occurred. Global
`d6_d8_advanced=false` and `synthetic_qualified=false` remain invariant. No
label-only D7 admission validator or caller-supplied byte-comparison D8
validator is exposed; those operational surfaces remain deferred until a
concrete target, final-code source/runtime closure, authoritative ownership and
trust-root provenance, fused start, official terminal lineage, and
isolated-replay receipts exist.

The recorded negative-access facts, including the absence of admitted
confirmation-value access before sealing, are explicit external attestations,
not cryptographic proof. The current local store also assumes trusted deletion
rights: an operator able to remove the claim, execution-start marker, or
terminal directory can defeat its local uniqueness history. A future durable
store must make that history append-only. In the historical D0-D5 selection
lifecycle, a consumed or failed selection is not retried under the same
protocol and seed family, and its older process-kill recovery remains
selection-specific. D7 deliberately does not inherit a manual
`terminal-aborted` inference: a valid D7 claim and start without a complete
terminal remains `started_unresolved`. Preserve it for forensic inspection;
the implemented pin-relative external-witness mechanics cannot be used as an
official finalizer until authoritative ownership and trust-root provenance
exist, and a development runner must not be invoked again.

Both the original and successor-aware source receipts remain Level-0,
source-only checks. They do not attest in-process callable identity,
Python/native runtime state, or resistance to hostile local mutation.

The exact pairwise reference fails loudly above 10,000 all-pair rows. No
approximate backend has been promoted yet. A pinned Faiss HNSW range-search
implementation and its receipt-gated audit path now exist. The first
consumer-safe, frozen Pythia-70M full-index/subset-query execution terminated
`insufficient`: all 1,000 preregistered queries had zero exact-reference
support at the frozen boundary. Deterministic empty output passed, recall was
not estimable, and no persistence receipt was issued. This is retrieval
plumbing evidence only.

## Development install

```bash
python -m pip install -e '.[ann,models,dev]'
```

The analytic calibration requires only the core dependencies:

```bash
python -m pip install -e .
spirallens calibrate
```

The full test suite includes the offline Pythia adapter and Faiss backend:

```bash
python -m pip install -e '.[ann,models,dev]'
pytest
```

Recorded-lineage tests fail closed and require the C1/C2 ancestry they verify
to be present locally. A shallow clone that omits any required lineage commit
must deepen or fetch that ancestry before running the full suite.

## First end-to-end run

Calibrate the model-free instrument:

```bash
spirallens calibrate \
  --samples 512 \
  --output runs/calibration/analytic-v0.1.json
```

Validate the tracked public context-bank example before capture:

```bash
spirallens context-bank validate \
  --path protocols/context_bank_example_v0_1.yaml \
  --allow-role example
```

Validate the post-outcome, outcome-excluded P0 hypothesis registry:

```bash
spirallens hypothesis-registry validate \
  --path protocols/order_parameter_hypothesis_registry_v0_1.yaml
```

This command is read-only. It verifies that all F0-F4 families remain
Level-0, no winner or integer output is authorized, and no prior subject
outcome, subject identity, semantic label, or numeric threshold can enter the
registry.

Generate the first tracked P1 instrument-development bundle:

```bash
spirallens synthetic-bundle generate \
  --protocol protocols/p1_representation_phantom_v0_1.yaml \
  --output-dir runs/p1-representation-dev-v0.1
```

The tracked protocol binds the exact generator commit and module SHA-256, the
P0 registry source and canonical digests, the two fixed cases, and an execution
boundary in which all model, subject, calibration-selection, and integer
authorities are false. The emitter executes the bound source bytes, validates
the generated numeric relations, round-trips every NPY payload, validates the
staged closed bundle, and revalidates the published tree. The manifest is
written last inside a private staging directory. Publication then makes the
complete validated directory visible in one atomic, exclusive, no-replace
namespace transition using Darwin `renameatx_np(RENAME_EXCL)`; an existing
destination is never replaced. The publisher retains the exact published
directory descriptor and passes its `(device, inode)` identity into the secure
bundle loader, so post-publication validation cannot silently follow a
replacement display path. This current implementation requires Darwin
`O_NOFOLLOW_ANY`, directory-relative operations, and a filesystem supporting
the exclusive rename. Unsupported environments fail closed. This is namespace
atomicity, not a claim of crash durability: the publisher does not yet fsync
the complete tree and parent directory. If post-publication validation fails,
the published tree is retained for forensic inspection rather than
destructively rolled back. Pre-publication failures likewise retain their
private, random staging directory; the emitter never performs a recursive
stat-then-delete cleanup that could race with a replacement directory.

The durable substrate preprocessing receipt records both
`identity-no-preprocessing` and the complete non-qualification boundary:
`qualification_status=not_evaluated`, `synthetic_qualified=false`, and D0-D8
all `not_run`. The same receipt records
`context_kind=synthetic_lattice`,
`synthetic_context_claim_eligible=false`,
`cycle_construction_status=not_run`, and a versioned conservative resource
guard. The guard uses estimator
`representation-phantom-conservative-static-estimate-v0.1`, safety factor
`4`, and 256 MiB estimated peak/output caps. It protects against
parameter-induced runaway allocation; it is explicitly not an operating-system
OOM guarantee.

The executed development graph is recorded with
`resolution=instrument_dev_executed` and exact
`mutual-knn`/`euclidean`/`k-6` choices. That receipt states what this visible
development cell ran; it is not `fixed_by_hypothesis`,
`calibration_resolved`, calibration selection, or graph-family qualification.
Cycle construction is not run. `CandidateGraph.cycle_support` therefore
contains the schema-required empty `<i8` array of shape `(0, 4)`; this means
that no cycle support was supplied, not that the graph was observed to be
cycleless.

The output contains no `CoreScore`, `CoreCandidate`, `EdgeConnection`, loop,
winding, calibration-selection, or confirmation artifact. Every emitted
F0/F1/F2 observation and supplied anchor remains at Level 0. Its positive/null
pair is a software-development cell, not an independent generator family and
not synthetic qualification. Two cold emissions are required to be
byte-identical in the executing environment; cross-environment numerical,
publication, or byte identity is not yet claimed.

This library slice does not reinterpret the frozen bundle. Instead:

- `spirallens.referents` declares the exact F0-F4 pointwise objects and
  same-object amplitude/direction laws while keeping field binding false;
- `open_numeric_payload_session()` is the first value-reading consumer, gated
  by a trusted parent-policy digest and one-consumer lineage; and
- `SpectralMomentGenerator` supplies a second construction-family foundation
  with disjoint fit/evaluation quadrature and separated oracle truth.

No existing P1 protocol, bundle schema, artifact schema, or frozen Pythia
protocol/receipt bytes are migrated by these additions.

The provisional [`spirallens.graphs`](src/spirallens/graphs) foundation now
adds three deterministic, exhaustive
canonical-coordinate-order Euclidean float64 adjacency mechanisms—mutual-kNN,
inclusive fixed-radius, and all-pair shared-neighbor—plus structural diversity
measurement. A graph-independent
`DiscreteDomainComplex` supplies an exact
integer oriented triangular complex, and `CycleClassBinding` can certify one
narrow relation: a graph cycle refines the same caller-declared, induced support
boundary exactly once. These records are in-memory fingerprints, not
persistence schemas, and do not verify when or why the caller selected that
support or refinement rule. The matched relation is not generic homology, a
latent manifold topology, a core, winding, graph-family cycle invariance, or
D4 qualification by themselves. The later D0-D5 engine consumes these records,
but only a frozen execution can produce a D4 gate result. See
[Graph and discrete-domain foundation](docs/GRAPH_AND_DISCRETE_DOMAIN_BOUNDARY.md).

Validate one generated canonical instrument manifest:

```bash
spirallens instrument-artifact validate \
  --path path/to/canonical-artifact.json \
  --expected-source-sha256 <sha256> \
  --expected-canonical-sha256 <sha256>
```

This is deliberately a single-manifest check. It does not resolve referenced
artifacts or payloads and reports `validation_scope=single_manifest`.

Validate a canonical closed-world integrity bundle:

```bash
spirallens instrument-bundle validate \
  --path path/to/instrument-bundle.json \
  --expected-source-sha256 <sha256> \
  --expected-canonical-sha256 <sha256>
```

The bundle command resolves every exact `ArtifactRef`, requires all indexed
artifacts to be reachable from declared roots in an acyclic dependency graph,
and requires at least one instrument artifact and instrument root. It requires
exact `PayloadRef` closure and streams payload bytes only to verify declared
length and SHA-256. It also validates the implemented cross-manifest metadata
joins and each ContextBank's declared allowed role. It rejects subject fit
roles and cannot authorize subject access or execution. It does not decode
arrays, validate payload semantics, or qualify the bundle scientifically.
Member loading is descriptor-relative and fail-closed: symlinks and files with
multiple hard links are rejected, and platforms without the required
`dir_fd`/no-follow support report `secure_member_open_unavailable` instead of
falling back to pathname reopening. A returned `LoadedBundlePayload` is an
integrity receipt only; it intentionally exposes no reusable payload path or
handle.

The example bank used by the separate Pythia atlas path contains only
project-authored synthetic engineering fixtures. It is not used by the
model-free P1 representation phantom described above. Every bank entry has
`role=example` and `claim_eligible=false`. Scientific discovery and held-out
banks are separate frozen artifacts beginning in M2.

The canonical receipt was produced by the following historical, bounded,
atlas-only Pythia-70M public-example plumbing invocation:

```bash
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
PYTHONPATH=src python3 -m spirallens public-example-plumbing run \
  --protocol protocols/pythia70_public_example_plumbing_v0_1.yaml \
  --output runs/pythia70-public-example-plumbing-v0.1 \
  --receipt \
    experiments/pythia/receipts/pythia70_public_example_plumbing_v0_1.json \
  --expected-protocol-source-sha256 \
    ef93891c7450ef13cc2c5da54bf1a80d4a0b679df2df04964f2cc505e00aaf4c \
  --expected-protocol-canonical-sha256 \
    968ad990e7c80ddae3cadcf71c5b39aa37f7b5cad88ea473df094cedb6b633d6
```

This is provenance, not a rerun command. The tracked receipt now occupies the
shown no-overwrite path, and the generated atlas may occupy the shown output
path in the execution workspace. Any independent replay must use fresh parent
directories while retaining the frozen output basename
`pythia70-public-example-plumbing-v0.1`; it must not replace the canonical
receipt.

The frozen protocol also binds implementation commit
`de24a2b73fa408d49ed4252c8a18332554978296`, and the runner requires that commit
to remain an ancestor of the execution checkout. Integration therefore must
preserve the PR commit ancestry; squash or rebase integration is incompatible
with this frozen engineering cell and fails closed. Ancestry is necessary but
not sufficient: the runner also rejects tracked or untracked drift under
`src/spirallens`, so a later independent replay requires a clean,
source-compatible checkout or dedicated worktree.

The strict tracked protocol selects the exact model revision and cached model
file hashes, ContextBank source and canonical digests, structured slot, 32
explicit row IDs, CPU/float32 runtime, resource ceilings, output identity, and
source implementation. Network access is disabled and the model is loaded
with local files only. The complete protocol content and identity are embedded
in the atlas request and run fingerprint.

The receipt records the access facts—`model_accessed=true` and
`activation_values_persisted=true`—and independently binds the manifest and
array hashes. It also records `scientific_claim_eligible=false`,
`p1_instrument_consumed=false`, D0-D8 `not_run`, and every candidate, neighbor,
graph, field, core, loop, holonomy, winding, semantic, SAE, and integer stage
as `not_run`. The only authorized consumer is atlas integrity validation;
downstream candidate and neighbor entry points reject this execution class
before opening activation arrays.

If atlas finalization succeeds but no receipt is published, that directory is
terminally unreceipted: do not analyze or reuse it. Preserve it under a
quarantine name for diagnosis, fix the publication failure, and rerun into the
original frozen output ID from a fresh path.

Low-level capture can still use `--context-ids` and `--position` directly.
`--position` is the observed residual position and, by default, also the slot
replaced by each swept row; pass `--sweep-position` when they differ. This raw
mode is an engineering escape hatch and carries no ContextBank identity.

This produces a fixed-context model-input-row activation atlas. It is not a
language-space or semantic atlas: a row ID is an address in the model input
embedding table, and SpiralLens attaches no decoded meaning or expected
outcome. It is also not a subject run, candidate source, model-bound
instrument bundle, P1 execution, or progress on D0-D8.

The following command belongs to the preserved historical retrieval workflow,
not to the public-example engineering atlas above. It can consume only an
atlas whose own execution contract authorizes candidate extraction:

```bash
spirallens candidates \
  --manifest runs/<retrieval-authorized-atlas>/manifest.json \
  --output runs/<retrieval-authorized-atlas>/candidates.jsonl \
  --protocol protocols/pythia_v0_1.yaml
```

Candidate ledger v0.3 separates retrieval from judgment. A backend sees only
the unprojected `resid_pre` row matrix and proposes canonical global row-index
pairs. SpiralLens then recomputes every state and drift metric in float64 from
the original arrays. Backend scores cannot pass a gate or enter candidate
identity.

The bounded exact implementation remains the reference backend. The selected
but unpromoted approximate implementation is `faiss-cpu==1.14.3`
`IndexHNSWFlat` with normalized float32 inner-product range search. Build and
search run single-threaded in fresh Python subprocesses; every proposal is
still judged from the original atlas values by the shared float64 reranker.

The reusable measurement and support rules are frozen in
[`protocols/neighbor_recall_gate_v0_1.yaml`](protocols/neighbor_recall_gate_v0_1.yaml).
They require `>= 0.99` aggregate, query-local, density-macro, and
density-by-cosine-boundary recall across deterministic cold rebuilds. Empty or
under-supported required cells are `insufficient`, never an automatic pass.
The atlas-specific v0.2 declaration remains preserved at
[`protocols/pythia_neighbor_v0_2.yaml`](protocols/pythia_neighbor_v0_2.yaml).
The published native-call producer contract remains preserved as historical in
[`protocols/pythia_neighbor_v0_3.yaml`](protocols/pythia_neighbor_v0_3.yaml);
it keeps the outer query artifact batch at 512 while bounding each native
Faiss range-search call to one query. Its bytes remain available for static
inspection only; it cannot authorize preflight, subject execution, or
approximate-candidate persistence. The preserved consumer-safe v0.4 template
is separately preregistered in
[`protocols/pythia_neighbor_v0_4.yaml`](protocols/pythia_neighbor_v0_4.yaml).
It keeps backend version 0.2 but requires qualification receipt schema v0.2
at one exact, non-selectable output path.
Receipt-gated approximate persistence uses the separate typed candidate
declaration
[`protocols/pythia_candidate_v0_2.yaml`](protocols/pythia_candidate_v0_2.yaml);
the older v0.1 declaration remains exact-only and cannot be made
ANN-authorizing by changing its status alone.

The first tracked subject-qualification pair is separately frozen for the
synthetic example bank, Pythia-70M, and `layer_index=0`:
[`protocols/pythia70_slot_only_001_layer0_candidate_v0_2.yaml`](protocols/pythia70_slot_only_001_layer0_candidate_v0_2.yaml)
and
[`protocols/pythia70_slot_only_001_layer0_neighbor_v0_2.yaml`](protocols/pythia70_slot_only_001_layer0_neighbor_v0_2.yaml).
The v0.2 subject attempt ended in a native infrastructure error before any
`pass`, `fail`, or `insufficient` outcome and is terminal under its one-shot
contract. Its reservation marker is retained as a tombstone. Those files do
not upgrade the run into semantic or scientific evidence. The bank is
`claim_eligible: false`, and even a future pass establishes
approximate-retrieval coverage only.

Index bytes, full states, row order, layer group, runtime, candidate protocol,
query contract, and exact rerank contract are bound into the audit identity.
Query selection uses a canonical row-universe digest over ordered token IDs,
the ContextBank/model revision, position, and token domain. Raw manifest bytes
and run UUIDs remain audit provenance but cannot change the query sample.
Every subject audit also requires an out-of-band-hashed execution-freeze
record that verifies the exact pushed source tree, interpreter, installed
NumPy/Faiss content, import root, paths, and argv. For backend v0.2 it also
binds a canonical, production-shape synthetic qualification receipt generated
by two fresh subprocesses, including the fixture, native binary, config, and
range-call limit digests plus the clean, live-pushed preflight commit and
`src/spirallens` tree. Its digest is persisted in the audit identity. The
final pathname is exclusively reserved before any outcome computation, and a
complete fsynced recovery sidecar is staged before the reservation marker can
be replaced.
Approximate candidate persistence accepts only the built-in Faiss backend and
a receipt loaded from persisted audit/protocol files against out-of-band
SHA-256 digests. The audit query subset may expand to all query rows at
persistence; no other target field may change.

The generic tracked v0.4 draft deliberately keeps
`issue_persistence_receipt_on_verified_pass: false`. A separate atlas-specific
v0.4 protocol froze the synthetic qualification receipt, row identity, layer,
and candidate declaration before its one-shot. That audit is terminal
`insufficient`, not `pass`: the exact reference contained zero retrieval pairs
and zero candidates for all 1,000 selected queries. Therefore no approximate
candidate ledger or backend promotion is authorized.
The compact tracked outcome witness is
[`protocols/pythia70_slot_only_001_layer0_subject_audit_v0_4_outcome_observation.yaml`](protocols/pythia70_slot_only_001_layer0_subject_audit_v0_4_outcome_observation.yaml);
it is observation-only and binds the
[exact tracked audit bytes](runs/pythia70-full-slot-only-001/layer-0-neighbor-audit-v0-4.json)
without reconstructing them.

The historical pre-outcome prepare-only invocation used to obtain
atlas-specific bindings without running the ANN or observing an audit outcome
was:

```bash
spirallens neighbor-audit \
  --manifest runs/pythia70-full/manifest.json \
  --layer 0 \
  --protocol protocols/pythia_neighbor_v0_4.yaml \
  --prepare-only
```

It is shown for provenance and must not be rerun against the consumed
Pythia-70M identity.

The v0.4 native path passed a separate subject-independent production-shape
qualification that accepted no atlas, token, drift, decoded string, or
semantic input. Its canonical receipt is preserved at
[`protocols/pythia70_slot_only_001_layer0_faiss_range_qualification_v0_2.json`](protocols/pythia70_slot_only_001_layer0_faiss_range_qualification_v0_2.json).
The receipt qualifies retrieval plumbing only and must not be regenerated at
the same one-shot path.

An earlier receipt-v0.1 producer run was observed to return `pass`, but its
volatile receipt was lost during reboot before it could be tracked. Loading
that receipt after Torch had entered the process exposed an OpenMP collision,
so consumer binding was never established. That observation is not a subject
audit outcome, does not authorize promotion, and did not consume the subject
one-shot. SpiralLens does not enable an unsafe duplicate-OpenMP environment
workaround; receipt v0.2 moves consumer regeneration into a fresh subprocess.

The complete freeze, audit, receipt, and persistence contract is documented in
[Neighbor Audit and Receipt Contract](docs/neighbor_audit.md).

`--full-vocabulary` is required to authorize every ID in the declared sweep
domain explicitly.
Atlas arrays are memory-mapped, manifests are written atomically, completed
files are checksummed, and a resume request must match the original capture
fingerprint.

## Roadmap: experiment to library

SpiralLens is intentionally growing in two stages: first prove that the
instrument is scientifically auditable, then stabilize the parts that deserve
to become a general library.

- **Now — instrument foundation (`0.1.x`):** analytic phantoms, Pythia
  activation atlases, structural candidate ledgers, versioned provenance, and
  fail-closed storage, plus exact and selected-unpromoted Faiss retrieval,
  full-index/subset-query audits, and verified receipt plumbing.
- **Recorded — synthetic D0-D5 qualification:** the frozen Cartesian-surrogate
  one-shot passed its six scoped gates under the committed chronology. This is
  not representation-instrument or subject evidence.
- **Recorded — D6 independent-family admission:** the exact surrogate profile
  and non-negotiable construction-diverse confirmation contract are sealed in
  the authoritative bundle above. D7 and D8 remain machine-readable `not_run`
  until a separately implemented family can satisfy that contract;
  same-family seed changes cannot do so.
- **Recorded C1 candidate — D7 confirmation foundation:** the
  spectral-moment slice has four development cases and a typed seed-free design
  reconstructed from the authoritative D6 loader receipt. Its canonical parent identity is
  commit-stable because validation-time current-loader HEAD/digest fields are
  excluded, while typed receipt validation remains mandatory. C1 binds the
  complete seed-slot inventory, a static-bounded declared diversity review,
  registry/aggregation bytes, successor-rebinding review contract, and source
  manifest. C1 cannot attest its future commit and therefore contains no
  source-closure receipt itself. The separate committed C2 now verifies its
  declared historical Git source set, but does not attest runtime/transitive
  dependency closure, repository review, current-source compatibility, a
  frozen confirmation seed, full-design receipt, admitted family, lifecycle,
  runner, result, or replay authority.
- **Implemented internal v0.2, not frozen — seed-free D7 execution topology:**
  the full D6 parent protocol is strictly reconstructed; explicit boundary,
  state-warp, and observation-perturbation translations produce an exact
  seed-slot inventory of 64 primary, 192 core, and 1,152 loop cells. The full
  graph/field/blind-core/continuous-loop path now has one internal oracle-free
  seed-slot prediction kernel. The permanently-excluded-seed development path
  is a policy adapter over that kernel and retains the same observable
  prediction semantics. An explicitly supplied seed alone attests no freeze,
  authorization, or chronology, and the kernel produces no D7 gate, result, or
  terminal.
- **Encoded historical v0.1 proposal plus C1 review contract — successor
  structural rebinding:** the inherited D6 v0.1 cells and stress-strata hashes include
  selection seeds and seed-bearing IDs. The typed successor rule carries graph
  axes and thresholds forward exactly and requires cells/stress
  structural-projection equality under distinct successor identities. A strict
  reader reconstructs the unchanged historical proposal. C1 now encodes the
  exact successor review contract but embeds no repository-review attestation.
  The committed C2 now verifies declared historical Git source-set closure
  only. The rule remains ineffective until repository review and typed
  admission; C2 does not attest runtime or transitive dependencies. It does
  not satisfy the historical exact hashes; D6 v0.1 bytes remain unchanged.
- **Frozen — post-D6 analysis separation:** the canonical
  post-selection descriptive plan may read only the already-opened PR #9
  terminal and cannot inform D7 design. A separate value-blind D7 gap matrix
  reads only the D6 contract and tracked implementation surfaces. Neither
  artifact runs an analysis, names a candidate family, computes a progress
  score, or grants execution authority. The descriptive plan records that its
  planning used opened outcome values; before its runner may execute, the
  complete D7 family descriptor, admission, protocol, declared Git source-set
  closure, and lifecycle must already be frozen under a committed receipt.
  Runtime/transitive closure remains a separate, unattested obligation. See
  [Post-D6 Descriptive Analysis and Value-Blind D7 Gap Plan](docs/POST_D6_ANALYSIS_AND_D7_GAPS.md).
- **Recorded — receipt-only C2 declared Git source-set closure:** C2 is the
  unique receipt-only child of exact clean post-merge C1 and verifies every
  declared historical Git-tree blob without adding a design choice. Its
  committed loader succeeds through the merge lineage. It does not execute
  historical code or attest Python/native runtime, transitive dependencies,
  in-process identity, hostile-local-mutation resistance, or current
  compatibility.
- **Implemented deep-internal contract, prefix-persistence,
  authority-prerequisite, and item-19 terminal/witness/runner mechanics; step
  18 authority remains partial — replay target and attempt envelope:** two
  canonical, unpersisted
  internal specifications keep the future immutable seed-bearing replay target
  separate from the append-only attempt chronology. Separate deep-internal
  record and validation modules now define the concrete canonical schemas and
  pure structural joins for declaration, authorization, claim, start,
  scientific result or infrastructure failure, manifest, and consumption. The
  identity flow is acyclic: outcome → manifest → consumption. Scientific
  `pass`, `fail`, and `insufficient` remain results; infrastructure failure
  remains a separate non-scientific terminal variant, and no placeholder
  result may stand in for either. A future verifier-established authoritative
  start binds an external execution identity and remains
  `started_unresolved` without a terminal unless a future verified external
  witness supports finalization. After final-code
  source/runtime closure and reviewed family admission, a future seed-supply
  lifecycle must acquire its exclusive claim before the single supplier
  invocation. It then atomically publishes the seed-bearing full design and
  target, commits their freeze receipt, and only then creates launch intent. If
  the claim exists but atomic target publication does not complete, the seed
  supply is aborted and cannot be retried; target absence alone is not evidence
  that the supplier was never invoked. The future target remains exactly Level
  0 and its local authority vector remains all-false. No concrete target,
  official or authoritative attempt instance, official seed, execution
  capability, official runner/terminal/finalizer, or replay comparator is
  created here. The separate local writer now persists and strictly reloads
  the four-stage caller-supplied Level-0 primary prefix as chained,
  false-authority envelopes in a dedicated evidence-only lane without
  replacement. It reobserves authorization/pre-start absence coordinates, but
  grants no authority; a start record plus terminal absence is only
  `caller_supplied_start_record_present_terminal_absent`, while any terminal
  entry is unverified presence. It cannot establish execution,
  `started_unresolved`, or isolated-replay provenance. Exact closure of the final current execution source and
  runtime follows only after those operational code surfaces are complete.
  Deep-internal canonical component, absence-receipt, evidence-payload, and
  verification-receipt byte schemas now reject arbitrary or noncanonical
  caller bytes and perform pure structural joins. They do not load the frozen
  target or authenticate an external witness. The prefix-persistence slice
  observes only the declared local path coordinates and cannot authorize a
  finalizer.
  A further non-authorizing bundle now gives canonical structure to a concrete
  subset of the later prerequisites. Dedicated target-admission,
  target-full-design, and target-source/runtime leaves carry only explicit
  caller claims and `identity_authenticated=false`. Typed exclusive-claim and
  single-invocation inputs causally join the supplier, both seed-exclusion
  registries, readiness, caller-alleged receipt bindings, official inventory,
  and atomic inventory/full-design/target publication. The physical input
  carries the target-and-primary-role-derived attempt key plus positive
  store/lane/parent coordinates, requires distinct store and lane identities,
  and excludes every persistence-reserved lane, evidence, attempt-envelope,
  and chronology path lexically and by known physical alias. The
  artifact-binding surface has no raw `from_bytes`
  factory; the loader applies its size cap, then verifies the digest before
  parsing, and translates canonical parse errors. It authenticates none of
  these inputs and emits no reusable token. Authoritative target-bound exact
  inventory and gate semantics therefore remain deferred. Separate
  deep-internal mechanics now atomically publish one closed structural
  result/failed-attempt terminal by descriptor-relative native no-replace
  directory rename and strictly reload it. The writer rejects competing
  attempt-scoped staging entries, symlink/hardlink/FIFO or unknown-member
  substitution, file-identity drift, parent/stage descriptor drift, and
  uncertain cleanup; it fsyncs members, staging directory, and terminal
  parent, with parent-fsync failure reported rather than laundered. A typed
  primary-only post-start runner handoff projects replay target, full
  inventory, aggregation, and result-schema identities into the complete
  six-component output. Its only scientific boundary is a zero-argument
  producer callback; the exact official executor and aggregation remain
  outside that callback and are not implemented here.

  External abort mechanics now persist a two-signature Ed25519 observer plus
  verifier envelope as a required member of the closed failed-terminal
  inventory. One integrated operation verifies that envelope against explicit
  runtime pins, performs its fixed live prefix/terminal-coordinate
  revalidation, derives the finalization/failed-attempt/manifest/consumption
  records, publishes with no replacement, and strictly reloads the exact
  visible terminal. A second path strictly reloads and reauthenticates an
  existing terminal to the same explicit pins. This proves signature
  authentication only relative to caller-supplied runtime pins. It proves no
  trust-root provenance, official authority, wall-clock freshness,
  authoritative start, or observed execution. The private post-start
  ownership type has deliberately no issuer in this change. Full-design
  closure, admission, freeze, official seeds, the supplier, official exact
  execution/aggregation, scientific eligibility, D7, and D8 all remain
  incomplete or `not_run`. The operational order is now explicit: treat the
  terminal/witness/runner mechanics as implemented without an official run;
  next implement a fused verify-and-exclusive-start operation with no reusable
  authorization token; close the exact final source/runtime and family
  admission; invoke the seed
  supplier once and atomically publish target/full design before committing
  freeze and launch intent; then invoke the fused start. Execute without
  overrides and require complete isolated byte replay. Only a
  future scope-specific confirmation artifact may change its own qualification
  status; the current official result remains byte-identically false for
  `d6_d8_advanced` and `synthetic_qualified`.
- **Then — candidate-to-loop integration:** keep geometry/holonomy and
  field/defect paths separate, join them only through explicit same-substrate
  artifacts, persist a same-field core-degeneracy scalar and its nested-radius
  profile, and retain Pythia-70M as plumbing-only development material.
- **Before M2 — quantify sensitivity:** sweep injection amplitude, declared
  perturbation/noise, and sampling density end to end through atlas, ANN,
  graph, and cycle construction. Exact-recall audits are stratified by local
  density. A zero-candidate result is qualified only relative to the frozen
  detectable region.
- **First scientific protocol:** create separate frozen discovery and held-out
  context-bank artifacts, freeze the integrated instrument with a signed tag
  and an independently timestamped content-addressed snapshot, and run the
  same preregistered design on Pythia-160M without tuning on either held-out
  results or Pythia-70M outcomes.
- **Research validation:** test whether surviving relational structure is lost
  by SAE reconstruction relative to a matched-MSE PCA-\(k\) compressor and
  whether held-out, norm-preserving interventions change downstream behavior
  selectively.
- **Library alpha/beta:** extract stable core APIs, formalize adapter protocols,
  add schema migration and compatibility policy, publish documentation and
  benchmarks, then release on PyPI.
- **1.0:** stable documented API, supported artifact migrations, reproducible
  release process, multi-backend test matrix, and an explicit governance and
  deprecation policy.

The canonical milestone definitions, exit criteria, API boundaries, risks, and
immediate next plan live in the single
[Research-to-Library Roadmap](docs/ROADMAP.md).

## Repository boundaries

- `core/` contains framework-neutral stable-candidate primitives. Its
  compatibility tests have begun, but it is not yet a 1.0-stable API.
- `access/` contains provisional typed provenance, descriptor-only prepare
  access, consumer authorization, value-access lineage, and execution
  lifecycle contracts. It imports no model or numeric framework.
- `referents/` contains the provisional F0-F4 pointwise-referent contract and
  model-free same-object vector/spin-two numeric relations. Successful checks
  establish neither a substrate-bound field nor model-side construct validity.
- `holonomy/` contains continuous closed-loop transport quantities.
- `topology/` contains sampled-winding quantities and, later, topology
  promotion tests. A sampled charge is not a continuous-field certificate.
- `instrument_contracts/` contains implemented experimental metadata
  boundaries for the P0 registry, provisional canonical artifacts, and
  closed-world integrity bundles. Its ordinary bundle loader reads opaque
  payload bytes only for length and SHA-256 verification. A separate
  authorization-bound numeric session decodes declared arrays and validates
  closed numeric relations; neither path runs an estimator, graph constructor,
  or subject access;
- `synthetic/` contains the model-free, source-bound P1 development generator,
  a distinct spectral-moment generator-family foundation, numeric self-audit,
  conservative resource preflight, exact executed development graph, and
  current-environment exclusive bundle publisher. It is not a
  calibration-selection or subject-execution boundary;
- `graphs/` constructs provisional model-free,
  canonical-coordinate-order Euclidean float64 graph families and a
  graph-independent discrete-domain foundation from supplied numerical inputs.
  It remains separate from retrieval and does not qualify a scientific graph,
  field, core, loop, or topology claim;
- `qualification/` contains the experimental, model-free D0-D5 protocol,
  source/evidence binding, charge-blind core and continuous sampled-loop
  kernels, crossed aggregation, exclusive attempt chronology, terminal
  persistence, and the scope-limited D6 independent-family admission
  boundary. Deep internal modules now also contain the Level-0 C1 source-set
  candidate, the choice-free C2 issuer/loader, and its committed
  declared-Git-source-set receipt, plus canonical unpersisted replay-target and
  append-only attempt-envelope contract specifications. They are not exported
  from `spirallens.qualification` or the package root. No admission, seed,
  execution, result, or promotion surface is published.
  Importing the namespace does not run a selection or confirmation, advance
  global D6-D8, or authorize subject access;
- `factors/` accounts for LayerNorm, RoPE, attention value transport, routing,
  and MLP paths.
- `neighbors/` retrieves row-index pairs from unprojected states only; it never
  decides whether a pair is a candidate.
- `semantics/` is downstream annotation and evaluation, never discovery.
- `benchmarks/icicl/` is an optional external benchmark and is not imported by
  the core package.

See the [Fundamental Frame](docs/FUNDAMENTAL_FRAME.md),
[glossary](docs/glossary.md), and
[branched claim taxonomy](docs/claim_ladder.md) before adding a new metric or
persisted field.

## License

SpiralLens is licensed under the
[Apache License 2.0](LICENSE).
