# P4 reference uncertainty: centers tighten faster than split structure

The registered campaign completed on 2026-09-06: **72/72 execution units**,
with no failed, timed-out or rerun measurement units. This write-up is dated
2026-09-07. Independent reference averaging reduces background prediction
error and center uncertainty, but does not automatically recover a single
double-charge center, high-precision pair geometry or null specificity.
Synthetic development / Level 0; no model was accessed.

## 1. Explicit calibration assumption and denominators

The [plan](P4_REFERENCE_UNCERTAINTY_PLAN.md), committed at`2f7d8ba`, declares
a separately observable **background-only synthetic calibration channel**.
This changes the estimand from the predecessor's full-response fit. The
comparisons below are within this new lane, not a controlled improvement
over the predecessor's0/80 local-structure result. Availability of such a
channel in a real model remains unestablished.

Reference cohort seeds200–215 each receive256 independent noisy background
observations at the fixed five-point stencil, withP128 probes per point.
The measured F2/F4 moments are fitted separately for each repeat; the first
K=1,4,16,64,256 fitted coefficient matrices are then averaged. F4 probes
are not pooled across repeats. All160 prefix/hypothesis references are
sealed in one complete bank before any geometry or held-out observation.

There are16 independent reference cohorts,4,096 repeat sets and8,192 fits.
The four new geometry seeds400–403, two strengths0.08/0.10 and seven
fixtures give56 geometry units. Each reuses the same observed full field
for all160 estimated references and two ideal-reference controls:
**8,960 estimated reconstructions +112 ideal controls =9,072 records**.
These are not9,072 independent trials. K prefixes are nested/paired, F2/F4
share probes, and geometry cases reuse the same16 reference cohorts.

All reconstruction uses257x257 vertices, the predecessor's charge-blind
locator, candidate-before-loop seals, amplitude/angular/overlap stops and
original0.10 position-match score. A separately registered0.01 matching
score is secondary, not a replacement. Truth is used only in construction
and after reconstruction for scoring; no expected center/count/charge is
given to the locator or its loop reader.

## 2. Reference uncertainty actually decreases

Prediction RMSE against the eight clean, disjoint held-out background
positions, median across all16 reference cohorts:

| Average count K | F2 RMSE | F4 RMSE |
| ---: | ---: | ---: |
| 1 | 0.002745206 | 0.004416786 |
| 4 | 0.001348429 | 0.002775914 |
| 16 | 0.000696828 | 0.001249019 |
| 64 | 0.000385677 | 0.000657825 |
| 256 | 0.000180034 | 0.000357892 |

The endpoint reduction is15.25 times forF2 and12.34 times forF4. The
corresponding empirical90th-percentile coefficient-vector radius about
the cohort coordinatewise median decreases from0.009794826 to0.000584651
forF2 and0.018590546 to0.001104397 forF4, about16.75/16.83 times. These
coefficient norms use the fixed affine basis; they are not spatial errors.

All16 cohorts contribute to each calibration statistic. Clean held-out
observations repeat exactly across the56 geometry units; repetition is
checked, not counted as56 independent validation experiments. The reported
empirical radii/quantiles are descriptive spreads, **not confidence regions
with validated coverage**. No theoretical scaling exponent is fitted or
substituted for the observed curves.

## 3. A tight center can still be a split double zero

For the injected single+2 center at alpha0.10, pooled descriptive medians
over four geometries x16 shared reference cohorts (64 records per cell):

| K | F2 centroid error | F4 centroid error | F2 split span | F4 split span |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.083718 | 0.145825 | 0.550836 | 0.683658 |
| 4 | 0.035277 | 0.084470 | 0.388617 | 0.517638 |
| 16 | 0.021175 | 0.034304 | 0.250122 | 0.321989 |
| 64 | 0.012442 | 0.020561 | 0.171024 | 0.235491 |
| 256 | 0.006170 | 0.012050 | 0.133727 | 0.152302 |

All64 records have an available centroid at eachK. Centroid means the
absolute-measured-charge-weighted component center; span is the largest
component separation. A single resolved component has span0; no resolved
component has an unavailable centroid/span, not a zero measurement.

