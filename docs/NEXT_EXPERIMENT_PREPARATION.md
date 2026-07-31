# Next Experiment Preparation

- **Status:** preparation plan; no subject protocol or subject execution
- **Depends on:** [Order-Parameter-First Fundamental Frame](FUNDAMENTAL_FRAME.md)
- **Historical evidence boundary:** [Experiment Interpretation Ledger](EXPERIMENT_INTERPRETATION_LEDGER.md)
- **Claim state at entry:** Level 0 for any real-model order-parameter or
  topological-defect hypothesis

This plan ends with a synthetic-qualified, replayable instrument bundle. It
does not select a Pythia subject, build a subject graph, observe a subject
field, or authorize a subject run.

The plan was created after the frozen Pythia-70M retrieval audit. That audit
cannot select a field hypothesis, graph, threshold, exclusion, model, context,
or preprocessing choice below.

## 1. Preparation principles

- Field first; charge only when its mathematical prerequisites exist.
- Continuous holonomy and sampled winding remain distinct outputs.
- Competing field hypotheses remain separate and retain their own claim
  ceilings.
- Synthetic calibration qualifies an instrument, never a model claim.
- Graph construction is a first-class nuisance family, not a cosmetic
  parameter sweep.
- Any required `fail` stops qualification.
- Any required `insufficient` blocks qualification rather than shrinking the
  required design after observation.
- Subject preparation begins only after a locked independent calibration and
  byte-replay freeze.

## 2. Stage P0 — post-outcome, outcome-excluded hypothesis registry

**Implementation status:** the strict, metadata-only v0.1 registry and P0
policy validator are implemented, together with the canonical
closed-integrity bundle boundary described in Stage P2. This completes
representation and integrity checking of the families and their unresolved
choices; it does not select or advance one.

Before implementing a new estimator, create a registry that explicitly
postdates the Pythia-70M outcome while excluding that outcome from selection.
Mathematical coherence, independently generated synthetic
calibration-selection data, and prespecified nuisance coverage may select a
hypothesis or parameter. The Pythia-70M status, support counts, candidate
values, and downstream retrospective analyses may not. Every field hypothesis
declares:

- input tensor and observation axis;
- centering, residual, and architecture-accounting rule;
- domain and substrate binding;
- estimator and fit scope;
- gauge or basis transformation law;
- target manifold and admissible charge group, if any;
- amplitude, support, and identifiability quantities;
- interpolation, lift, trivialization, or reference convention;
- edge-connection rule for vertex-wise local coordinates;
- allowed observables;
- forbidden labels;
- claim ceiling;
- mathematical failure reasons.

The initial registry keeps all of the following unresolved.

### F0 — support diagnostics

Local covariance eigenvalues, entropy effective rank, top-two concentration,
and spectral gaps.

- Output: field-unbound `SupportDiagnostic` values.
- Maximum claim: Level 1G support diagnostic, never a defect-field observable
  by itself.
- Forbidden claim: phase, winding, or defect.

### F1 — projector and connection

Local rank-two projector \(P_i\), principal-angle coherence, and Procrustes
links.

- Output: projector field and continuous connection/holonomy.
- Rank status: rank two is part of this hypothesis definition, not a
  confirmation-time parameter.
- Initial role: geometry-branch comparator; advancement remains a
  calibration-selection decision.
- Forbidden claim: integer charge inferred from matrix holonomy.

### F2 — local covariant section

A declared, cross-fitted local frame \(U_i\) and accounted response \(s_i\)
define \(z_i=U_i^\top s_i\).

- Output: amplitude and gauge-covariant sampled section.
- Rank status: the two-channel target is fixed by this hypothesis; covariance,
  weighting, and neighborhood estimators remain calibration choices.
- Winding eligibility: only if the bundle is orientable, the section is
  nonzero on the loop, all connection, branch, and sampling gates pass, and a
  frozen global trivialization/reference or a proven gauge-invariant
  connection-corrected lift exists.
- Otherwise: only continuous connection or section diagnostics are eligible;
  integer promotion is forbidden.

### F3 — fixed or global-plane section

A fit-split-only oriented plane \(B\) defines \(z_i=B^\top s_i\).

- Role: simple projection-dependent baseline.
- Initial ceiling: exploratory Level 1D only after a bound, replayed field
  observation; otherwise Level 0.
- Required controls: fit leakage, ambient basis, reflection, random-plane
  ensemble, and held-out projection checks.

### F4 — spin-two anisotropy

The traceless part of a declared in-plane symmetric tensor defines a
director-like complex section.

- Output: anisotropy amplitude and doubled-angle direction.
- Kept separate from F2 because its transformation and charge conventions
  differ.

No winner, primary integer output, covariance estimator, residual source, or
numeric threshold is selected at P0. A future rank other than two is a new
hypothesis family, not an after-the-fact F1/F2 setting.

## 3. Stage P1 — representation-shaped analytic substrates

Build high-dimensional, discrete substrates with known latent structure and
random ambient embeddings. Independent generator families are required; new
seeds of one closed form are not independent confirmation.

**Implementation status — first instrument-development slice:** the tracked
[`p1_representation_phantom_v0_1.yaml`](../protocols/p1_representation_phantom_v0_1.yaml)
protocol now generates a shared 9-by-9 lattice embedded in 16 dimensions, with
eight cross-fitted probes and an exact mutual-kNN development graph at
\(k=6\). It emits one angular-section positive and one fixed-direction null
through F0 support diagnostics, F1 local rank-two frames, and an F2
gauge-covariant section. The canonical substrate uses the
instrument-development-only `synthetic_lattice` axis rather than pretending
that lattice addresses are model token positions. Each
`SyntheticLatticeSubstrateBinding` embeds a model-free
`SyntheticLatticeContextBinding` that binds generator, protocol, row, lattice,
and boundary provenance. The generated bundle has `context_banks=()` and
contains no model, tokenizer, or Pythia binding.

**Implementation status — pointwise referent and second-family foundation:**
the provisional `spirallens.referents` namespace now freezes the pointwise
F0-F4 objects against the tracked registry. F0 and F1 are explicitly
non-order-parameter referents. F2/F3 derive amplitude and direction from the
same pointwise vector; F4 derives both from the same pointwise traceless
spin-two tensor and keeps the doubled-angle convention distinct. Substrate
field and interpolation binding remain false, so F2-F4 are formulas from which
a later field may be built, not order parameters in this slice. The
registry-bound contract-set digest is
`4108ccda4f2a76920091bf2bf422b97297fe4d91ee54f14e2b03362e53e358f2`.

The first separate value consumer now derives content row identity and validates
bounded numeric NPY payloads and a predeclared, tolerance-bound L2-amplitude
relation from descriptors retained during secure bundle validation. The
ordinary bundle validator remains opaque. A separate
spectral-moment/Fourier-quadrature construction supplies typed F2/F4 positive,
fixed-null, and prerequisite-failure controls with disjoint fit/evaluation
samples and oracle truth excluded from estimator inputs. It applies a
conservative pre-allocation resource cap and harmonic resolvability floors,
recomputes moment/truth linkage on both splits with a non-vacuous relative
recovery gate, and binds the canonical controls back to the declared spec.
This second family is a development foundation, not an integrated
qualification cell, independent confirmation, or D0/D1 pass.

**Implementation status — graph and discrete-domain foundation:** the
provisional `spirallens.graphs` namespace now implements deterministic,
exhaustive canonical-coordinate-order Euclidean float64 mutual-kNN, inclusive
fixed-radius, and all-pair shared-neighbor adjacency on one bound numerical
input. It measures pairwise edge, degree, component, and two-core relations
without setting a diversity threshold or gate result. A
graph-independent oriented triangular `DiscreteDomainComplex` verifies exact
integer boundary operators, and a `CycleClassBinding` may prove that a graph
cycle refines one caller-declared face-support boundary exactly once. These are
immutable in-memory fingerprints only and do not verify caller-side selection
history or outcome blindness. Same induced support boundary is not generic
homology, a core, winding, graph-family cycle invariance, topology promotion,
or D4 qualification by itself. The later Stage P7 engine consumes these
foundations, but only a frozen engine execution can produce a D4 gate result.

