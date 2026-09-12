# P4 signal-strength cross sections: fixed prospective exploratory panel

Decision date: 2026-09-04. Status at commitment: specified, not run.
Synthetic development / Level 0 only. The preceding reference-perturbation
results motivated this panel; they do not determine its outcomes. This plan
is committed before generating the new strength-screen observations.

## Question and one changing construction

How do residual magnitude, reference sensitivity, direction, and sampled
winding change as the injected quadratic component becomes weaker?

Keep the substrate flat and use `z=x+i*y`. The clean response has
`F2(z)=F4(z)=z + 0.25*alpha*z^2`. Alpha is strength relative to the earlier
quadratic anchor, not a measured SNR. Alpha=1 reproduces that clean anchor;
alpha=0 removes only the quadratic term, leaving a linear full field. It
is not the earlier curved-coherent construction and not an all-zero full
field. Curvature, support, graph locality, and loop size are not swept.

Generate actual clean probe means/covariances for each alpha before adding
noise. Do not scale previously measured residuals, angles, or winding.
Plane observations are clean and strength-independent. Evaluation is clean
and identical between reference arms A/B at each strength. Baseline A/B and
held-out V observe the same strength-dependent construction with separate
noise streams. Each strength has its own affine fits; the reference is not
artificially held equal to the fit at alpha=1.

## Fixed 33-level ladder and denominator

The ordered alpha values are:

`0, 0.000001, 0.000003, 0.00001, 0.00003, 0.0001, 0.0003, 0.001,
0.002, 0.003, 0.004, 0.006, 0.008, 0.01, 0.0125, 0.015, 0.02,
0.025, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.125, 0.15,
0.20, 0.25, 0.35, 0.50, 0.65, 0.80, 1.0`.

The fine near-zero tail exposes the existing amplitude floor; the denser
0.001–0.20 region samples weak-signal behavior without adaptive refinement.
No levels are added, removed or rerun according to favorable outcomes.

- Primary: side65 (4,225 vertices), k8, P8/P32/P128, seeds0–3,
  baseline/V noise scale0.03, all33 strengths: 396 paired units.
- Noiseless control stripe: same domain/k, P128, seed0, noise0,
  all33 strengths: 33 paired units.

Total **429 paired units / 858 arm measurements**, organized as twelve
noisy strength traces and one noiseless trace. Each unit retains all nine
field/loop-graph cells, five loops in both directions, all six existing
estimands for F2/F4, and the fixed core adjacency. Affine-residual paired
comparisons total **77,220 loop/hypothesis records**. Unrun, failed or
unavailable units stay in their registered position and denominator.

Four seed pairs are not enough for probability calibration. Reused graph
rows, loop directions, nested probe counts and strength points within one
trace are not independent replications. Noiseless repeats are controls.

## Noise pairing and chronological boundary

Use a new namespace, `SeedSequence([seed,0x50345353]).spawn(3)` (P4SS),
with streams A/B/V in that order. For a fixed domain/seed each role consumes
conceptual `(N,128,3)` standard-normal draws in vertex-major order, in
chunks of4096 vertices. Use the first P draws at each vertex. Bind the full
standard-normal stream bytes with a hash. These draws are identical across
alpha and prefix-paired across P, but independent across A/B/V and seeds.
They are not a replay of the old P4RV reference screen. When noise is zero,
no random draws are consumed or counted as independent references.

Identical added raw noise does not guarantee identical moment error:
especially F4 can depend on the strength-dependent clean covariance.
Record rather than assume the fitted-reference difference at each alpha.

Keep the original five-point affine-fit stencil and eight disjoint held-out
V coordinates. Seal all six graph-row reference fits before any V or
evaluation moment. V is diagnostic only and never selects a strength,
reference or graph. Each arm seals all36 charge-blind core records before
loop readout. Plane, branch-cut, amplitude (`1e-6`), core and coverage
rules remain unchanged; no missing scalar or field is reconstructed.

## Readouts and planned descriptive summaries

Retain the complete original arm reports, held-out diagnostics, input and
source hashes, and the five paired winding-admission categories. Add the
previously fixed perturbation recipe at every loop/hypothesis: amplitude,
reference-difference magnitude, pointwise ratios, coefficient angle,
radial/transverse changes, endpoint slopes and sampled-vertex reference-
segment minima. Preserve support/direction counts and null summaries.
Store fixed summary statistics in each report; retain source arrays for
exact per-point replay rather than duplicating long derived point series
at every strength. F4 angles are spin-two coefficient phases, not physical
director rotations. Positive sampled minima are not loop clearance.

Primary cross sections use outer-forward. For each P/seed/hypothesis and
strength, display whether all nine cells have both arms admitted at +2,
other admitted agreement, disagreement, one-arm admission, or neither.
If graph cells mix categories, preserve their counts rather than selecting
one row. The original +2 result is an injected-anchor recovery descriptor,
not a new admission rule or a physical-topology claim.

For every finite strength trace, report (a) the first sampled strength with
all nine cells both admitted at +2, and (b) the earliest strength from which
that condition holds at every remaining sampled level through alpha=1.
Record the preceding sampled level as the lower bracket, preserve every
break/re-entry, and leave either result null if absent. If any unit in the
trace fails or is unrun, no all-suffix persistence is certified for that
trace. These are grid descriptors, not continuous critical points,
monotonicity guarantees, calibrated detection limits or p-values.

Also compare per-row medians/ranges of `D/min(a,b)` and absolute coefficient
angle. Never divide separate medians to obtain a median ratio. Keep all
three graph rows and four paired seeds identifiable; do not treat them as
12 independent trials. Use fixed strength axes in the visual cross sections
and preserve unavailable regions rather than joining lines through them.

## Implementation, execution and receipts

Use separate successor sources and isolated function namespaces. Do not edit
the byte-pinned predecessor algorithms, plans, outputs or scientific gates.
Test clean alpha=1 parity, alpha=0 linear fields, weak quadratic moments,
raw-noise pairing across alpha/P, noiseless exact arm duplication, actual
seal chronology, all-cell/all-loop retention, nulls, trace re-entry/failure
handling and output integrity before the registered panel.

Commit plan first, then tested implementation, then results to working
PR#122. Run on an isolated Furnace checkout, NumPy CPU reference, one child
and one BLAS thread, nice10. Bounds: 180 seconds per unit, 2,400 seconds
overall, 8 GiB child virtual address space, 2 GiB per file, and a 12 GiB
pre-unit output-disk admission check (not a filesystem quota). No GPU/model
runtime installation or other-workload change is authorized by this panel.

Retain raw NPZ and full reports on Furnace; return compact cross-section
receipts containing every registered unit and row/loop summary. Verify
report, NPZ and compact-output hashes. Keep failed/timeout/unrun records.
Results go in a separate document; do not rewrite this plan after readout.
No D7/D8, SCI-S1/S2, Pythia-160M, verified-core, order-parameter,
phase/transition, or scientific-authority promotion follows from this run.
