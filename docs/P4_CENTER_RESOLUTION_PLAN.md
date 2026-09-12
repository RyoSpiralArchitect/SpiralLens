# P4 expanded center-resolution slice and separate stress controls

Decision date:2026-09-09. Status at commitment: specified, not run.
Commit before generating any new reference cohort or geometry observation.
Synthetic development / Level0; no model access or scientific gate changes.

## Fixed comparison and what increasing the population means

Expand independent evaluation-reference cohorts from16 to64 and geometry
cohorts from4 to16. Sample positive-pair distances0.080 through0.160 in
0.005 increments. Keep K16/256/4096, alpha0.08/0.10, the background-only
calibration assumption, and the predecessor's inference/tolerances unchanged.
Larger cohorts improve estimation of conditional decision frequencies;
they do not by themselves shrink an individual record's separation range.

Reuse the exact predecessor envelope bank, SHA-256
`fc42c19e7d561eee00ce14abf4652d24a4b440e3aba1046d1bc82762a37a403b`,
copied without alteration to`protocols/p4_center_resolution_envelope_v0_1.json`.
Its original32 calibration cohorts, pairing, three affine radii and all
seals remain fixed. Validate the exact file and internal envelope before
consumption. No new calibration, maximum/quantile selection or radius
enlargement is allowed using this campaign's observations. The comparison
is conditional on this one inherited empirical calibration, not a new
coverage qualification. Pair differences cannot bound common-mode bias.

Use new reference seeds800–863 with the predecessor noise namespace
0x50344944,4,096 independent background repeat sets per cohort, five fit
positions andP128 probes. Reuse the existing raw-draw, per-repeat moment,
affine-fit and prefix-averaging functions exactly; never pool F4 probes.
Seal all384 estimated references before any new geometry/stress observation.
This generates262,144 repeat sets and524,288 F2/F4 fits.

## Primary resolution matrix

Geometry seeds900–915 use the unchanged center/angle generator. Ordered
fixtures: double; positive pair distance0.04; the17 positive pairs from
0.080 through0.160; positive pair0.40; reverse pairs0.08,0.16,0.40;
dipole0.40; nonzero constant; zero; linear+1; cubic+3. There are28 fixtures.
The primary32 units are alpha0.08 then0.10, each with16 ordered geometries.
Each fixture has384 estimated references and two ideal controls, totaling
344,064 estimated +1,792 ideal =345,856 primary inference records.

The nine quadratic-fit and16 disjoint held-out coordinates are unchanged.
Observe and retain exactly these25 points with the existing exact-cube
P128 construction and dense moment adapter. Inference consumes these
observed points, not an oracle coefficient shortcut. This is an inference-
first resolution study, not345,856 new full-grid local-loop reconstructions.
The inference has always depended numerically on these25 positions;
changing its saved input footprint changes input hashes, not its fit rule.

Before launch, verify support-measurement and inference-numerical parity
against the full257x257 construction on nonregistered geometry fixtures.
Keep input/coordinate hashes and readout seals distinct. Every primary
record preserves its status, interval/missingness, center/root bounds,
source-reference identity, readout seal and post-inference truth scores.
Do not silently inherit full-grid, graph-family or local-core admission.

For each available discriminant bound, retain the registered additive
decomposition: constant radius r0/(abs(a)-rA), center/linear contribution
2 abs(m) rm + rm^2, and numerical curvature term
abs(c/a) rA/(abs(a)-rA), with rA=1e-9. These are model-bound contributions,
not independently sampled physical errors. Their sum must reproduce the
original rD without changing the decision. No feasible-set tightening.

## Separate, deliberately uncorrected stress lane

After the full primary matrix, use geometry900–903, alpha0.10, all64
references atK4096 and both hypotheses. Use seven fixtures: double,
positive pairs0.08/0.12/0.16, zero, linear and cubic. Seven ordered modes:

- constant coefficient bias at0.5,1,2 times the frozen constant radius;
- linear coefficient bias at1 times the frozen x/y radii;
- evaluation-probe noise standard deviations1e-9,1e-7,1e-4.

Bias is an explicit synthetic coefficient-space stress transformation,
not a claim to have observed/refitted a biased raw calibration channel.
Add lambda*r0*exp(i*pi/7) to the fitted reference constant. For the linear
mode, add rx*exp(i*pi/7) to its x row and ry*exp(i*(pi/7+pi/3)) to its y
row. The transformed coefficient has its own hash and source-reference
binding. The same deterministic bias is shared by all cohorts within a
hypothesis; it is neither independent noise nor an extra calibration draw.