This slice is deliberately below the Stage P1 exit. Graph family, metric,
scale, identifiability, interpolation, lift, trivialization, and reference
choices remain unresolved for qualification even though the executed
development cell binds its exact constructor ID and records
`resolution=instrument_dev_executed` for `mutual-knn`, `euclidean`, and
`k-6`. This state records only what a visible instrument-development cell ran;
it is neither hypothesis-fixed nor calibration-resolved, and it cannot qualify
or calibration-select a graph family.

Cycle construction is `not_run`. The `CandidateGraph` carries an empty
`<i8`, shape `(0, 4)` cycle-support payload solely to satisfy the current
schema. Empty support here means that no cycle support was constructed or
supplied, not that the graph was evaluated and found to be cycleless. The slice
emits no core score, localized core, connection, loop, winding, selection,
confirmation, or integer result. Its paired cases are one analytic generator
family, not independent confirmation. The durable preprocessing receipt binds
`identity-no-preprocessing`, the full protocol content and digests,
`qualification_status=not_evaluated`, `synthetic_qualified=false`, and D0-D8
all `not_run`.

Before any generator allocation, a versioned conservative static estimator
applies a safety factor of four and rejects estimated peak or output footprints
above 256 MiB. The receipt persists the estimator ID, estimates, caps, safety
factor, and
`parameter-induced-runaway-allocation-guard-not-os-oom-guarantee` claim
boundary. This is not an operating-system OOM guarantee. Current-environment
cold replay is byte-identical; numerical portability and the Darwin-only
exclusive publication path have not been evaluated elsewhere.

### Positive families

- supplied section charges \(q=0,\pm1,\pm2\);
- known SO(2) holonomy with zero and nonzero supplied section winding;
- nested loops and charge conservation;
- nonuniform sampling and density imbalance;
- known amplitude depression and known singular sets.

### Gauge and basis metamorphs

- vertex-wise SO(2) gauge changes;
- ambient orthogonal reparameterization;
- sign and basis flips;
- declared reflection and conjugation cases;
- orientation reversal.

### Negative families

- radial amplitude without winding;
- isotropic covariance;
- stretch, shear, and pure gauge;
- smooth gradient with no winding;
- random projection artifacts;
- degree- or density-correlated fields;
- shuffled vertex fields;
- degree/component-preserving graph rewires.

### Prerequisite failures

- amplitude zero on an evaluated loop;
- unresolved \(\lambda_2-\lambda_3\) gap;
- low subspace overlap or edge coherence;
- O(2) non-orientability;
- disconnected or cycleless support;
- branch-cut and undersampling alias;
- unmatched cycle class;
- missing or sparse core support.

### Stress axes

- noise;
- density and neighborhood-sample imbalance;
- spectral-gap and coherence sweeps;
- sampling and radius sweeps;
- graph-scale sweeps selected without field outcomes.

## 4. Stage P2 — experimental artifact boundaries

The intended artifacts use the canonical type names from the Fundamental
Frame. Their metadata-only v0.1 schemas and strict canonical loader are
implemented as provisional experiment contracts, not stable public APIs. No
estimator, graph constructor, calibration result, or subject artifact is
created merely by loading those schemas. A separate closed-integrity bundle
validator resolves manifests and opaque payload references without decoding
payload values or qualifying an experiment. The P1 development emitter now
instantiates a bounded F0/F1/F2 cell, semantically self-audits its generated
arrays before publication, and then uses that same closed-integrity validator.
It does not change the validator into a scientific qualification gate.

The separate `open_numeric_payload_session()` path is not part of ordinary
bundle validation. It requires a trusted parent-policy digest and exact
`numeric_payload_validation` authorization before any path inspection, retains
only requested descriptors from the same validation transaction, re-hashes
them, and returns owned read-only arrays after strict NPY and row-identity
checks. Value-contract failures are hard failures rather than scientific
`insufficient` results.

### `SubstrateBinding`

Bind:

- ordered vertex and observation identities;
- exactly one declared evolution axis;
- raw states and accounted response source;
- masks, dtype, shape, and content digests;
- preprocessing fit receipt.

An ordinary model `SubstrateBinding` additionally binds a ContextBank role and
split and rejects `synthetic_lattice`. A model-free development phantom instead
uses `SyntheticLatticeSubstrateBinding`, which has no ContextBank, model, or
tokenizer reference. Its embedded `SyntheticLatticeContextBinding` binds source
ID, generator revision and module/spec digests, protocol source and canonical
digests, row identity, lattice shape, boundary rule, and
`claim_eligible=false`.

No unqualified field named `phase` or `time` is permitted. A
`SyntheticLatticeSubstrateBinding` requires both `role=instrument_dev` and
`evolution_axis=synthetic_lattice`; the referent is excluded from the P0 model
observation-axis candidate set and cannot be laundered into a subject axis.

### `GraphConstructionSpec` and `CandidateGraph`

The specification binds the graph family, metric, constructor, scale-selection
rule, deterministic tie policy, and allowed role. The resulting graph binds:

- canonical vertices, edges, and weights;
- connected components, degree distribution, two-core, and cycle support;
- substrate, specification, and graph digests.

`instrument_dev_executed` is an execution receipt, not a scientific selection.
When used, family, metric, and scale must all carry that resolution and the
graph role must be `instrument_dev`; conversely every `instrument_dev` graph
must use that resolution for all three choices and cannot be relabelled
`fixed_by_hypothesis` or `calibration_resolved`. It cannot refine a registry
`calibration_selection`, count as `calibration_resolved`, or qualify the
constructor. In the first P1 slice the cycle-support field is an explicitly
unconstructed empty payload paired with `cycle_construction_status=not_run`;
it is not a cyclelessness diagnostic.

### `SupportDiagnostic`

Bind a field-unbound scalar definition, neighborhood and fit role, values,
uncertainty, support, and pointwise reason codes. Effective rank, anisotropy,
gap, density, and coherence begin here. A `SupportDiagnostic` is not a
`CoreScore`.

### `GeometricFieldEstimate`

Bind a geometry hypothesis, substrate, estimation-graph, fit, projector or
frame, eigenspectrum, support, gauge law, and content digests. It can support
connection and holonomy analysis without an `OrderParameterField` or
`CoreCandidate`.

### `CoreScore`

Bind the scalar definition, neighborhood and fit role, values, uncertainty,
support, and pointwise reason codes. It also binds the exact
`OrderParameterSpec` and `OrderParameterField` digests plus a frozen rule
showing why the score marks zero or unresolved amplitude/identifiability of
that same field. It has no access to loop holonomy, winding, or charge results.

Its neighborhood mode is exactly one of:

- `graph_free`;
- `inherit_field_estimation_graph`, binding that graph digest;
- `explicit_core_graph`, binding its own `GraphConstructionSpec` and
  `CandidateGraph`.

The current D0-D5 qualification protocol chooses exactly
`inherit_field_estimation_graph`; `graph_free` remains a general artifact mode,
not an admitted qualification-engine `CoreGraphMode`.

### `OrderParameterSpec` and `OrderParameterField`

The specification binds:

- hypothesis, input, fit-role, substrate, and estimation-graph identities;
- target manifold, gauge law, and admissible charge group, if any;
- amplitude and identifiability rule;
- interpolation, lift, global trivialization, or reference convention;
- claim ceiling and forbidden labels.

