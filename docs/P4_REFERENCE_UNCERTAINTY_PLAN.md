# P4 reference uncertainty: averaging, positions and split/merge uncertainty

Decision date: 2026-09-06. Status at commitment: specified, not run.
Synthetic development / Level 0. Commit before drawing the new references
or observing the registered geometry fixtures. This is a targeted successor
to the spatial-fidelity result, not independent scientific confirmation.

## Question and explicit change of calibration lane

Does reducing independent reference-measurement noise reduce uncertainty in
the reconstructed center and split width, and which errors remain? The
previous panel recovered the correct outer charge without faithful local
structure. Its coefficients, scores and failures remain immutable.

This successor explicitly assumes a **separately observable background-only
calibration channel** in the synthetic generator. Its background coefficient
field is z; evaluation is z plus an injected residual. Fit the background
from noisy measured probes, never by editing fitted coefficients toward an
oracle. This changes the calibration estimand relative to the predecessor's
full-response fit; it is not evidence that a model provides such a channel.
No calibration method is selected using localization scores.

## Registered independent reference cohorts

Use16 new reference cohort seeds200–215, NumPy SeedSequence keys
`[seed,0x50345255,repeat_index]`, and repeat indices0–255. A repeat draws
standard-normal noise in exactly(5,128,3) order, for the ordered physical
stencil [(0,0),(-0.5,0),(0.5,0),(0,-0.5),(0,0.5)]. Noise scale0.03.
This namespace and these cohorts are new, not old A/B or geometry draws.

At each stencil position generate the same exact eight-cube background
probes, repeated toP128, with known constant xy observation frames. Observe
F2 mean and F4 traceless covariance with the existing NumPy moment adapter.
Fit each repeat's affine coefficients by unweighted least squares against
[1,x,y]. Separately average the fitted coefficients of the firstK repeats,
for **K=1,4,16,64,256**. Never pool raw probes across repeats for F4: that
would change the covariance estimand. Do not change the fit stencil, frame,
noise scale or the per-repeat128-probe measurement.

Store raw calibration probes, moments, per-repeat coefficients and each
prefix average. Bind their hashes and reference seals. Prefixes are paired,
not independent conditions. There are16 independent cohorts,4,096 repeated
background observations,8,192 F2/F4 fits and160 averaged reference estimates.
Seal all160 estimates in a complete reference-bank receipt before reading
any held-out/evaluation observation. No failed cohort can be omitted.

After bank closure, also measure the clean background at the existing eight
held-out coordinates (the four +/-0.5 corners and four +/-0.25 axis points).
These are disjoint from the fit stencil. Report every prefix reference's
prediction error against these independently measured held-out values.
They are clean synthetic evaluations, not an additional noisy validation
cohort, and they never select a reference or prefix.

## Held-out geometry and fixed reconstruction

Use four new geometry seeds400–403 with the existing geometry namespace
and generator, at alpha0.08 and0.10. Keep all seven fixtures: single+2 zero,
separated+1/+1 pair (distance0.4), close+1/+1 pair (distance0.08), reverse
-1/-1 pair, +1/-1 dipole, nonzero constant and identically zero residual.
Scale the predecessor's0.10 residual construction by alpha/0.10; do not
alter positions, orientation or the background when changing strength.

Fix256 cells per side (257x257 vertices), P128 clean evaluation probes and
the constant xy frame. Each of56 alpha/geometry/fixture units has the same
observed full field for every reference. Retain both F2/F4, all16 cohorts
and fiveK prefixes, plus one ideal-reference control per hypothesis.
Total: **8,960 estimated-reference reconstructions +112 ideal controls
=9,072 local reconstructions**, not9,072 independent trials. New graph
construction/admission is outside this direct coefficient-field bench.

Reuse the predecessor charge-blind locator, candidate-before-loop seals,
component rectangles and unresolved rules without editing their source.
Keep amplitude floor1e-6, branch margin0.15 radians, possible-zero roundoff
allowance1e-12, overlapping-loop/boundary/nonlocal stops and the original
0.10 position-match score. Keep zero/insufficient distinct. The primary
full local-structure score is unchanged; additionally report the stricter
0.01 match score as a labeled secondary diagnostic, not a replacement.

