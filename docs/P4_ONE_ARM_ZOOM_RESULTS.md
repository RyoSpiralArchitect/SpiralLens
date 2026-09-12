# P4 one-arm zoom: completed targeted exploratory results

Decision date: 2026-09-05. **99/99 pairs / 198 arms completed** in
178.137496 seconds. Retained 17,820 paired loop/hypothesis records and
3,564 separately labeled sampling-estimator checks. No measurement failed,
timed out or remained unrun. Synthetic development / Level 0.

The three isolated outer A-only entries resolve differently: one becomes
three consecutive sampled entries, another has nearby B-only entries, and
the third reveals a second A-only stop with an intervening winding-zero
region. The new samples expose structure hidden by the original grid.

## 1. Contract and exact predecessor replay

The [registered local-slice plan](P4_ONE_ARM_ZOOM_PLAN.md) was committed as
`f4c05d1` before new observations. Execution used
`8372094bb65a77dff4b845704ec3273233d61f5d`. Each selected center has sixteen
equal decimal subdivisions on either side: three windows of33 points.
The nine old anchors are exact replays; 90 strength conditions are new.
Selection was motivated by observed predecessor results, so this remains
targeted exploration, not independent confirmation or probability calibration.

Flat `F2=F4=z+0.25*alpha*z^2`, side65/k8, noise0.03, original fit and
validation stencils, six reference seals, 36 core seals per arm, all nine
graph cells and all five loops in both directions are retained. A/B/V raw
noise uses the predecessor P4SS namespace, with separate fits at every
strength. There are three reused seed pairs, not 99 independent trials.

All nine anchor replays exactly match the old input hashes, noise receipts,
held-out records, array layout, baseline/field seals and paired loop reports.
The returned arrays preserve the original data; the new diagnostics locate
their minimum-amplitude vertex and maximum-angle edge.

## 2. What the denser outer slices reveal

All nine cells have identical scalar diagnostics/categories at every
sampled strength (their provenance hashes still identify different graph
receipts). The counts below are strength entries, not independent graph
replications. Percentages are relative quadratic strength, not measured SNR.

| Window / hypothesis | One-arm entries | Admitted winding sequence |
| --- | --- | --- |
| P8/seed1, F4, 0.2–0.4% | A-only at0.2875%,0.29375%,0.3% | A stays0; B: -1 → insufficient → 0 |
| P8/seed3, F4, 8–12.5% | A-only at10%; B-only at11.5625% | B:0 → insufficient → +1; A:-1 → insufficient → 0 → +1 |
| P128/seed0, F2, 0.8–1.25% | A-only at0.825% and1% | A stays0; B:-1 → insufficient → 0 → insufficient → +1 |

The companion F2 slice at P8/seed3 also contains B-only entries at
10.46875% and12.34375%, as A moves from0 through+1 to+2. B moves from+1
to+2 between **11.09375% and11.25%**;
both endpoints are eligible and the finite grid contains no B-stop entry
between them. The companion F2 at P8/seed1 stays -1 in both arms. The
companion F4 at P128/seed0 has A=+1 throughout, while B changes from+1 to+2
between1.1875% and1.203125%, again without a sampled insufficient entry.
Absence of a stopped sample does not establish continuous clearance.

Across the six outer traces there are six A-only and three B-only entries.
The earlier outer display's zero B-only count was specific to its coarse
grid; this same outer loop now contains both kinds of one-arm admission.
These targeted counts do not estimate A/B probabilities.

### Sampled brackets, not continuous endpoints

| Stop / reference | Previous admitted alpha | Insufficient sampled alpha(s) | Next admitted alpha |
| --- | ---: | --- | ---: |
| P8/s1 F4 / B | 0.0028125 | 0.002875,0.0029375,0.003 | 0.0030625 |
| P8/s3 F4 / B | 0.09875 | 0.1 | 0.1015625 |
| P8/s3 F4 / A | 0.1140625 | 0.115625 | 0.1171875 |
| P8/s3 F2 / A, first | 0.103125 | 0.1046875 | 0.10625 |
| P8/s3 F2 / A, second | 0.121875 | 0.1234375 | 0.125 |
| P128/s0 F2 / B, first | 0.008125 | 0.00825 | 0.008375 |
| P128/s0 F2 / B, second | 0.009875 | 0.01 | 0.01015625 |

The P128 B=0 interior contains thirteen consecutive sampled strengths,
0.008375 through0.009875. Thus the old endpoint difference -1 to+1 resolves
into two sampled changes with a measured intermediate zero region. The
isolated 10% and1% stops still occupy single entries in the new grid;
their continuous widths remain unresolved. No phase-transition or
continuous charge claim follows from these sampled descriptors.

## 3. Located edges and unchanged gates

All nine outer one-arm entries stop solely on
`branch_cut_or_undersampling_ambiguity`. Their stopped-arm minimum sampled
amplitudes range from7.759627e-5 to1.238901e-3: approximately77.6–1,238.9
times the fixed1e-6 amplitude floor. They fail the maximum adjacent angle
limit, pi-0.15 =171.405633 degrees. The stopped angles span
172.994063–178.855500 degrees. No insufficient winding is filled in.

| Selected event | Stopped arm / maximum-angle edge coordinates | Maximum angle |
| --- | --- | ---: |
| P8/s1 F4, 0.2875–0.3% | B: (1,-0.53125) → (1,-0.5), same edge across all3 entries | 176.3554°,178.4877°,173.3043° |
| P8/s3 F4, 10% | B: (1,0.125) → (1,0.15625) | 176.8446° |
| P8/s3 F4, 11.5625% | A: (-0.4375,1) → (-0.46875,1) | 173.3806° |
| P128/s0 F2, 0.825% | B: (0.75,1) → (0.71875,1) | 178.8555° |
| P128/s0 F2, 1% | B: (-1,-0.5625) → (-1,-0.59375) | 172.9941° |