The field binds the specification and substrate digests, per-vertex values,
amplitude, frame or tensor identity, eigenspectrum and support diagnostics, and
reason codes for unresolved values.

### `CoreCandidate`

Bind its `CoreScore`, source role, localization algorithm, support,
uncertainty, substrate digest, exact `OrderParameterField` digest, singularity
rule, and neighborhood mode/graph digest. Localization must be frozen before
any loop readout and cannot consume holonomy, winding, or charge.

### `GroundTruthAnchor`

Bind a supplied synthetic core/anchor and generator identity for conditional
loop-mathematics evaluation. It is never estimator input, never serialized as
a `CoreCandidate`, and cannot satisfy a core-localization gate.

### `EdgeConnection`

Bind principal angles, Procrustes singular values, coherence, O(2)/SO(2)
orientation state, transport convention, and exact endpoint field identities.

A vertex-wise section coordinate cannot be differenced across local frames by
subtracting raw angles. Every cross-vertex increment must bind the declared
edge connection and transport convention; unresolved orientation or coherence
produces a reason code rather than a forced angle.

### `LoopEstimate`

Use a discriminated `branch` field.

Every branch binds ordered support, matched class or anchor identity,
cycle-graph digest, orientation, sampling, and support evidence.

- `branch=geometry` binds a `GeometricFieldEstimate` and `EdgeConnection`,
  reports continuous holonomy, and does not bind an order parameter or core.
- `branch=defect` binds an `OrderParameterField`, interpolation, lift,
  trivialization/reference, boundary amplitude/identifiability, and branch
  evidence. It binds an `EdgeConnection` only when local frames require one.
  A localized-defect claim additionally binds a `CoreCandidate`.
- An unlocalized sampled graph-cycle winding may omit `CoreCandidate`, but its
  claim ceiling remains Level 1D and it cannot enter Level 2T.

### `CalibrationSelectionDecision`

Before hidden confirmation, bind:

- all considered hypotheses and their advance, retain-diagnostic, or reject
  status;
- required versus diagnostic cells and every aggregation rule;
- selected estimators, graphs, thresholds, coverage and abstention gates;
- calibration-selection inputs and output digests;
- source commit, claim ceiling, and unresolved hypotheses.

The selection artifact is sealed before confirmation data are opened.
Non-advanced competitors remain reported and cannot be retroactively made
required or silently dropped.

The generic instrument artifact above is not a bridge from the PR9
`QualificationResult`: its inputs are canonical instrument artifact
references, while the result is a separate qualification terminal type. The
current D6 implementation therefore uses a dedicated
surrogate-profile-advancement decision that binds the full terminal identity
and cannot resolve a P0 hypothesis. Conflating these two decision classes would
launder Cartesian surrogate evidence into representation-instrument evidence.

### `CalibrationConfirmationResult`

Bind the sealed `CalibrationSelectionDecision`, every attempted confirmation
cell, the locked result, unresolved hypotheses, source commit, and artifact
digests. It may apply the selection decision but cannot select or amend it.

Every artifact requires canonical ordering, exact field sets, tamper rejection,
row-order mismatch rejection, and byte-identical replay.

### Implemented closed-integrity bundle boundary

One canonical bundle manifest declares roots and a closed index of instrument
artifacts, P0 registries, ContextBanks, and opaque payloads. Validation:

- resolves every `ArtifactRef` by exact type, schema version, artifact ID, and
  canonical digest;
- rejects missing, extra or unreachable artifact entries and dependency
  cycles;
- requires exact `PayloadRef` closure and verifies each payload's declared byte
  length and SHA-256 by streaming its bytes without decoding values;
- checks selected cross-manifest substrate, graph, field, core, loop,
  registry, selection, and confirmation metadata joins;
- loads each ContextBank under its explicitly indexed allowed `ContextRole`;
  and
- forbids subject fit roles, subject-data authorization, subject access, and
  subject execution.

This is an integrity and provenance boundary only. It does not validate array
layout or payload semantics, recompute row identities from payload content,
map `ContextRole` to `FitRole`, prove calibration-cell completeness, qualify
D0-D8, or support scientific, topological, semantic, or causal claims.

The P1 emitter is a separate producer above this generic validator. It executes
the exact bound model-free generator, semantically recomputes the generated
F0/F1/F2 array relations, and round-trips each NPY payload before calling the
unchanged closed-integrity validator. Its manifest indexes no ContextBank;
instead, bundle validation checks the embedded synthetic-context row identity,
site count, and ineligible claim state.

Publication is also an emitter boundary rather than a validator claim. The
emitter writes `bundle.json` last inside a private staging directory, validates
the complete staged tree, and publishes the whole directory with one Darwin
`renameatx_np(RENAME_EXCL)` no-replace namespace transition before
revalidation. The exact published directory descriptor remains open, and its
`(device, inode)` identity is required by every secure loader traversal.
Unsupported platforms or filesystems fail closed. This gives exclusive
namespace atomicity, not crash durability; the implementation does not yet
fsync the complete tree and parent directory. A tree already made public is
retained for forensic inspection if post-publication validation fails. An
unpublished private staging tree is also retained on failure instead of being
recursively deleted through a raceable pathname.

## 5. Stage P3 — substrate and leakage binding

- Bind exactly one evolution axis. Model observations use `token_position`,
  `layer_index`, or `training_step`; representation-shaped development
  phantoms use `synthetic_lattice`, which is forbidden outside
  `instrument_dev`.
- Graph construction sees only the frozen, declared unprojected state.
- Field estimation sees only the declared accounted response.
- A local covariance uses leave-one-out or fold-cross-fit estimation so a
  vertex cannot define its own field frame without disclosure.
- Whitening or a global plane is fit only on its allowed fit role, persisted,
  and frozen.
- Decoded strings, semantic labels, SAE labels, and held-out answers remain
  absent.
- All variants of one base phantom remain in the same split group.
- Contexts remain grouped by family, source, and template.
- Pythia-70M history is development material only and cannot select any
  confirmatory choice.

## 6. Stage P4 — graph-family crossed qualification

Prepare genuinely distinct same-vertex constructions:

1. mutual-\(k\)-nearest-neighbor graph on the frozen ambient metric;
2. fixed-\(\epsilon\) radius graph on that metric;
3. shared-nearest-neighbor or neighborhood-overlap graph;
4. an optional preregistered diffusion-distance adversary.

The first three deterministic constructors and a structural-diversity receipt
now exist as a model-free foundation. Their family labels and measured
adjacency differences are not an adequacy decision or evidence of independent
failure modes. The qualification thresholds, scale selection, crossed cells,
and required-family gate in this stage remain unimplemented.

Metric changes, such as cosine versus frozen-whitened Euclidean distance, form
a separate null.

Graph scales are selected without field, core, holonomy, winding, or charge
outcomes against frozen nuisance targets:

- common-vertex support;
- component coverage;
- two-core and cycle coverage;
- declared edge or degree budget.

Pairwise edge Jaccard, degree correlation, component structure, and two-core
support are persisted. Nearly identical required families yield
`insufficient_graph_diversity`, not evidence of invariance.

Run the full matrix:

\[
G_{\text{field estimate}}
\times
G_{\text{cycle construction}}.
\]

If core localization uses a graph, its nuisance axis is declared explicitly.
An inherited core graph binds \(G_{\text{core}}=G_{\text{field}}\); an
independent core graph requires the matched-support
\(G_{\text{core}}\times G_{\text{field}}\times G_{\text{cycle}}\) design.
Core support stability is persisted across every required core-graph family.

A supplied phantom center may create a `GroundTruthAnchor` for conditional
loop-mathematics qualification only. Independently, a charge-blind,
field-bound `CoreScore` may create an inferred `CoreCandidate` for localization
qualification. The two artifacts never substitute for one another, and the
inferred candidate is sealed before loop readout. Confirmation cells cannot
recenter, replace a cycle, or retune a scale after observing an observable.