The endpoint median centroid error decreases about13.57/12.10 times, but
split span decreases only4.12/4.49 times. AtK256 every single+2 fixture
still resolves as **two components**, for both hypotheses and both
strengths (256 correlated records). Their outer winding is correctly+2;
their full local-structure score is0/256 under either position tolerance.
That is a stable aggregate center, not recovery of one verified core.

The cohort spread also tightens without pooling different true centers.
For the first registered geometry, seed400 at alpha0.10, the empirical
90th-percentile centroid radius changes0.112859 ->0.008501 forF2 and
0.287228 ->0.012193 forF4, with16/16 available centers throughout.
Every other geometry's separate spread remains in the summary.

The reduction is not uniformly monotone: forF4, seed400 at alpha0.10,
the median double-zero span rises0.605212 ->0.630978 fromK1 toK4 before
falling to0.176661 atK256. This condition is the view's first-seed default,
not a removed outlier or a selected successful prefix.

## 4. Coarse recovery improves; strict geometry and null controls still matter

At alpha0.10, each entry below has64 records: four geometries x16 shared
reference cohorts. The primary score requires matched count, positions
within0.10 spatial units and signed charges together.

| Injected structure | F2 primary, K1 -> K256 | F4 primary, K1 -> K256 | F2 secondary0.01, K256 | F4 secondary0.01, K256 |
| --- | ---: | ---: | ---: | ---: |
| one center,+2 | 0 ->0 | 0 ->0 | 0 | 0 |
| separated+1/+1 pair, distance0.4 | 1 ->64 | 0 ->64 | 12 | 0 |
| close+1/+1 pair, distance0.08 | 0 ->64 | 0 ->58 | 0 | 0 |
| reverse-1/-1 pair, distance0.4 | 1 ->64 | 0 ->64 | 10 | 0 |
| dipole+1/-1, distance0.4 | 2 ->64 | 0 ->64 | 9 | 1 |

The close-pair median measured spans atK256 are0.138493/0.161153 forF2/F4,
against the injected0.08. Passing the old tolerance therefore does not
establish high-precision separation. At alpha0.08 the final primary
close-pair score is62/64 forF2 and50/64 forF4, while the other three
separated-pair fixtures each reach64/64. All80 ideal-reference localized
controls pass both scores; the remaining32 ideal controls have no
resolved charged components. This does not redefine absence as complete
field reconstruction.

Missingness is retained. At alpha0.10, dipole centers are available in
33/64 F2 and36/64 F4 records atK1; atK4 these become59/64 and33/64,
respectively. Both reach64/64 atK256. These are conditional error
summaries, not an improvement manufactured by discarding missing centers.
At alpha0.08, geometry400, reference211/K256/F2, the close pair has two
candidate loops reading+1 each, but overlapping-component-loops prevents
either from becoming a resolved component. Its outer winding is+2; its
centroid/span stay null. The final F2 close-pair error summaries use63/64
available centers, not64/64.

For the identically zero injected field, the number of reference cohorts
with a resolved charged component is:

| K | F2, out of16 | F4, out of16 |
| ---: | ---: | ---: |
| 1 | 10 | 10 |
| 4 | 8 | 9 |
| 16 | 9 | 14 |
| 64 | 11 | 11 |
| 256 | 8 | 11 |

These zero-field observations are identical across the geometry/strength
replicas, so those replicas do not increase the denominator. Averaging
shrinks coefficient error but does **not** monotonically remove its
charged zeros. These are false positives relative to the injected null,
not proof that the locator invented zeros of the measured residual.
The ideal zero field stays globally below the amplitude floor with
undefined winding. All nonzero-constant controls have no resolved charged
components. Neither null has a defined truth centroid or span error.

## Interpretation and next bounded question

The useful progress is a measured uncertainty budget: reference estimates,
centroid stability, split/merge fidelity and null specificity are now
separate observables. Repeating the background measurement is effective
for positions under the declared calibration assumption; it is not a
general certificate of local structure or a way to admit the zero field.

The next bounded design should test whether **one uncertain center region
can be distinguished from two genuine nearby centers while retaining null
specificity**, with new held-out cohorts. Keep reference-induced spread
separate from grid/loop-overlap stops. Any uncertainty-aware abstention or
split/merge rule needs a prospectively fixed successor, not retrospective
merging of the current two components to make this panel pass. Do not
assume that further averaging alone will solve the null problem.

