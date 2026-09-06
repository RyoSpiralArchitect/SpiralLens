# P4 reference perturbation: exploratory reanalysis results

Decision date: 2026-09-04. **32/32 retained pairs analyzed; 5,760/5,760
loop/hypothesis records preserved**, in 11.035096 seconds. CPU synthetic
development only, claim ceiling Level 0.

This is **post-hoc exploratory reanalysis of already observed pairs**, not
confirmation on new observations. The known winding outcomes motivated the
[fixed analysis plan](P4_REFERENCE_PERTURBATION_PLAN.md). The new quantities
describe reference sensitivity without refitting, resampling, selecting an
arm, recomputing winding, or changing an admission rule.

The main distinction is relative scale. At P128 in the primary curved
construction, a reference change remains comparable to or larger than the
residual and can substantially rotate its coefficient direction. For the
injected quadratic component, similar absolute reference changes are small
relative to a much larger retained residual. These observations suggest
useful descriptors for a future fixed experiment; they do not establish
a threshold separating genuine structure from artifacts.

## 1. What was held fixed

The inputs are all 32 pairs from
[independent reference validation](P4_REFERENCE_VALIDATION_RESULTS.md),
created at commit `465238be0fe9b63bbe83fbd40408b2484d7d75e8`.
Analysis-plan commit `616ca47` preceded implementation/execution commit
`b18c2dec5baa67e0783b528559f5c3dd96066891`. Existing pair outcomes were
already known before the analysis plan; this sequencing does not make
the reanalysis a preregistered confirmation.

Every input report and raw NPZ was checked against its original manifest.
The analyzer also checked retained array mappings, field seals, array/frame/
support hashes, identical A/B full fields, and identical fixed loop paths.
It reads only needed NPZ members after checking whole-file integrity. The
original arrays, source files, plans, and result documents were not edited.

The denominator remains 32 pairs × 9 graph cells × 5 loops × 2 directions
× 2 hypotheses = 5,760 records. Numerically identical supported loop-graph
columns refer to the same field-row diagnostic; they are not separately
drawn observations. Graph rows, reverse traversal, nested P, and noiseless
copies are not independent replications. Original A/B winding states,
reasons, values, and all five admission categories are copied unchanged.

## 2. Definitions and summary convention

At one vertex in the same recorded coefficient frame, write
`a=norm(rA)`, `b=norm(rB)`, `d=rB-rA`, and `D=norm(d)`. The symmetric
relative perturbation is `rho=D/min(a,b)`. It is null whenever either
endpoint amplitude is at or below the unchanged floor `1e-6`; no epsilon
replacement or ratio clipping is used. Unsupported or numerically
unavailable quantities also remain null with reasons.

The angle is `atan2(det(rA,rB), dot(rA,rB))`, only where both endpoint
directions are defined. Tables below convert its absolute magnitude from
radians to degrees for readability. **F4 degrees are spin-two coefficient
phase differences, not physical director-angle differences; they are not
halved.** These are same-vertex comparisons, not across-vertex transport.

For the artificial reference segment `rA+lambda*d`, `0<=lambda<=1`, let
`s` be its minimum amplitude at that vertex. The artifact retains its
minimizing lambda, `s/min(a,b)`, radial/transverse changes about A, endpoint
angular slopes, amplitudes, signed amplitude change, relative perturbations
about each arm, and all fixed min/quartile/median/max summaries. This segment
is algebraic interpolation between retained references, not an additional
fit, observation, or physically validated reference path.

The primary tables use **outer-forward only**, as fixed in the plan. Each
unit entry is the minimum–maximum of the **three field-row medians across
sampled vertices**. A single number means those three medians agree to the
shown precision. These ranges are not confidence intervals. In particular,
the median of pointwise `D/min(a,b)` is not the ratio of the separate
medians of `D` and `min(a,b)`.

## 3. Relative change and coefficient-angle change: every unit

`C` denotes curved coherent; `Q` denotes quadratic excess. Conditions are
`construction/side/seed/P`; noise is 0.03 except the four marked clean
controls. The side-65 outer loop has 256 vertices; side 257 has 1,024.