## 7. Stage P5 — failure vocabulary

The gate states remain:

- `pass`;
- `fail`;
- `insufficient`;
- `not_run`.

Malformed, tampered, or leaky artifacts are rejected as invalid rather than
recorded as scientific failures.

### `fail`

Use when prerequisites and support are adequate but:

- a known phantom response is wrong;
- two evaluable required graph cells disagree;
- a pure-gauge or rewire negative remains positive;
- orientation or nested-loop behavior violates the frozen expectation.

### `insufficient`

Use when:

- no cycle or two-core support exists;
- graph families are not genuinely distinct;
- a matched cycle class cannot be established;
- spectral gap, edge coherence, or amplitude is below its floor;
- the bundle is non-orientable for a requested U(1) quantity;
- the branch or sampling resolution is ambiguous.

No required insufficient family is silently dropped.

### Coverage, abstention, and aggregation

Every metric declares its evaluation unit: vertex, core, boundary loop,
matched class, graph cell, or phantom instance. Each required stratum persists
attempted, evaluable, `pass`, `fail`, `insufficient`, and `not_run` counts.
Required strata initially include:

- generator family and supplied charge;
- noise and density regime;
- boundary/core distance;
- radius and sampling regime;
- field-estimation graph by cycle-construction graph;
- core-estimation graph when it is not graph-free.

Calibration selection freezes minimum evaluable fractions, maximum abstention,
per-stratum recall and specificity or false-positive limits, and the
worst-case aggregation rule before hidden confirmation. A floor cannot qualify
an estimator by turning adverse positives into `insufficient`. If coverage is
below its gate, the enclosing required stratum is `insufficient`; an average
over the remaining cases cannot pass it.

### Initial reason codes

- `no_cycle_support`
- `graph_family_not_distinct`
- `cycle_class_not_matched`
- `spectral_gap_below_floor`
- `edge_coherence_below_floor`
- `amplitude_at_or_below_floor`
- `branch_cut_or_undersampling_ambiguity`
- `non_orientable_bundle`
- `null_specificity_failed`

Numeric floors remain unresolved until the declared calibration-selection
stage.

## 8. Stage P6 — role and access separation

Use five roles:

1. `instrument_dev`: visible implementation and debugging;
2. `calibration_selection`: preregistered grids may select instrument
   parameters;
3. `calibration_confirmation`: locked, one-shot independent generators,
   embeddings, and noise regimes;
4. `subject_discovery`: future candidate localization without instrument
   changes;
5. `subject_confirmation`: future held-out context/model groups opened only
   after protocol freeze.

Any learned preprocessing fits only its declared role. Hidden calibration
cannot be inspected during threshold selection. A
`CalibrationSelectionDecision` is sealed before the confirmation role is
opened. After locked confirmation, freeze one content-addressed instrument
bundle before preparing any subject manifest.

## 9. Stage P7 — decision gates and stopping rule

The repository now contains a closed, model-free D0-D5
calibration-selection engine and its persistence/chronology contracts. That
implementation alone does not set a gate to `pass`. The official selection
outcome now exists because the exact canonical readiness/protocol/freeze F
artifacts, a
launch intent persisted before one exclusive attempt claim; exact clean
tracked store-freeze/intent/claim/descriptor G artifacts; fresh G-derived
authorization; and one atomic execution-start transition have been published
and the one-shot run terminated in one validated terminal transaction. All six
gate states are `pass` within their serialized scopes. The result remains
Level 0, Cartesian-surrogate-only, and false for D6-D8, synthetic
qualification, P0 winner, representation transfer, localized join, subject,
semantic, and integer/topology authority.

### D0 — definitions

All inputs, transformations, targets, interpolation or transport conventions,
outputs, and claim ceilings required by the exact declared lane are complete.
For the current engine that means the F2/Cartesian qualification lane, not a
completed F0-F4 competitor matrix and not a selected P0 winner.

For the current selection engine, the executable D0 evidence path binds the
exact source commit and module digests, canonical P0 registry and referent
set, closed estimator/generator/graph implementations, numeric thresholds,
required core/crossed cells, exact stress strata, and Level-0 authority
boundary. The recorded official result passed this D0 contract; that pass
defines only the engine/protocol scope serialized in the gate.

### D1 — analytic correctness

Known positives and negatives must behave correctly in the separately
implemented representation and Cartesian Fourier construction families. This
is construction and implementation diversity, not a claim of institutional or
epistemic independence. The Cartesian family provides nonzero-with-core,
null-with-core, null-without-core, and prerequisite-failure controls with
estimator-visible inputs separated from oracle truth. Runtime evidence, not
declarative booleans, is bound into the result evidence root. After each
estimator output is sealed, an evaluator-side scorer records exact per-graph
amplitude, support, harmonic/direction, and gauge-invariant phase-law errors
against frozen thresholds; D1 failure IDs are derived from those numeric
receipts.

The metric contract is closed: Cartesian amplitude, second-harmonic, and
split-disagreement metrics use `d1_numeric_tolerance`; Cartesian direction
uses `d1_cartesian_direction_cosine_floor`; representation amplitude uses
`d1_numeric_tolerance`; representation phase coherence uses
`d1_representation_phase_coherence_floor`; and both support metrics require
exact zero. Each metric also has one exact comparator. Validation of an
attempted result requires the full live-verified source-binding companion,
reruns both D1 families under the current engine with the fixed development
seed, and requires canonical-byte equality with the persisted D1 receipts.
That rerun does not read or consume selection seeds.

This is a deterministic procedural cross-check inside the declared local
source-binding boundary. It is not cryptographic proof that source or runtime
was untampered, and it does not attest an independent or native runtime.

The representation estimator's D1/D3 checks do not transfer the Cartesian
D2-D5 result to that estimator. The result schema therefore keeps
`representation_d2_d5_qualified=false`; D6 must require either
representation-native D2-D5 evidence or a separately reviewed
construct-equivalence bridge.

### D2 — prerequisite semantics

Amplitude, gap, coherence, orientation, branch, and support failures produce
the correct gate state and reason. Known-core localization, off-core
rejection, and density- or sparsity-induced false-core controls behave as
declared without loop inputs. A `GroundTruthAnchor` may qualify conditional
loop mathematics but cannot count as a successful localization.

The current engine makes this a separate core-only matrix. Its charge-blind
localizer consumes amplitude, identifiability, coherence, support, and the
declared field graph. It does not receive loop rows, sampled totals, supplied
charge, or expected loop outcomes. Core predictions are collapsed across the
field-graph axis for D2. At execution time each charge-blind core prediction is
sealed before the loop prediction, but the loop kernel does not consume that
core outcome; oracle core anchors and loop truth remain hidden until every
prediction for the primary unit is sealed.

The core predicate is localized same-section low amplitude alone. At an exact
zero the normalized direction is undefined by construction; an independent
identifiability threshold is not part of the candidate predicate.
Identifiability, coherence, and support are measurement-eligibility checks on
the non-core support. Candidate-site degree support is checked independently.
The protocol additionally freezes a selection-seed-free two-by-A falsifier
matrix. A high-amplitude off-center row with local identifiability loss must be
evaluable `no_core`; a low-amplitude row whose incident measurements are
removed must abstain with exactly
`candidate_measurement_support_below_minimum`. This typed runtime matrix
participates directly in D2 rather than becoming a false-core failure only
after an oracle label is opened.

This D2 result is a Level-0 localized zero/core candidate only. It is not a
vortex certificate, topology or charge claim, or proof that a later loop
observable joins the candidate.

### D3 — gauge and basis behavior