The two P128 stops involve different edges on the upper and left boundary.
The edge locations supply concrete targets for a later spatial-resolution
test; they are not located physical defects or qualified cores. Positive
vertex amplitudes do not certify the field between those vertices.

## 4. Sampling controls and all-loop denominator

All1,188 cyclic-origin estimator checks preserve reliability, eligible
integer and scalar extrema within the declared tolerance. All17,820
algebraic label exchanges preserve equal/different/neither categories and
swap A-only with B-only. These checks consume no new random draws.

The2,376 stride-two checks use two offsets of128 original outer samples;
they are estimator-only coarsenings with no inherited graph admission.
For each field row, offset0 changes reliability at four P8/s1 F4/B points
and one P8/s3 F2/B point; offset1 changes one P8/s1 F4/B point. Across all
three rows,18 derived comparisons change reliability. Whenever full and
coarsened estimators are both reliable, their winding integers agree.
The already-observed one-arm entries remain stopped under both offsets.
This is sensitivity to removing samples, not evidence of spatial convergence.

| All retained loops/directions | Equal | Different | A-only | B-only | Neither | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| F2 | 5,562 | 3,240 | 54 | 54 | 0 | 8,910 |
| F4 | 6,228 | 2,538 | 90 | 54 | 0 | 8,910 |

Every compact unit retains all graph/loop/hypothesis entries, including
original states/reasons/nulls, located scalar diagnostics and separately
labeled coarsened estimates. Reverse loops and repeated graph cells are
correlated records, not additional independent evidence.

## 5. Validation and evidence locations

Twenty new focused tests pass; the combined zoom/strength/reference/
perturbation suite passes154 on Mac and154 on Furnace. Tests include exact
old-anchor arrays, raw-noise pairing, located edge orientation and nulls,
cyclic/swap/decimation behavior, replay integrity and modified-array rejection.
After execution,205 source bindings and297 report/NPZ/compact hashes match.
All nine old anchors are independently rechecked against retained reports.
Cross sections replay from all99 compact outputs. One initial summary-helper
check compared Python tuples to JSON lists and stopped before writing output;
JSON normalization fixed that comparison without rerunning a measurement.
After the documentation update, the zoom/generated-view suite passes34.
The interactive overview retains all396 A/B observations across six plots;
736/360-pixel light/dark checks cover labels, selection, series toggles,
aligned hover details and overflow. The spatial detail shows the selected
sampled vertex and edge, and leaves insufficient winding values null.

Peak child RSS:200,261,632 bytes. Campaign output before manifest:
1,754,456,065 bytes. NumPy CPU, one child / one BLAS thread, nice10; no GPU
or model was used.

Furnace root:
`/home/ryospiralarchitect/scratch/spirallens-one-arm-zoom-20260905-TAQsQz/`.
The isolated `checkout/` holds execution source, `campaign/` holds raw NPZ,
full reports, all compact entries and receipts. The returned local evidence
is `artifacts/p4-one-arm-zoom-20260905/`, with a `campaign/` compact copy,
verification helper, its attempt note and the interactive-display checks.

| Receipt | SHA-256 |
| --- | --- |
| Protocol | `c26b3b6020d8a31e4d0568c61028a5805671924f732523c3ea5b7dd74309b8ba` |
| Launch plan | `9f007e76fa943438dbe94d9516aa4dfc526ffbf1497d3c5a33733efecbd3824b` |
| Manifest | `7b5a8529f0332109cbef71804dbf3b365ca3064c8717b87f827df1a3ffbc3125` |
| Cross sections | `1354d4c1c04d0cde4050e78c3b0a70e7ddc7fb626362541f0611f5ee95bc2668` |
| Summary | `69d20255fb7b7142b04db67cfaba1e5d2a1b40979763fb2456391f92a7af8c0a` |
| Visual data | `f68fd23af96a0250dba6a1a1f159a1216cea250ed24fe8913d5c87d479c5a3fd` |
| Verification receipt | `9d016509bf95fa050b0456a2dadfa5ed39cb25d0df3e20922968c9d03ceb803d` |
| Verification/summary helper | `0ee7b01868547616686128b8a543a35920d803eac72207a2196b2c3127249052` |
| Interactive zoom | `3aa7be71e86427fd48dab509f86f4efab4dd213deea83e2c47a7cc724458410a` |
| Returned archive,5,586,827 bytes | `3da703ee34aa1f1b5cde7cee50057570ab23fd18464f9cbb7aadf66ec51b3ea9` |

The interactive source is
`/Users/ryohiga/.codex/visualizations/2026/07/22/019f8a17-0be7-7901-80b6-393a863331e6/one-arm-strength-zoom.html`.
It accompanies the unchanged earlier33-level overview.

The campaign CLI is `scripts/run_p4_one_arm_zoom_v0_1.py --output NEW_DIR
--predecessor OLD_STRENGTH_CAMPAIGN`, run with the committed checkout's
`src` on PYTHONPATH. It requires Linux, a new disjoint output directory,
and the pinned predecessor manifest/anchor reports. Use the registered
resource bounds; the old output is not an append target.

The next useful test is a prospectively fixed spatial refinement around
these located edges, with comparable observation/noise pairing and both
reference arms. Further alpha refinement can resolve the remaining sampled
singletons, but this result alone supplies no continuous widths, calibrated
thresholds, verified cores, model-derived order parameter or physical phase.
D7/D8, SCI-S1/S2 and Pythia-160M gates retain their existing status.