For noisy evaluation, keep reference coefficients unchanged. Add Gaussian
noise to actual25x128x3 probes before the original moment adapter. Use
SeedSequence[geometry_seed,0x50345253] for one standard-normal array in
the fixed support/probe/component order. Reuse that draw across the seven
fixtures, both hypotheses and all three noise strengths for paired contrasts.
Save the noisy probes and measured fields. No covariance or tolerance is
retrofitted to admit these observations. Exceeding the original1e-9 held-out
or curvature gate remains an explicit unsupported/mismatch outcome.

There are28 stress units and25,088 estimated inference records; no stress
ideal controls and no pooling with primary clean-evaluation frequencies.
Primary counterparts supply the nominal paired controls. Record actual
reference-envelope coverage, false-two/zero-compatibility outcomes, family
rejection, unavailable bounds and wrong coverage without correcting them.

## Preselected full-grid local-reader cross-check

After stress, run geometry900–903, both strengths and eight fixtures:
double, positive pairs0.08/0.10/0.12/0.14/0.16/0.40, and zero. Use only
the first four reference cohorts800–803 at all three K values/F2/F4,
plus two ideal controls:64 units,1,664 full-grid records. This subset is
fixed before outcomes, not selected for success or failure.

Retain the unchanged charge-blind locator, candidate/loop seals, overlap
stops, amplitude/angular gates and original0.10/secondary0.01 scores.
Compare each full-grid inference's numerical payload with its compact
support counterpart; preserve their distinct input footprints/seals.
Truth scores follow both readouts. These are paired duplicate observations
of a primary subset, not1,664 additional independent trials or a repair of
the predecessor's full-grid evidence.

## Aggregation and Monte Carlo precision

At each primary alpha/hypothesis/K/fixture, retain all16x64=1,024 records
with explicit statuses,64 reference-cohort identities and16 geometry IDs.
Never call them1,024 independent trials. Keep false-two single controls,
null controls, unavailable intervals and root-disk disjointness separate.
Report per-reference and per-geometry decision fractions alongside pooled
descriptive counts. Do not turn an unavailable interval into separation0.

Use2,000 deterministic two-way bootstrap draws for display uncertainty:
SeedSequence[20260909,0x50344253], independent with-replacement samples
of64 reference indices and16 geometry indices per draw. Apply the same
draw weights to every paired curve, K and hypothesis. Report pointwise
5th/95th percentiles of the decision fraction, with no monotonic regression
or smoothing of outcomes. These resampling bands describe this finite
two-axis sample conditional on the one fixed envelope. They are not
calibrated simultaneous confidence bands, coverage bounds for separation,
or uncertainty over calibration/real-model mismatch. Do not fit a universal
resolution threshold or claim absence below it.

Retain zero-field replica equality checks and use64, not geometry/strength
replication, as the cohort denominator for identical null observations.
The stress lane has four geometry groups and correlated repeated noise;
report its full statuses and counts separately, without primary-style
precision bands or a combined discovery/specificity rate.

## Execution and evidence

188 ordered execution positions:64 references,32 primary,28 stress,64
full-grid cross-checks. Total372,608 inference outputs comprise345,856
primary,25,088 stress and1,664 paired local-reader duplicates. Label these
denominators separately; only the last1,664 have new full-grid local loops.

Use an isolated Furnace checkout with NumPy CPU, one child/one BLAS thread,
nice10. Limits:180seconds per unit,3,600seconds campaign,8GiB address space,
2GiB per output file,12GiB total output admission and16GiB free disk before
each launch. No GPU/model or managed-runtime changes. Stop on a failed unit
or incomplete reference bank; preserve every attempt/terminal, failed and
not-run position. No in-place retry or output-directory reuse.

Replay all raw reference fits, support probes/fields, conditional outputs
and local-reader controls. Bind inherited envelope, complete reference bank,
source files, compact rows and raw arrays before/after consumption. Return
an exact-closure compact archive with all reports/attempts/terminals and
deterministically regenerated summaries; full raw arrays stay on Furnace.
Compact output retains full-precision values and readout seals, not only
successful or rounded display results.

Preserve every predecessor byte/score and current D7/D8, SCI-S1/S2 and
Pythia-160M status. Restricted coefficient-field roots are not verified
in-domain cores, model order parameters, phase/transition/holonomy evidence
or a validated digital twin. Neither greaterN nor a successful source/replay
check supplies scientific authority.