No D7/D8, SCI-S1/S2, Pythia-160M or scientific-authority gate changes.
This is not model-derived phase, transition, holonomy, order parameter,
verified core, or a validated digital twin of model dynamics. An improved
instrument-fidelity diagnosis is not a measured discovery rate for model
vortices.

## Execution, verification and artifacts

Execution source:`516e1ac875deadf6038fa0e6142aba94ff1205df`. Isolated Furnace
checkout:`/home/ryospiralarchitect/scratch/spirallens-reference-uncertainty-20260906-AkULvf/checkout`.
Its sibling `campaign/` holds the raw calibration probes, per-repeat fits,
shared full fields and exact reference coefficients. The run took236.013022
seconds; peak child RSS112,664,576 bytes; compressed arrays197,557,217 bytes.
Python3.14.4 / NumPy2.5.2, Linux7.0.0-29, NumPy CPU, one child/one BLAS
thread, nice10. No GPU/model access or managed-runtime changes.

The27 new tests and predecessor suites total225 passes on Mac and225 on
Furnace. The implementation revision's three clean-wheel CI jobs pass;
later documentation revisions have their own checks. All prior source
and protocol bindings remain unchanged.

Post-run verification replays all8,192 fits and9,072 local records from
raw observations and saved full fields/reference matrices. It checks209
source bindings and144 report/array hashes. The complete reference bank
precedes geometry, and its seals/source hashes are checked during
consumption. No residual array is copied160 times; each residual is
losslessly reconstructed by the declared subtraction.

Local evidence:`artifacts/p4-reference-uncertainty-20260906/campaign/`.
The returned compact archive contains exactly367 files, including all72
report/attempt/terminal/log sets and the summarizer. Local verification
checks every extracted byte, all manifest joins and byte-exact regeneration
of the summary and visual-data projections; full raw replay occurs on
Furnace. The interactive view retains both hypotheses, all56 fixture /
strength / geometry selections, all fiveK values, unavailable outcomes and
the K1/K256 spatial clouds. Curves use observed medians and descriptive
quantiles; hover interpolation is labeled as display interpolation.
All56 selections, actual marks, cross-series visibility/hover, exact cursor
guides, pinned detail and label/mark clipping are checked at736/360px in
light/dark themes. The view rounds display data to eight significant digits;
the full-precision summary and raw records remain unchanged.

| Binding | SHA-256 |
| --- | --- |
| Protocol | `e4aa1f7d6a94c9d9274d9a16c858d47eeb813abff11fa52dd0a0d6a8df5b41ce` |
| Launch plan | `26e50bb7d556dafd9ff643d547be93c87978db894fe0694e288bc5afe2e4c0dc` |
| Reference bank | `a7b0cc935fe26d2a1ef71f2b7c8849a0fda930d430e191a8c3341e5cb6b394e8` |
| Manifest | `4d0190db91e641d40a2023ba3e9282f2361e8c0e75145b98e7fbbcb6824fa0fa` |
| Summary | `7f14ef17c6b6b4b08b19b75576bef0ab3d60764f40b08eb03750a54b54cac1b4` |
| Visual data | `d098a4fccd4a054ad2b973ae4d25055c5d53bd2091b364da1542e5c4aec9ad7b` |
| Furnace verification | `bee85d8a2795652fe00821201ba960d5247aa71c8c22049805e17c2fb253d15c` |
| Returned archive,7,891,354 bytes | `bf7d7c51824cc8fea365267b860da9bded4d5899b2458b83e089ff78a3713345` |
| Local returned-evidence verification | `5f945ff2a86abadc592025bfb69fcf64b5675ed400c4e6dfbf71bd9bac1077f7` |
| Compact-summary helper | `8abc689f0fbca880e94c06009c9bd1ccbb0a55baa04ed223b95497cd42c477a7` |
| Interactive uncertainty view | `3fce6daccaf53c3c4f8762089c98e38f46404cc1344f0367ce4c647dbee2e937` |
| Final visual checks | `2e7acdd57a2abde44f80c040e56da2331526c7df3c6caaf049fce653f32b01a0` |