Projector and holonomy invariants survive their declared gauge group.
Projection-dependent baselines change only as declared. Any eligible
local-frame integer uses its frozen trivialization/reference or
connection-corrected lift and passes its transformation tests; otherwise the
integer path remains disabled.

The present D3 engine reruns the representation input, all three field graphs,
the discrete domain and matched cycles, the field estimator, and the blind
loop estimator for both the base and ambient-transformed input across every
three-A-by-three-B cell. It persists the fitted O(2) alignment determinant and
requires the unrounded sealed loop total to obey that determinant's signed
law. A small aligned-array error alone cannot pass: in particular, a
determinant-negative Procrustes alignment must be accompanied by a sign
reversal of the independently rerun loop total.

Reference rotation, reference reflection, and loop reversal are also rebuilt
as distinct `BlindLoopInput` variants and passed through
`estimate_and_seal_loop`; their input identities, prediction identities,
signed totals, determinants, and errors are round-trip validated in the full
D3 receipt. The older array-level metamorphic checks remain secondary
diagnostics rather than substitutes for these pipeline executions. All of
this remains fixed-development-seed, oracle-free Level-0 evidence. No integer
or topology path is enabled.

### D4 — graph construction

Required families are deterministic, genuinely distinct, and supported. The
full crossed matrix qualifies on selection phantoms. The charge-blind core
prediction is sealed before the loop prediction, while both core-anchor and
loop oracle truth remain hidden until all predictions are sealed. The loop
kernel receives neither the core prediction nor its anchor. A graph-based core
estimator either inherits the bound field graph or passes its declared
three-axis core-by-field-by-cycle design.

The present crossed engine executes field graph A by cycle graph B by loop-role
cells over one exact discrete domain and matched boundary refinement. The
field-sensitivity sentinel must demonstrate both exact A-graph consumption and
a frozen minimum RMS change in substantive field outputs; changed graph IDs,
adjacency digests, or one-bit content digests alone are insufficient. Loop
evaluation persists an unrounded integrated signed sampled-phase total and its
graph-family span only. It does not persist an integer winding or claim
topology. Engine availability still does not make D4 `pass`.

### D5 — specificity and coverage

Required positive, null-with-core, and null-without-core controls behave as
preregistered. Worst-case required strata meet their frozen coverage,
abstention, recall, and specificity gates. Additional shuffled or rewired
families remain later extensions unless they are named in a future exact
protocol manifest.

The current contract requires the exact `boundary`, `state-geometry-warp`, and
`structured-observation-perturbation` stress-level manifest at the
phantom-instance unit. The first numeric construct deterministically maps each
fixed grid coordinate \(x\) to
\(x+s\sin(\pi x)/\pi\), for \(s\in\{0,0.1\}\), before the state feature
embedding; the grid cardinality does not change, so this is not a
sample-density intervention. The second adds
\(a\cos(\sqrt{2}\alpha+\phi_{\mathrm{seed,row}})\), for
\(a\in\{0,0.01\}\), to the observed values. It is a deterministic
row-seeded term, not stochastic measurement noise.

The closed two-seed declaration has four matched controls and eight paired
stress variants in each declared seed block: 64 execution variants, not 64
independent replicates. The protocol explicitly records that seed-block
independence is unproved and that no inferential sample size is claimed.
Boundary changes the loop construction but not the Cartesian generator or
field fit. D2 therefore requires exact equality of the identity-free
estimator-input fingerprint and candidate/anchor observations across
central/wide repeats and then counts 32 unique scientific input units. Missing
or disagreeing repeats fail closed; D4/D5 preserve all 64 loop execution
variants.

Graph cells are repeated nuisance measurements, not independent replicates.
Nonzero and null controls form the rate denominator. The designed
prerequisite-failure control is excluded from those rates but remains mandatory
and must end in the correct insufficient/abstain state; forced output, a wrong
reason, or `not_run` blocks D5. Every expected primary must pass.

Every serialized verdict also carries its positive claim scope. D0 is limited
to engine/protocol contracts; D1/D3 cover the Cartesian surrogate and
fixed-development representation checks; D2/D4/D5 cover the Cartesian
surrogate only. These scopes cannot authorize representation D2-D5 transfer.

### D6 — scope-limited advancement freeze

The terminally recorded D0-D5 result may advance only the exact
`f2-cartesian-surrogate-d2-d5-v0-1` profile to an independent-family
confirmation gate. The D6 decision binds the exact protocol, freeze, claim,
launch authorization, terminal manifest, consumption, result, evidence root,
gate scopes, required cells, graphs, thresholds, stress strata, aggregation,
and coverage rules.

That decision does not advance a P0 hypothesis or the representation
estimator. It fixes P0 winner selection, representation D2-D5 transfer,
localized core-loop join, integer/topology output, semantic authority, and
subject access to false.

The recorded decision is
`experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/d6-surrogate-advancement-decision.json`
with canonical SHA-256
`c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07`.
It binds source commit
`7673ef81bbd67afce5d20255cc6ca6d68e453c3f`, was first tracked in
`1fcff8bfedc7d3ae8386bc409595607b5b57b8c4`, and passed the clean
tracked authoritative reload. The loader additionally requires the complete
current loader source surface to equal the tracked blobs of one stable current
HEAD and returns that commit plus its source-binding digest. This is a
clean-execution-surface check, not a historical compatibility claim. The
receipt therefore does not change its explicit false values for current-source
compatibility, historical reexecution, or historical D1 recomputation.

The pre-run D0-D5 `SelectionFreezeArtifact` is a different object: it binds one
unopened selection attempt to exact protocol bytes and a seed-family
commitment. It does not decide which instrument advances and cannot satisfy
D6.

The D6 admission specification is embedded in the single decision bundle and
sealed before any confirmation values are accessed. It requires a distinct
mathematical construction family, the same required case semantics, surrogate
estimator and trivialization, implementation registry, graph axes, separate
core and loop paths, stress strata, cell manifest, thresholds, and aggregation;
selection and confirmation evidence must be content-disjoint. Policy overrides
and post-selection exclusions are forbidden. A different seed, source digest,
or implementation label inside the same construction family cannot satisfy
this gate. The no-access fact is an external attestation rather than
cryptographic access proof.

The subsequent seed-free D7 implementation found that two D6 v0.1 bodies are
not portable as literal confirmation manifests. The required-cell body embeds
selection seeds, control IDs, and seed-bearing unit/cell IDs; the
required-stress body embeds the same primary IDs in stratum memberships. A
new-seed confirmation can preserve an exact structural bijection but cannot
be byte-identical to those two bodies without reusing selection identities.
The historical D6 bytes are not reinterpreted or rewritten. A reviewed,
versioned successor rule is required for D7 without changing the historical
exact admission.

That narrower proposal is now encoded internally as
`spirallens.d6-d7-structural-rebinding-amendment.v0.1`. It carries graph axes
and thresholds forward with exact byte identity and allows cells/stress to
fulfill only a D7 successor contract: both successor manifest identities must
differ from the selection identities while the typed structural-projection
digests match exactly. The ordinary or novel factory and the strict reader
reconstruct the seed-free design from the authoritative D6 receipt and strict
parent protocol; neither accepts caller-supplied digests as authority. No
amendment artifact is published, no family is admitted, and the D6 v0.1 exact admission remains
false. Historical D6 bytes are unchanged.

### D7 — locked independent calibration

The one-shot confirmation applies D6 without overrides, exclusions, newly
required cells, or required cells being removed. All non-advanced competitors
remain visible as frozen selection outcomes.

D7 is currently `not_run`. Unopened Cartesian seeds would provide a locked
replication, not construction-family independence.

The spectral-moment lane now has a seed-free execution design that:

- for ordinary or novel construction, requires the authoritative D6 receipt
  and strict full parent protocol;
