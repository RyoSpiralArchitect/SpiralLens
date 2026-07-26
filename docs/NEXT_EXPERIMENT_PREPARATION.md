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
that lattice addresses are model token positions.

This slice is deliberately below the Stage P1 exit. Graph family, metric,
scale, identifiability, interpolation, lift, trivialization, and reference
choices remain unresolved for qualification even though the executed
development cell binds its exact constructor ID. It emits no core score,
localized core, connection, loop, winding, selection, confirmation, or integer
result. Its paired cases are one analytic generator family, not independent
confirmation. The durable preprocessing receipt binds
`identity-no-preprocessing`, the full protocol content and digests,
`qualification_status=not_evaluated`, `synthetic_qualified=false`, and D0-D8
all `not_run`. Current-environment cold replay is byte-identical; portability
has not yet been evaluated.

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

### `SubstrateBinding`

Bind:

- ordered vertex and observation identities;
- exactly one declared evolution axis;
- raw states and accounted response source;
- masks, dtype, shape, and content digests;
- ContextBank role and split;
- preprocessing fit receipt.

No unqualified field named `phase` or `time` is permitted.
`synthetic_lattice` is accepted only with `role=instrument_dev`; it is excluded
from the P0 model observation-axis candidate set and cannot be laundered into a
subject axis.

### `GraphConstructionSpec` and `CandidateGraph`

The specification binds the graph family, metric, constructor, scale-selection
rule, deterministic tie policy, and allowed role. The resulting graph binds:

- canonical vertices, edges, and weights;
- connected components, degree distribution, two-core, and cycle support;
- substrate, specification, and graph digests.

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

### D0 — definitions

All F0–F4 inputs, transformations, targets, charge groups, interpolation or
transport conventions, outputs, and claim ceilings are complete.

### D1 — analytic correctness

Known positives and negatives behave correctly on development generators.

### D2 — prerequisite semantics

Amplitude, gap, coherence, orientation, branch, and support failures produce
the correct gate state and reason. Known-core localization, off-core
rejection, and density- or sparsity-induced false-core controls behave as
declared without loop inputs. A `GroundTruthAnchor` may qualify conditional
loop mathematics but cannot count as a successful localization.

### D3 — gauge and basis behavior

Projector and holonomy invariants survive their declared gauge group.
Projection-dependent baselines change only as declared. Any eligible
local-frame integer uses its frozen trivialization/reference or
connection-corrected lift and passes its transformation tests; otherwise the
integer path remains disabled.

### D4 — graph construction

Required families are deterministic, genuinely distinct, and supported. The
full crossed matrix qualifies on selection phantoms. Core and anchor receipts
are sealed before any loop observable is computed. A graph-based core
estimator either inherits the bound field graph or passes its declared
three-axis core-by-field-by-cycle design.

### D5 — specificity and coverage

Pure-gauge, shuffled, and rewired nulls are negative as preregistered.
Worst-case required strata meet their frozen coverage, abstention, recall, and
specificity gates.

### D6 — selection freeze

The `CalibrationSelectionDecision` seals advanced hypotheses, required and
diagnostic cells, estimators, graphs, thresholds, aggregation, and coverage
rules before confirmation access.

### D7 — locked independent calibration

The one-shot confirmation applies D6 without overrides, exclusions, newly
required cells, or required cells being removed. All non-advanced competitors
remain visible as frozen selection outcomes.

### D8 — freeze and replay

The complete synthetic-qualified bundle is byte-replayable and records every
unresolved choice and claim ceiling.

Any required failure stops. Any required insufficient result blocks. Only D0
through D8 authorize a later subject-protocol preparation step. They do not
authorize subject execution.

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

Subject model, context, layer, semantic interpretation, SAE comparison, and
topology promotion remain outside this preparation document.

## 12. Post-D8 subject-access boundary

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

This section defines a future access boundary only. It does not create a
subject manifest or choose a subject in the present work.

## 13. Preparation completion

Preparation is complete only when a source-pinned, synthetic-qualified,
content-addressed bundle passes D0–D8 and an adversarial review confirms:

- no prior subject outcome selected the instrument;
- no field or graph family was dropped after observation;
- every required failure mode is replayable;
- geometry and topology outputs remain separate;
- the next step is still subject `prepare-only`, not subject execution.
