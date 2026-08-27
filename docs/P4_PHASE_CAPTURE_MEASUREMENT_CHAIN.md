# P4 Phase-Capture Measurement Chain — Design v0.1

**Status:** `planned_not_frozen_not_run`

**Decision date:** 2026-08-27

**Claim ceiling:** design-only Level 0

**Execution, model, subject, network, and Pythia-160M authority:** false

This document designs the measurement chain needed to pursue F2/F4,
model-derived order-parameter fields, charge-blind core candidates, relative
holonomy, sampled winding, operational phase-like regimes, and transition
candidates. It does not freeze an executable P4 v0.3 protocol, choose numeric
thresholds or inputs, authorize a launch, or report an observation.

The design is a successor input to the consumed P4 v0.2 terminal. P4 v0.2
showed that one calibration-fixed absolute graph-parameter triplet did not
remain jointly evaluable under its held-out seed/density-warp nuisance. That
result is treated as a reception-layer falsifier, not as evidence for or
against phase, transition, holonomy, winding, F2, F4, an order parameter, or a
core.

## 1. Outcome sought

The target is not one scalar called `phase`. The target is a provenance-bound
chain whose outputs retain their separate meanings:

| Target | Required object | Earliest possible reading | Explicit nonclaim |
| --- | --- | --- | --- |
| F2 | cross-fitted local O(2)-covariant vector section | pointwise/support observation | not yet an order parameter |
| F4 | cross-fitted local spin-two traceless-tensor section | pointwise/support observation | not an ordinary vector field |
| order parameter | same-object section, amplitude, direction, gauge law, interpolation, and substrate binding | Level 1D candidate | not automatically a core or topology |
| core | charge-blind same-field degeneracy rule sealed before loop readout | `CoreCandidate` | not a verified singularity by score alone |
| holonomy | relative transport around a declared closed path | Level 1G | continuous; not integer charge |
| winding | sampled angle increment of an eligible order-parameter section | Level 1D | not topology before Level 2T controls |
| operational phase-like regime | a stable distribution of same-object angles/amplitudes under a declared gauge and support region | model-internal candidate | not thermodynamic phase or semantics |
| transition candidate | held-out change on a predeclared ordered axis, above the qualified detection surface | model-internal structural candidate | not causal or semantic before Level 3 |

The unqualified persisted field name `phase` remains forbidden. F2 uses its
order-parameter angle; F4 persists its doubled-angle spin-two coordinate and,
when needed, a director angle modulo π. Geometry-branch transport angle remains
separate from both.

## 2. Ordered measurement chain

```text
M0 freeze identities, roles, budgets, and no-read chronology
  -> M1 qualify field-blind graph-scale transport across nuisance definitions
  -> M2 construct F2 and F4 as co-primary cross-fitted sections
  -> M3 bind each eligible section into its own OrderParameterSpec/Field
  -> M4 seal charge-blind same-field CoreScore/CoreCandidate before loop readout
  -> M5 bind nested/reverse/off-core loops to declared domain classes
  -> M6 geometry branch: connection and relative holonomy
  -> M7 defect branch: boundary-eligible sampled winding
  -> M8 crossed graph, gauge, architecture, deformation, and null controls
  -> M9 end-to-end synthetic detection-limit surface
  -> M10 held-out checkpoint-axis phase-like-regime/transition confirmation
  -> M11 later semantic/causal intervention bridge
```

Every stage persists `pass`, `fail`, `insufficient`, or `not_run`. A downstream
stage cannot cure or silently omit an upstream required failure. Geometry and
defect are separate branches: either may remain evaluable when the other does
not, and neither inherits the other's claim level.

## 3. M1 — nuisance-robust graph reception

P4 v0.3 should not reuse one absolute `k/r/min_shared` triplet. It should
combine two protections:

1. a predeclared, field-blind, dimensionless parameter-transport law; and
2. worst-case selection of that law's hyperparameters across multiple
   predeclared calibration nuisance definitions.

For vertex count (n), a future freeze may instantiate the following rule
family after exact tie and clipping rules are specified:

\[
k=\lceil\kappa(n-1)\rceil,\qquad
s=\operatorname{median}_i d_{i,(k_s)},\qquad
r=\rho s,\qquad
m=\lceil\tau k\rceil.
\]

Here mutual-kNN uses (k), fixed-radius uses (r), and shared-neighbor uses
((k,m)). The rule may read only row identity, vertex count, the declared
metric's distance/order statistics, and field-blind domain support. It may not
read F2/F4 values, amplitude, direction, core, loop readout, holonomy, winding,
charge, phase-like aggregates, controls, or subject outcomes.

The calibration selector chooses ((\kappa,k_s,\rho,\tau)) by a frozen
lexicographic worst-case objective over multiple seed, density, noise, and
sampling nuisance definitions. It must retain all three genuinely distinct
graph families, common support, matched declared boundary classes, component
and two-core coverage, and the declared edge/degree budget. A separately
sealed held-out nuisance then applies the transport law without reselection.

The graph families do not invent the loop. A two-dimensional intervention
coordinate domain and its oriented boundary classes are declared before graph
construction. Each graph family only answers whether it supports that same
domain class. Construction-specific cycle indices cannot substitute for this
identity.

## 4. M2–M3 — F2/F4 and order-parameter binding

F2 and F4 remain co-primary. No calibration, holonomy, winding, core, or
transition outcome selects a winner.

### F2 branch

F2 observes a cross-fitted local section

\[
z(x)=U_{\mathrm{fit}}(x)^\top s_{\mathrm{eval}}(x),
\qquad A_2(x)=\lVert z(x)\rVert_2.
\]