- reconstructs every parent design-body hash;
- requires explicit boundary, state-warp, and observation-perturbation
  assignments;
- materializes exactly 64 seed-slot primary units, 192 core cells, and 1,152
  loop cells;
- binds the exact three A and three B graph families plus both loop roles; and
- executes the current development field estimator and blind
  core/continuous-loop kernels on permanently excluded development seeds
  without supplying an oracle-truth record to those kernels or producing a
  gate/result.

The `D7ParentD6Binding`, confirmation foundation, and execution design began as
internal `v0.2` drafts. Their canonical identity omits the
validation-time current-loader HEAD and source-binding digest so unchanged
historical inputs remain stable across clean descendant commits. Their ordinary
or novel builders still require and validate the authoritative typed D6 loader
receipt; the loader surface remains a validation-time prerequisite rather than
canonical D7 identity. C1 now embeds the stable seed-free projection of that
design in one canonical candidate.

PR26 adds one private, recorded-C1-only archival reconstruction route for the
fixed producer. It first verifies pinned C1/C2, loads the exact parent protocol,
reconstructs the typed design from the C1-embedded binding, and requires
whole-document equality with the design recorded in C1. It is not a general
alternate construction path or a historical reinterpretation of D6 or C1, and
it accepts no caller-authored design.

The corrected item-21 source anchor defines the remaining positive-authority
boundary as three separate tracked artifacts in fixed order: exact
source/runtime receipt, seed-free readiness, then scoped reviewed
successor-family admission. It issues none of the artifacts and freezes all
item-21 documentation. The receipt is the only addition in its direct-child
commit, readiness the only addition in the next direct child, and admission the
only addition in the next direct child. No merge, intervening change, combined
artifact or documentation commit, or embedded future-child identity satisfies
this receipt-only chronology. Item 21 is partial at the source commit. The
three artifact-only children add and strictly reload/rejoin the chain,
completing item 21 at the final corrected tip.

Historical reload remains tied to the corrected source-anchor tree and runtime-lock
blob. The current-readiness check separately rejects later live source or
runtime drift. Full HEAD-reachable artifact history must contain one exact
direct-child introduction; every later path event must remain on its descendant
lineage with the identical `100644` blob. Historical source reconstruction
uses the issuer's per-member and aggregate caps, and live readiness requires
the anchor and HEAD plus every bounded source-path event on their descendant
ancestry to retain the exact source tree. Merged-away artifact or source
mutations and exact source reverts therefore fail rather than being laundered
by endpoint equality.

Since item-22 orchestration is not introduced here, any
source-changing implementation PR must first create a reviewed, versioned
exact-current source/runtime re-anchor at the separate fixed pre-claim path
`item22-current-source-runtime-reanchor.json`, outside the reserved
`item22-seed-supply/` namespace, and bind it to the item-21 chain. That
re-anchor precedes the exclusive item-22 claim and every supplier call.

That is implementation conformance, not D7 execution evidence. Committed C2
verifies only the declared historical Git source set; the final corrected chain
separately adds exact source/runtime receipt, seed-free readiness, and scoped
reviewed successor-family admission. Concrete confirmation seeds, seed-bearing
target admission, freeze, lifecycle, authoritative target binding, official
terminal publication, and isolated replay remain absent. The deep-internal
persistence-only slice can now record
and reload a caller-supplied primary declaration-through-start record prefix as chained
false-authority envelopes in a dedicated evidence-only lane without
replacement. It grants neither execution nor scientific authority, cannot be
promoted in place, and rejects isolated replay before writing any stage.
PR #23 separately adds a canonical, non-authorizing structural candidate for
a concrete subset of later launch-authority prerequisites. Its target-shaped
record uses dedicated caller-claimed admission, exact-full-design, and
exact-source/runtime candidate leaves, all with
`identity_authenticated=false`. Typed exclusive-supply-claim and
single-supplier-invocation inputs causally join the supplier, development and
parent registries, readiness, caller-alleged admission and source/runtime
receipts, official inventory, and atomic inventory/full-design/target
publication; all verification fields remain false. The physical input carries
the target-and-primary-role-derived attempt key, positive distinct
store/lane and parent device/inode coordinates,
and persistence-reserved path exclusions. The artifact binding has no raw
`from_bytes` factory. The bundle loader applies its size cap, verifies the
digest before parsing, translates canonical parse failures, and proves only
canonical bytes and structural joins. It does not authenticate any issuer,
establish registry provenance, observe path absence, reverify a runtime,
reserve a namespace, invoke a supplier, or authorize a start.
C1 records a declared static-bounded construction review, stable design, D7
registry/aggregation application, successor review contract, and complete
declared Python source set; C2 changes only the historical Git source-set
closure state. Runtime and transitive dependency closure are unattested and
lie outside C2's scope. Accordingly, no open-mapping or label-only D7 admission
function exists. See
[`D7_CONFIRMATION_EXECUTION_DESIGN.md`](D7_CONFIRMATION_EXECUTION_DESIGN.md).

The recorded ordering is:

1. C1 records the declared source set while embedding neither its future commit
   nor a source-closure receipt;
2. the unique receipt-only C2 child of exact post-merge C1 verifies ancestry
   and the exact declared C1 source blobs without adding a design choice; C2
   does not execute historical code or attest Python/native runtime,
   transitive dependencies, in-process identity, hostile-local-mutation
   resistance, or current compatibility; and
3. the replay target and attempt envelope are now typed separately; the local
   evidence lane preserves only
   `caller_supplied_start_record_present_terminal_absent`; and PR #23 exposes
   the typed, caller-claimed authority-prerequisite input boundary as a
   non-authorizing structural bundle rather than a capability.

This addition does not revise any earlier artifact or decision. Canonical
caller records, their digests, and serialized “capability” labels remain
caller-controlled data. They cannot be upgraded into authority in place.
Their authority and verification fields remain false; the item-21
issuers/loaders do not promote them or accept them as substitutes for the three
tracked positive artifacts.
Registry completeness is evaluated only against the explicitly bound registry
sources and counts; it is not evidence that a trusted supplier or historical
parent was consulted.

Roadmap item 19 now adds mechanics without changing that authority boundary.
One deep-internal writer stages a complete structural scientific-result or
failed-attempt inventory, hardens descriptor-relative publication against
races, staging remnants, symlink/hardlink/FIFO/unknown-member substitution,
and file-identity drift, publishes it by native no-replace directory rename,
and strictly reloads it. A private primary-only post-start runner handoff
validates the complete target projection and six-component result behind a
single zero-argument producer callback. Roadmap item 20 now issues that
ownership only inside one deep-internal raw-descriptor → canonical
`origin/main` → declared source/runtime, callable/process, physical identity,
and absence observation → no-replace start transition. Repository/store tree
disjointness is proved by descriptor-relative device/inode ancestry rather
than path spelling. It requires start-parent
fsync proof, repeats those observations after the start becomes visible, and
consumes ownership before callback entry. Every exit after ownership
construction invalidates both callback entry and terminal publication,
including a failure before runner dispatch. The runtime surface is limited to
tracked `src/spirallens/**`, `pyproject.toml`, the required runtime lock, exact
equality of the complete installed distribution name/version inventory,
interpreter executable bytes, producer source/code identity, and selected
process-envelope fields. It does not close
installed package files, loaded native libraries, mutable module globals,
callable defaults or closures, unrecorded environment state, model state, or
data state. No caller can supply or receive ownership. A separate PR26
deep-internal surface fixes the zero-argument official producer and exact
full-inventory, aggregation, and full-design builders behind the callback
boundary; it does not create an official invocation or authority artifact.