| Unit | Condition | F2 median rho | F2 median absolute angle, ° | F4 median rho | F4 median coefficient angle, ° |
| --- | --- | --- | --- | --- | --- |
| 00 | C/65/0/8 | 2.06418–2.09622 | 93.4162–93.8135 | 1.81384–1.83907 | 62.4085–62.8366 |
| 01 | C/65/0/32 | 1.52672–1.55759 | 55.5782–57.9152 | 2.14638–2.20979 | 40.1932–41.5087 |
| 02 | C/65/0/128 | 1.91374–2.07607 | 49.4800–55.6991 | 1.17169–1.25855 | 27.9828–29.7143 |
| 03 | C/65/1/8 | 1.63456–1.65810 | 58.7353–60.4543 | 1.62641–1.63859 | 72.7517–75.4522 |
| 04 | C/65/1/32 | 1.94050–1.99981 | 73.6561–79.8257 | 2.45939–2.46716 | 79.5892–82.8565 |
| 05 | C/65/1/128 | 2.29505–2.35525 | 109.793–119.956 | 1.45718–1.57991 | 35.2561–36.2948 |
| 06 | C/65/2/8 | 2.23181–2.29844 | 113.907–114.604 | 1.48863–1.49908 | 63.9975–64.4152 |
| 07 | C/65/2/32 | 1.71760–1.75394 | 80.0297–81.5509 | 2.73924–2.84256 | 142.812–147.177 |
| 08 | C/65/2/128 | 2.65039–2.68908 | 143.213–144.252 | 1.51246–1.52420 | 24.4447–26.7444 |
| 09 | C/65/3/8 | 2.35280–2.35806 | 160.972–161.120 | 2.26493–2.27303 | 95.3947–95.4760 |
| 10 | C/65/3/32 | 2.65121–2.70874 | 102.332–103.716 | 2.18198–2.22935 | 151.145–151.628 |
| 11 | C/65/3/128 | 3.02011–3.36782 | 97.3608–104.354 | 2.24750–2.31951 | 97.7015–99.7855 |
| 12 | Q/65/0/8 | 0.117786 | 3.50368 | 0.175551 | 7.06164 |
| 13 | Q/65/0/32 | 0.0301666 | 0.868697 | 0.0869481 | 3.20421 |
| 14 | Q/65/0/128 | 0.0162520 | 0.632803 | 0.0272140 | 0.734119 |
| 15 | Q/65/1/8 | 0.116315 | 4.11546 | 0.119431 | 4.59812 |
| 16 | Q/65/1/32 | 0.0446278 | 1.65632 | 0.0641402 | 2.35830 |
| 17 | Q/65/1/128 | 0.0268635 | 0.999478 | 0.0148932 | 0.579227 |
| 18 | Q/65/2/8 | 0.105941 | 3.19020 | 0.0524000 | 1.52848 |
| 19 | Q/65/2/32 | 0.0395415 | 1.12920 | 0.0677538 | 2.20658 |
| 20 | Q/65/2/128 | 0.0390661 | 1.08875 | 0.0277921 | 1.13178 |
| 21 | Q/65/3/8 | 0.189055 | 7.60511 | 0.370651 | 13.0534 |
| 22 | Q/65/3/32 | 0.0713577 | 2.32266 | 0.183357 | 6.41712 |
| 23 | Q/65/3/128 | 0.0273012 | 1.17568 | 0.0623356 | 1.63316 |
| 24 | C/257/0/128 | 1.57674–1.60636 | 60.1470–60.4303 | 2.54220–2.57641 | 149.023–149.707 |
| 25 | C/257/1/128 | 2.74105–2.76148 | 156.555–158.163 | 2.40735–2.43079 | 114.434–119.497 |
| 26 | Q/257/0/128 | 0.0251639 | 0.792185 | 0.0738160 | 1.93920 |
| 27 | Q/257/1/128 | 0.0493110 | 2.09395 | 0.0394019 | 1.55694 |
| 28 | C/65/0/8, clean | 0* | 0* | 0 | 0 |
| 29 | C/65/0/128, clean | 0* | 0* | 0 | 0 |
| 30 | Q/65/0/8, clean | 0 | 0 | 0 | 0 |
| 31 | Q/65/0/128, clean | 0 | 0 | 0 | 0 |

`*` The clean curved F2 fixed-radius row has only 254/256 defined endpoint
directions: two points are at/below the floor and retain null ratios and
angles. Their amplitudes and segment diagnostics remain available. The
zero medians summarize the defined subset, not invented directions at
those two vertices. The other field rows and F4 have 256/256 directions.
These clean zeros come from identical-reference controls; they are not an
independent test of invariance to changing the reference.
All noisy primary and sentinel outer loops have defined endpoint directions
at all their sampled vertices; this does not override a loop-level winding
branch-ambiguity failure.