All truth objects are confined to construction and post-reconstruction
scoring. Neither locator nor component readout receives centers, expected
counts, fixture labels or expected charges. Averaging is fixed before any
geometry score, and no best seed/prefix/field is selected.

## Uncertainty propagation readouts

For each measured reconstruction, before truth-side scoring, record:

- resolved charged-component count, signed charge pattern and outer winding;
- centroid weighted by absolute measured charge, or null if none resolves;
- maximum pairwise component distance, zero for one resolved component,
  or null if none resolves;
- every position, component box, loop amplitude/angular margin, unresolved
  reason and possible-zero candidate that did not become a resolved core.

This centroid is a descriptor of measured charged components, not an
assertion that an unknown physical core has that center. A net-zero dipole
does not cause division by its signed charge. No resolved component means
unavailable center/span, not origin/zero width.

Only then score distance of that centroid to the known absolute-charge
centroid and error of the measured span versus the known maximum separation.
Also retain the original count/position/charge matching, misses, false
positives, and secondary0.01 matching. For zero/constant truth, center and
span error are undefined; score false positives and amplitude/state instead.

Across the16 cohorts at eachK, retain all observations, count histograms,
valid and missing denominators, empirical median and90th percentile of
location/span error, and empirical90th-percentile radius about the cohort
centroid median. The latter is a descriptive spread, **not a confidence or
credible region with validated coverage**. Use NumPy linear quantiles.
Conditional error summaries always show how many of16 cohorts contributed.
Do not hide abstentions, or interpret an error decrease due to dropped
cohorts as unconditional improvement.

Report held-out background prediction RMSE and coefficient-vector spread
againstK separately from spatial errors. Coefficient error may decrease
without a corresponding proportional decrease in split width or improved
null specificity. No monotonicity or successful recovery is required for
completion; preserve every nonmonotone or unresolved result. Do not infer a
scaling exponent from a theoretical law or replace the observed curve.

## Execution, verification and claim ceiling

Use successor source files on PR#122. Byte-pin the plan, implementation and
tests; leave all spatial-fidelity and earlier bindings unchanged. Tests use
geometry/reference seeds outside the registered held-out cohorts. Test
noise prefixes/independence, probe/moment and least-squares identities,
bank closure and reference-before-evaluation chronology, field sharing,
unaltered locator/scorer behavior, centroid/span missingness, null controls,
tampering/missing artifacts and exact planned denominators before launch.

There are72 planned execution positions:16 calibration cohorts, then56
geometry units. If the reference bank is incomplete, all geometry positions
remain not_run. Execute in a new isolated Furnace checkout, NumPy CPU,
one child/one BLAS thread, nice10; no model/GPU or runtime changes.
Bounds:180seconds per unit,1,800seconds campaign,8GiB child address space,
2GiB per file and4GiB pre-unit output-disk admission. Preserve attempts,
failures, timeouts and unrun positions; do not reuse an output directory.

Save measured full fields once per geometry unit, calibration observations
and exact reference coefficients. A residual is losslessly reconstructible
from those arrays by the declared subtraction; it need not be stored160
times. Bind every reconstructed field hash in its candidate seal. Replay
each local reconstruction and score from retained arrays, and replay all
averaged coefficients from raw calibration measurements. Verify source,
reference-bank and artifact hashes before/after consumption. Return compact
outputs and exact-file-closure receipts; raw arrays remain on Furnace.

Publish results, uncertainty plots and the unchanged failure denominators.
The benchmark tests a synthetic noise-reduction intervention and geometry
fidelity, not a real model order parameter, verified core, physical phase,
holonomy or transition. D7/D8, SCI-S1/S2, Pythia-160M and all scientific
authority gates retain their existing status. A better instrument diagnosis
is not a measured increase in the discovery rate of model-internal vortices.