The strict start loader grants no authority and explicitly does not establish
`started_unresolved`. The fused call makes at most one terminal-publication
attempt. Hard exit or `BaseException`, post-start drift, unproved start-parent
fsync, or success/failure publication error can leave a visible structural
start with no terminal and retry still forbidden. If an ordinary exception
does publish a visible failed terminal whose final parent fsync is unproved,
the fused path makes a best-effort attempt to attach its terminal identity and
durability warning to that same exception.

For external aborts, a canonical two-signature Ed25519 observer/verifier
envelope is a required closed-inventory member. The integrated path verifies
against explicit runtime pins only after atomically consuming callback entry
and prepared-terminal publication. It performs fixed live
prefix/terminal-coordinate revalidation, derives the finalization and terminal
records, publishes without replacement, and strictly reloads; existing
terminals can be strictly
reauthenticated to the same pins. This is authentication relative to those
pins only. It establishes no pin/trust-root provenance, official authority,
wall-clock freshness, authoritative start, observed execution, scientific
eligibility, retry/replay authority, D7, or D8. No supplier or official seed
was used, and no official execution occurred.
The item-19 finalizer accepts only the evidence-only loaded prefix; it cannot
accept or reauthenticate the item-20 authoritative-start transaction.
Authoritative-start-compatible external-abort integration therefore remains a
pre-item-24 blocker.

The next execution-preparation order is:

1. retain the completed terminal transaction, external-witness verification
   relative to explicit pins, and typed runner mechanics as non-authorizing
   and non-scientific;
2. retain the completed fused verify-and-exclusive-start mechanics without
   creating an official descriptor or officially invoking them; their canonical
   `origin/main`, declared source/runtime and callable/process, disjoint-store,
   two-pass absence, no-replace start plus parent-fsync proof, and one-callback
   checks emit no reusable authorization token;
3. retain item 21's exact `requirements-d7-runtime-lock.txt`, fixed
   zero-argument official producer, exact full-inventory, aggregation, and
   full-design builders, and installed-inventory equality check as code-side
   ingredients only; after all item-21 source is final, add only the exact
   source/runtime receipt in its direct-child commit, only seed-free readiness
   in the next direct child, and only scoped reviewed successor-family
   admission in the next direct child; strictly reload and rejoin all three
   before item 21 is complete;
4. if the execution-source surface changes, first publish and review the
   fixed-path exact-current re-anchor bound to item 21; only then acquire the
   exclusive seed-supply claim, invoke the supplier once, publish the exact
   seed-bearing target and full design atomically, commit their freeze, persist
   launch intent after that freeze, and execute item 23's already separated
   descriptive result without changing D7 design bytes;
5. before item 24, create and commit the closed nine-member fused descriptor
   and pass strict verification-evidence replay/rejoin, recognizing that
   structural replay preserves but does not recompute or independently
   reauthenticate its live-observation digests and that terminal lineage binds
   the evidence bytes only; pass temporary Git/runtime end-to-end validation
   and authoritative-start-compatible external-abort integration; and
6. make item 24 the first official fused invocation, requiring an exact
   terminal outcome and complete isolated byte replay.

Nothing in the corrected source anchor or its three artifact-only children performs
item 22. Even at the final corrected tip, no exclusive supplier claim or invocation,
official seed inventory, atomic seed-bearing target/full-design publication,
or committed freeze exists. Launch intent, the canonical
nine-member descriptor, an official invocation/start/run/terminal/result, D7,
and D8 also remain absent or `not_run`.

The terminal schema keeps the immutable replay target separate from
the attempt envelope that binds launch authorization, exclusive claim,
execution start, success/failure, and terminal lineage. A placeholder result
must not stand in for either object.

### D8 — freeze and replay

The complete synthetic-qualified bundle is byte-replayable and records every
unresolved choice and claim ceiling.

D8 is currently `not_run` because D7 has not passed and no isolated full-bundle
replay exists. A future replay must compare complete canonical bytes in a
separate namespace; replay demonstrates determinism and is not counted as a
second independent confirmation.
There is no D8 promotion helper that can pass from two caller-supplied byte
strings; typed D7, execution, namespace, source, and replay receipts are still
required.

### Post-D6 analysis is split before either lane runs

The already-opened PR #9 terminal may be inspected only under the canonical
`postselection_descriptive_only` plan. That lane declares prior outcome
exposure, fixed scientific grains, eight mandatory descriptive packages,
`claim_delta=none`, and an absolute prohibition on D7 design use. It also
records that planning used opened outcome values; only its runner and result
remain unexecuted.

A separate canonical D7 structural gap matrix may inspect only the D6 decision
and a tracked source snapshot. It cannot read the terminal result, terminal
manifest, consumption, Pythia engineering values, subject values, or unopened
confirmation values. Its closed vocabulary is `absent`, `contract_only`,
`implementation_foundation_only`, `evidence_present_but_ineligible`, and
`blocked`; it has no completion percentage, weighted score, candidate, or
admission state.

Both artifacts are frozen but unexecuted. PR #11 adds no public analysis
runner, writer, D7 admission helper, or promotion API. The detailed chronology,
unit contract, work packages, gap rows, and full research sequence live in
`docs/POST_D6_ANALYSIS_AND_D7_GAPS.md`.

There is no independent operator or information barrier. Therefore the
complete D7 family descriptor, admission, protocol, declared Git source-set
closure, graph/case/stress and aggregation bytes, lifecycle, launch intent,
exclusive attempt, and absent result namespace must be frozen under a
committed receipt before the descriptive runner may execute. Runtime and
transitive dependency closure remain separate obligations. Any later D7
design change requires a new version and review; the prior admission cannot be
carried forward.

Any required failure stops. Any required insufficient result blocks. A
complete applicable D0-D8 chain is necessary before later subject-protocol
preparation, but the current surrogate-engine D7/D8 lane is not sufficient and
grants no subject authority. Representation-native selection and independent
confirmation/replay, a same-substrate field/core/loop join, and the separately
reviewed instrument gates below must also complete. None of these authorize
subject execution.

For the current D0-D5 result schema, `d6_d8_advanced=false` and
`synthetic_qualified=false` are invariants. The scope-limited D6 admission
decision does not alter those bytes. Global D6-D8 therefore remain unadvanced
until a separately implemented family passes locked confirmation and complete
replay under a separately reviewed promotion contract.

## 10. Decisions allowed now

The following may be prepared without subject observation:

- hypothesis registry and mathematical transformation laws;
- per-hypothesis claim ceilings;
- artifact schemas and canonicalization;
- separate `GroundTruthAnchor` and charge-blind, field-bound
  `CoreCandidate` receipts plus localization tests;
- phantom-family specifications and hidden split assignment;
- graph constructors and deterministic tie-breaking;
- crossed-cell manifest;
- failure vocabulary and nonnumeric reason codes;
- evaluation units, coverage/abstention strata, and aggregation schemas;
- split/access policy;
- preregistered selection rubric;
- replay and adversarial-review checklist.

The P0 registry, metadata-only canonical schemas, and closed-integrity bundle
validator are now implemented under this allowance. Their exact boundary and
remaining non-claims are recorded in
[P0 Hypothesis and Artifact Contracts](P0_HYPOTHESIS_AND_ARTIFACT_CONTRACTS.md).

The commit-stable internal D7 `v0.2` draft identity and historical `v0.1`
successor structural-rebinding proposal remain preparation-only contracts.
The separately recorded C1 candidate preserves them and adds a review contract,
declared source set, registry, and aggregation application. The committed C2
receipt verifies that historical Git source set only. It selects no seed,
admits no family, and creates no lifecycle, terminal, D7, or D8 evidence.
Runtime and transitive dependency closure remain unattested.