At primary P128, the curved F2 row medians span **rho 1.914–3.368 and
49.48–144.25°**, compared with quadratic **rho 0.01625–0.03907 and
0.633–1.176°**. F4 spans **rho 1.172–2.320 and 24.44–99.79 coefficient
degrees** for curved, versus **0.01489–0.06234 and 0.579–1.633 coefficient
degrees** for quadratic. These are ranges over four seeded units' three
correlated field rows, not 12 independent trials or a fitted classifier.

## 4. Why absolute reference error alone was insufficient

For the primary side-65 noisy panel, the next table expands the scale
comparison. `median m` means the median sampled `min(a,b)`; `median s`
means the median minimum amplitude along each sampled vertex's artificial
reference segment. Each range covers the four registered seeds and three
field rows at that fixed construction/P, after calculating each row's
median separately. Full per-unit/per-row quantities remain in the reports.

| Construction | Field | P | Median D range | Median m range | Median s range |
| --- | --- | ---: | --- | --- | --- |
| Curved | F2 | 8 | 0.0300200–0.0588127 | 0.0158189–0.0263789 | 0.00492458–0.0185387 |
| Curved | F2 | 32 | 0.00984970–0.0213668 | 0.00667621–0.00899715 | 0.00579749–0.00705167 |
| Curved | F2 | 128 | 0.00672321–0.0134849 | 0.00320063–0.00394375 | 0.00144048–0.00316700 |
| Curved | F4 | 8 | 0.0303265–0.131294 | 0.0190881–0.0442550 | 0.0173597–0.0386923 |
| Curved | F4 | 32 | 0.0310198–0.0613031 | 0.0113222–0.0286010 | 0.00392760–0.0127186 |
| Curved | F4 | 128 | 0.00823186–0.0162661 | 0.00506996–0.00921073 | 0.00423351–0.00892832 |
| Quadratic | F2 | 8 | 0.0300305–0.0591443 | 0.294836–0.303453 | 0.294836–0.303453 |
| Quadratic | F2 | 32 | 0.00933226–0.0194679 | 0.307441–0.309266 | 0.307441–0.309266 |
| Quadratic | F2 | 128 | 0.00602263–0.0126615 | 0.309456–0.310883 | 0.309456–0.310883 |
| Quadratic | F4 | 8 | 0.0165593–0.129552 | 0.292018–0.305846 | 0.292018–0.305846 |
| Quadratic | F4 | 32 | 0.0190862–0.0587594 | 0.294552–0.308761 | 0.294351–0.308761 |
| Quadratic | F4 | 128 | 0.00467060–0.0161701 | 0.307339–0.311619 | 0.307339–0.311619 |

Absolute reference perturbations decrease in scale over the tested P
ladder, but the curved residual itself also becomes smaller. The reference
change therefore remains large relative to that residual. The quadratic
residual instead stays near 0.3 on the outer loop, so comparable absolute
changes produce much smaller relative and angular changes. This is a
descriptive mechanism for the different sensitivity in these constructions,
not a guarantee of monotonic behavior at every vertex or seed.

For example, unit 08 (curved, P128, seed 2) has F2 median D approximately
0.010846, median m 0.003201–0.003916, median s 0.001440–0.001606, and median
absolute angle 143.21–144.25°. The matched quadratic unit 20 has median D
approximately 0.010806, median m and s approximately 0.310289, and median
angle 1.089°. The original +2 quadratic winding and reference-dependent
curved winding are retained results, not recomputed discoveries here.

## 5. Sampled near-zero flags do not certify loop clearance

None of the outer-loop vertex segments in the **24 noisy primary units**
reaches the `1e-6` floor, although many of their original A/B winding
readouts differ. Checking these sampled vertices therefore does not rule
out a winding disagreement or establish that a continuous spatial/reference
path avoids zero between vertices.

Conversely, two noisy sentinels reach the floor at one sampled vertex
despite their corresponding endpoint winding agreeing in all nine cells:

| Unit / field row | Hypothesis | Flagged vertices | Minimum sampled segment amplitude | Original A/B winding |
| --- | --- | --- | --- | --- |
| 24 / mutual-kNN | F4 | 1/1,024 | `7.901649706546776e-7` | both +1, 9/9 cells |
| 25 / shared-neighbor | F2 | 1/1,024 | `4.999918440772973e-7` | both +1, 9/9 cells |