Under local frame gauge (G(x)\in O(2)), (z'(x)=G(x)^\top z(x)). Its angle
is defined only where the same-object amplitude exceeds the frozen floor and
the reference/orientation contract is resolved.

### F4 branch

F4 observes an in-plane traceless symmetric tensor (T(x)) and its spin-two
section

\[
w(x)=\left((T_{11}-T_{22})/2,\ T_{12}\right),
\qquad A_4(x)=\lVert w(x)\rVert_2.
\]

The persisted angular coordinate is the doubled-angle coordinate
\(\phi_4=\operatorname{Arg}(w_1+i w_2)\). A director angle is
\(\phi_4/2\pmod\pi\). Any later winding is reported under the doubled-angle
integer convention, never as ordinary-vector charge.

Each branch must bind its exact fit/evaluation split, substrate, graph used for
field estimation, interpolation, gauge/trivialization, amplitude floor, and
undefined-direction mask into its own `OrderParameterSpec` and
`OrderParameterField`. A support diagnostic or unrelated transport angle may
not be joined to supply the missing amplitude.

The branch outcome lattice is exactly:

- `both-qualified`;
- `f2-only`;
- `f4-only`;
- `neither-qualified`;
- `insufficient-support`.

`f2-only` and `f4-only` are comparative outcomes, not permission to erase the
other branch. `both-qualified` does not force a winner.

## 5. M4 — charge-blind core seal

Core localization precedes every loop value. For each eligible field, a future
freeze defines a same-field core-degeneracy scalar and nested-radius profile
from:

- the field's own amplitude;
- its own direction-identifiability or frame-conditioning quantity; and
- independent measurement support at the candidate location.

The exact scalar, threshold, nonmaximum/minimum rule, multiplicity rule, and
matching radius must be calibrated without loop, holonomy, winding, or charge
readout. The resulting `CoreScore` and zero, one, many, or unresolved
`CoreCandidate` set are content-addressed and sealed before M5. A supplied
synthetic `GroundTruthAnchor` remains separate and cannot be serialized as an
inferred candidate.

No core is a valid outcome. It permits the geometry branch and no-core defect
nulls to continue, but it forbids a core-centered defect claim. Multiple cores
must retain multiplicity; post-hoc selection of the one with largest winding is
forbidden.

## 6. M5–M8 — loops, holonomy, winding, and controls

### Loop contract

Every evaluated loop binds the declared domain class, orientation, center or
off-core relation, radius, sampling density, deformation family, and supporting
graph-family receipts. Required ensembles include nested core-centered loops,
reverse orientation, off-core loops, loops enclosing multiple candidates when
present, and sampling/refinement companions.

### Geometry branch

M6 estimates a declared local frame/projector connection and relative holonomy
around each eligible loop. It records the continuous group-valued or angular
remainder, path/deformation sensitivity, gauge controls, and architecture
factor accounting. It emits no integer and does not require a core.

### Defect branch

M7 reads only an M3 order-parameter field on an M5 loop whose every boundary
sample is amplitude/identifiability eligible and whose orientation/reference
contract is resolved. F2 uses principal increments of its vector angle. F4
uses the doubled-angle spin-two section. Every unrounded total and
proximity-to-integer residual is retained. Resolution to a Level 2T candidate
requires nested, reverse, off-core, deformation, sampling-density, core, null,
and full graph-cross controls; nearest-integer rounding alone is never an
output authority.

M8 gates the field/phase-like, geometry, and defect branches independently. It
always receives the eligible M3 field plus the M5 support receipts, consumes M6
only when the geometry branch is eligible, and consumes M7 only when the defect
branch is eligible. An unavailable branch stays explicitly unavailable and does
not erase or block another eligible branch. M8 crosses field-estimation graph by
cycle-support graph and adds a core-graph axis when the core estimator is
neither graph-free nor inherited from the field graph. Required controls include
known-positive, fixed/no-core null,
pure gauge, reflection/orientation, basis, degree-preserving rewire,
field-only shuffle, global norm, architecture factors, collapsed support,
zero amplitude, low coherence, non-orientability, loop deformation, nested
radius, and sampling refinement. Required `insufficient` cells cannot be
dropped from worst-case aggregation.

### Operational phase-like regime contract

M10 must return a separate outcome for F2 and F4 at each checkpoint and required
context stratum: `operational-phase-like-regime-candidate`,
`qualified-no-phase-like-regime-detected`, or `insufficient`. The evaluated
object is the same-field joint distribution of eligible amplitude and angular
coordinates. F2 retains its vector-angle coordinate and F4 its doubled-angle
coordinate. Required statistic families include amplitude-conditioned circular
concentration under a sealed trivialization, transport-corrected domain-coordinate
angular correlation, and coherent-support coverage, with statistics and
thresholds frozen before model access.

A candidate requires a held-out departure from matched nulls, adequate M9
sensitivity, and robustness across the required graph, gauge, architecture, and
context controls. A qualified non-detection is restricted to that same
sensitivity/coverage region. F2 and F4 may not be pooled, and core, holonomy,
winding, or transition outcomes may not select the regime statistic. This is an
operational model-internal regime, not a thermodynamic phase, semantic state, or
single global `phase` scalar.

### Partial-pattern registry

Each future checkpoint, together with its declared inter-checkpoint transition
boundary/window, persists one complete pattern record with explicit slots for
F2/F4 section and order-parameter eligibility, per-branch core multiplicity,
geometry relative holonomy, per-branch phase-like regime and sampled winding,
and transition status. Every slot keeps its measurement gate (`pass`, `fail`,
`insufficient`, or `not_run`), typed value or value reference, finding state,
coverage, uncertainty, strata, and reason. A slot may remain unresolved or not
applicable; the record itself is still retained.

`qualified-not-detected` is permitted only after the relevant control gate passes
inside the qualified M9 detection/coverage region. `fail` means the measurement
contract failed, not that the phenomenon is absent. `insufficient` and `not_run`
may never be recoded as absence. Partial co-occurrence patterns are descriptive
until a separate held-out protocol authorizes comparison, and may not select a
graph, field, core, loop, threshold, or checkpoint range.

## 7. M9 — detection-limit surface is not a model transition

Before any claim-bearing model run, synthetic fields enter through every
applicable stage of the full atlas-shaped path: representation injection,
retrieval, exact reranking, graph transport, field estimation, core seal, loop
support, branch readout, and final gates. Per-target/branch surfaces and the
joint partial-pattern surface are both required; an unavailable branch is never
imputed from another. The surface varies at least:

- injected same-object amplitude;
- declared perturbation/noise level;
- sampling density and local candidate density;
- core separation for opposite-sign dipoles; and
- graph/architecture nuisance strata.

It reports detection probability, coverage, abstention, false-positive rate,
uncertainty, and the region in which a later null could be qualified. A sharp
instrument threshold on this surface is a detection boundary, not evidence of
a model phase transition.

## 8. M10 — operational phase-like regime and model-regime transition

The primary future model-transition axis is ordered training checkpoint. Exact
checkpoint identities and range remain unresolved until a separate subject
protocol freeze. Intervention strength is a later causal-probe axis. Layer is
an architectural-depth profile and may not be relabelled as time.

Before any checkpoint comparison, the protocol must seal the exact checkpoint
hash and training step, a common model family/architecture/tokenizer/context and
address domain, and common intervention-domain coordinates. Comparison must use
gauge-invariant observables or an alignment fitted only on the fit partition;
the basis or alignment may not be selected from outcomes. Optimizer, data-mixture,
and schedule discontinuities are declared covariates rather than silently
absorbed into the transition label.

For each checkpoint, the frozen observable panel retains:

- F2 and F4 field eligibility and support coverage;
- same-object angular/order-parameter and amplitude distributions;
- per-branch operational phase-like-regime outcomes and charge-blind core profiles;
- relative-holonomy distributions on the geometry branch;
- unrounded winding/stability distributions on each eligible defect branch;
- graph-family agreement, abstention, and control outcomes.

A discovery partition may fit a bounded change-point model and propose a fixed
checkpoint window. Hidden confirmation then tests that window and the frozen
effect/coverage rules without moving it. A transition candidate requires a
held-out change in at least one field/core observable and at least one
independently computed geometry or defect observable, with overlapping
change-point uncertainty, required graph-family robustness, adequate detection
sensitivity, replication across the required context strata, and no omitted
required stratum. Smooth drift, one isolated spike, coverage loss, or a change
visible only after selecting F2/F4, graph, layer, alignment, or checkpoint range
is not a transition.

A qualified null is restricted to the frozen checkpoint range and the part of
the M9 detection surface with adequate power. Outside that region the result is
`insufficient`, not absence.

## 9. M11 — semantic and causal bridge

Model-internal phase-like or transition structure remains below Level 3. A
later, separately frozen test must use norm-preserving interventions that move
the eligible same-object angle or transport quantity while matching amplitude,
norm, locality, and sham directions. Selective held-out downstream behavior or
logit change under those controls is required before semantic or causal
language.

## 10. Chronology and stopping rules

The future executable chain must seal, in order:

1. identities, roles, budgets, and input definitions;
2. graph transport rule and numeric hyperparameters;
3. F2 and F4 specifications and fit/evaluation partitions;
4. amplitude/identifiability and core rules;
5. core candidates;
6. loop/class ensemble;
7. control matrix and numeric thresholds;
8. checkpoint identity, common coordinates, alignment/covariate rule,
   transition axis, observable panel, and change-point rule;
9. calibration-selection decision;
10. hidden-confirmation access.

The chain stops `insufficient` before field readout if graph reception is not
jointly evaluable. It stops or branches explicitly when field, amplitude,
orientation, core, loop, sensitivity, or coverage prerequisites are unresolved.
It stops `fail` when an evaluable known-positive, required null, covariance,
graph-invariance, or held-out transition rule is wrong. No failure may be
converted to `insufficient` by raising a floor after observation.

## 11. What this design authorizes

It authorizes only a later implementation-planning discussion. The next safe
code milestone is a model-free prototype of the dimensionless graph-scale
transport and multi-nuisance selector, with adversarial round-trip tests and no
official input generation. A separate dated decision is required to freeze
concrete nuisance definitions, transport hyperparameters, thresholds, source,
launch, and exact-one lifecycle.

This document does not authorize P4 v0.3 execution, Pythia-70M or Pythia-160M
access, raw-capture reuse, subject access, a winner between F2 and F4, a model
phase/core/topology claim, SCI-S1/S2 advancement, or scientific/semantic/
publication authority.