A separate public-example engineering lane may validate the already
implemented model observation apparatus. It requires a pre-execution protocol
with `execution_class=public_example_engineering`, an `example` ContextBank
with claim eligibility disabled, exact bounded rows, offline model-file
verification, resource ceilings, and an atlas-only consumer allowlist. The
receipt must state that the model was accessed and activations were persisted.
Every scientific and structural downstream stage remains `not_run`; the atlas
cannot enter candidate, neighbor, instrument, graph, field, core, loop,
semantic, SAE, or integer consumers. This lane neither prepares nor executes a
subject experiment and does not advance D0-D8.

## 11. Decisions that remain unresolved

Until independent calibration, do not select:

- a winning or advanced field/geometry hypothesis;
- covariance, weighting, neighborhood, or residual source for the fixed
  rank-two F1/F2 hypotheses;
- effective-rank, gap, coherence, or amplitude floors;
- projection or whitening method;
- graph scales or optional-family inclusion based on observed field behavior;
- cycle constructor, radius, or sampling count;
- holonomy or winding tolerances;
- orientability and U(1) eligibility;
- whether any integer output is authorized at all.

The exact mutual-kNN/Euclidean/\(k=6\) cell above does not resolve these
decisions. It is an `instrument_dev_executed` implementation cell only. No
cycle constructor, radius, or loop sampling count was run in that cell.

Subject model, context, layer, semantic interpretation, SAE comparison, and
topology promotion remain outside this preparation document.

## 12. Future subject-access boundary — not unlocked by surrogate D8 alone

Here, “post-D8” means after the complete applicable qualification chain, not
merely after the current surrogate-engine replay. Before any subject manifest
is issued, the representation-native F0-F4 instrument must be separately
selected, confirmed, and replayed; the same-substrate field/core/loop join must
be established; and any calibration-side integer/topology eligibility required
by the chosen convention must be frozen. These are still instrument
qualifications, not an observation of model topology.

A later `SubjectProtocolManifest` must pin the model and immutable revision,
ContextBank and roles, context and layer scope, evolution axis, frozen
instrument-bundle digest, field and graph specifications, run budget, output
identity, and claim ceiling before subject-derived tensors or diagnostics are
visible.

The subject `prepare-only` operation may validate identifiers, file presence,
schemas, and trusted digests. It may not load subject activation values,
estimate a field, construct a subject graph, inspect support or eigenspectra,
localize a core, or observe a candidate. Subject-data access requires a
separate, explicit execution authorization after manifest review and freeze.

Prepare-only consumes only a canonical descriptor created before observation.
It does not read an atlas manifest and redact it: a manifest contains
outcome-bearing summaries, run state, array digests, and other data-derived
facts. Paired canary payloads with the same descriptor must produce
byte-identical preparation output and a read trace containing only that
descriptor. The provisional framework-neutral implementation lives in
`spirallens.access`; it establishes an access mechanism, not a
`SubjectProtocolManifest` or subject-preparation authorization.

Value-derived provenance uses a monotone restriction operation. Any authorized
product that consumes values from the public-example engineering lane must
retain its claim-ineligible engineering taint. A free-standing policy object is
not lineage proof; the first numeric consumer must persist an explicit
parent-policy digest so copying or reserialization cannot masquerade as a
verified derivation.

Execution lifecycle is independent from D0-D8 gate state. The protocol freezes
same-attempt resume, output reuse, fresh replay, post-outcome retry, and
relabel policy separately. Once a hidden outcome is opened, correction
requires a new protocol identity and unopened family.

For D0-D5 selection, the official process first verifies the seed-free
executable source-set closure, which does not attest runtime or transitive
dependency closure, publishes and strictly reloads a canonical no-overwrite
readiness artifact, and only then invokes its seed supplier. The
resulting exact canonical protocol and unopened freeze bind that earlier local
artifact's path and digests and are committed as F. This is
`official-process-attested` ordering, not cryptographic or
human/external-process unseen proof. After F is fully revalidated, the local
chronology store persists and strictly reloads a launch intent before it
acquires one freeze-keyed exclusive attempt claim. The store freeze, intent,
claim, and descriptor must all be committed as exact clean tracked G blobs. A
fresh descriptor loader derives execution authorization only after checking
all four against one unchanged G HEAD, and the official runner repeats that
check before start. It also live-reverifies the complete executable source
closure, including the three official prepare/launch/run scripts, and
atomically creates a separate freeze-keyed execution-start marker immediately
before generation. The marker stores the descriptor-derived authorization
digest and authorized G HEAD, survives exceptions, and therefore rejects every
second call. A success result or typed failed-attempt artifact stores the same
authorization digest and is published with its consumption receipt and
manifest in one atomic terminal directory. Publication and reload require the
same typed authorization, prove
`engine commit -> authorized G -> current HEAD`, verify the four G artifacts
are unchanged at authorized/current commits and in the clean worktree, verify
that start/terminal paths were absent from G, and require the terminal digest
to match the persisted start. Result publication and reload also repeat full
protocol and live-source validation, including the exact intent/claim join.
Neither terminal kind may be replaced by a second outcome. A crash after
execution start leaves both claim and start marker in place and does not
authorize retry.

If the terminal artifact is subsequently committed, publication/reload does
not substitute the new HEAD for the source receipt captured during execution.
The successor verifier proves
`engine.commit -> stored execution HEAD -> current HEAD`, validates the current
clean executable source-set closure, checks every bound module, official
executable, registry, and referent blob at the execution HEAD, reconstructs
that exact historical receipt, and calls the existing summary-to-receipt
exact-digest verifier. Thus
an artifact-only descendant is admissible, while a sibling history, mismatched
execution blob, or current path/content drift fails closed.

The official package surface exposes
`run_and_publish_calibration_selection`, which owns execution start, result
validation, and terminal publication in one call. The in-memory
`runner.run_calibration_selection` path is development-only and is not
exported. After the official call owns the start transition, any Python
execution or result-publication exception first emits a conservative typed
failure with `attested_selection_values_observed=true`, then re-raises the
original exception. If a result or failed terminal became visible before the
publication call raised, only the exact expected terminal is strictly
reloaded; the attached typed receipt records that the call did not return and
that parent-directory fsync durability is not proved. A process kill cannot
execute that handler. A valid claim-plus-start store with no terminal
directory is therefore a read-only terminal-aborted state: it must not be
resumed or retried, and requires forensic inspection followed by manual typed
failure publication.

Raw provisional record construction is not an official evidence sink.
Standalone qualification-result write/load APIs reject the official protocol
ID; only the start-lineage-bound terminal transaction can persist or reload an
official result. Custom/development execution and standalone persistence remain
separate and accept no launch authorization.

The official one-shot is launched from a fresh interpreter at clean G after
its engine, F, and G commits. The local callable-binding check catches
accidental alias replacement only; it does not attest a hostile Python process
or native runtime. Terminal directory publication uses an exclusive Darwin or
Linux rename primitive and fails closed where that primitive is unavailable.

This is a practical local uniqueness boundary, not cryptographic or
adversary-resistant access proof. It trusts the external attestations and the
operator's store-deletion discipline. A future durable store must make claim,
execution-start, and terminal history append-only across administrative deletion and
multi-host execution.

Successor verification is still source-only Level-0 evidence. It does not
attest the in-process callable graph, Python/native runtime, or hostile local
mutation resistance.

This section defines a future access boundary only. It does not create a
subject manifest or choose a subject in the present work.

The pre-D8 public-example engineering carve-out above is disjoint from this
boundary: it authorizes only claim-ineligible atlas capture and integrity
reload, never a subject role or a downstream observation.

## 13. Preparation completion

Preparation is complete only when a source-pinned, synthetic-qualified,
content-addressed bundle passes D0–D8 and an adversarial review confirms:

- no prior subject outcome selected the instrument;
- no field or graph family was dropped after observation;
- every required failure mode is replayable;
- geometry and topology outputs remain separate;
- the next step is still subject `prepare-only`, not subject execution.