These are below-floor amplitudes, not verified exact zeros or cores. In
this panel, a sampled-vertex floor flag is neither necessary nor sufficient
for a difference between the recorded endpoint sampled winding integers.
No intermediate-reference winding was calculated or selected.

The noiseless curved controls also retain their two below-floor F2
fixed-radius vertices, at minimum amplitude about `9.46393834e-7`.
Their three corresponding graph cells remain neither admitted in the
original winding comparison. In noisy unit 05, B's three F4 branch-ambiguous
cells remain A-only admitted even though all sampled endpoint directions
are defined. Pointwise completeness and loop-level admission are separate.
All five original categories remain intact in each output record.

## 6. Execution, tests, and receipts

The analysis ran from
`/home/ryospiralarchitect/scratch/spirallens-reference-perturbation-20260904-04lTk9/checkout`
with outputs in its sibling `campaign` directory. It used Python 3.14.4,
NumPy 2.5.2, CPU only, one child/BLAS thread, and the prospectively fixed
120-second unit / 900-second campaign limits. No stage failed, timed out,
or remained unrun. No model, CUDA computation, new fit, new observation,
or new winding readout was involved.

The largest reported pre-write child RSS high-water was **113,319,936
bytes** (108.07 MiB), sampled after diagnostics but before final JSON
serialization; it is not an externally measured full-process-lifetime peak.
Output files totaled **144,695,101 bytes** (137.99 MiB) before the manifest's
own write. The registered limits—4 GiB child address space, 256 MiB per
file, and a 1 GiB pre-unit disk-admission check—were not reached. This was
a small retained-array analysis, not a new hardware-capacity benchmark.

The 58 focused tests passed locally (0.57 seconds in the main run) and on
Furnace (0.49 seconds). They cover analytic vectors, floor/null behavior,
arm swaps and traversal reversal, exact input validation, mutation
rejection, field/schema/hash checks, and non-overwriting output. The combined
targeted local regression passed **268 tests with 8 CUDA-dependent skips**
in 11.86 seconds, including these 58 tests. These are scoped test results, not full-repository or
clean-wheel claims. No GitHub CI completion claim is made here.

All 32 output report hashes and the four new analysis source/plan/test
bindings were checked. The original campaign's 199 source/protocol/test
bindings were separately verified; every child checked its retained input
report and NPZ receipt. Multi-gigabyte raw probe arrays were neither copied
into Git nor downloaded for this analysis. The local collection at
`artifacts/p4-reference-perturbation-20260904/campaign/` contains all new
point series, null reasons, fixed summaries, copied endpoint outcomes,
and execution receipts. The returned compressed bundle is 38,022,233 bytes.
Campaign elapsed time includes child input verification; per-unit
`timing_seconds` starts after report/NPZ hash checks.

| Receipt | SHA256 or commit identity |
| --- | --- |
| Analysis implementation commit | `b18c2dec5baa67e0783b528559f5c3dd96066891` |
| Fixed exploratory plan | `53fbfd1409d03de7fb6c8ee44361213a8b1574920ca2d8b89120b289fb37c202` |
| NumPy diagnostic kernel | `d1d27e86607d0114337294cda6bde9c84f7f8e63c1df4285d3b20d0814a2043b` |
| Read-only campaign analyzer | `2834f2927d8634ff04889b986dcf7e865d6269a8bf90165576b8cf12cde29f1e` |
| Focused tests | `d8978fbf512c50fce2d19935e191ef8ff7b39c645b1f4313816458e0fb9f5c39` |
| Input campaign manifest | `a6268fa2cd5f7f0644fc7412c8c907afeb2d8d0f3f5763b7d3827d944300e857` |
| Input campaign plan | `b67fc15fe22e57410fe65e47980abd117a1b33d07a16b63b9bda532a7f779c3d` |
| Analysis execution plan | `763a394f082c4d3da56a8799fe8adba4146275302abe27c17b1aa5a6403a9856` |
| Analysis manifest | `2d5fc1395e1d586e09d6ec1e18015fd5e0b104783563fa6c088ddb4ca9b5adab` |
| Returned report bundle | `b5c75887503718aae53f6637d524ca957868e3d6554e595d8dc4d1887ea417f9` |

No scientific-authority, verified-core, model-derived-order-parameter,
phase/transition, D7/D8, SCI-S1/S2, or Pythia-160M gate changes follow.
The next claim-bearing use of these descriptors would need a separately
fixed experiment and an explicit interpretation rule, rather than a rule
chosen to separate the already observed constructions.
