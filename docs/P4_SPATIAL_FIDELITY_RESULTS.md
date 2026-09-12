# P4 spatial fidelity: readable total winding is not faithful local geometry

Completed on 2026-09-06: **102/102 units**, with no failed, timed-out or
rerun measurement units. The registered three-part experiment separates
sampling error, frozen-reference error and local-structure recovery.
The results are synthetic development / Level 0, not a model digital twin.

## 1. Two stopped edges resolve differently

The original references and physical square boundary were unchanged. New
positions received newly generated P128 probes and the existing NumPy
moment measurement, not interpolation of old residuals. All216 anchor
comparisons (18 conditions x3 rows x2 hypotheses x2 arms) have maximum
coefficient difference **exactly0**, and their scalar states replay.
An independent post-run check also verifies byte equality for all432
full/residual array comparisons. Fresh audit moments match the analytic
construction within6.33e-15 absolute coefficient-vector error.

For P128/seed0 F2, armA remains sampled winding0 at every resolution:

| alpha / armB | 256 points | 512 points | 1,024 points |
| --- | --- | --- | --- |
| 0.00825: eligible winding | insufficient | insufficient | -1 |
| maximum adjacent angle | 178.8555 deg | 178.5933 deg | 125.8465 deg |
| minimum amplitude | 7.759627e-5 | 7.648576e-5 | 1.044356e-6 |
| 0.01: eligible winding | insufficient | 0 | 0 |
| maximum adjacent angle | 172.9941 deg | 141.7887 deg | 137.6735 deg |
| minimum amplitude | 1.426340e-4 | 1.562638e-5 | 1.562638e-5 |

The unchanged angular limit is171.405633 degrees and the amplitude floor
is1e-6. At alpha0.00825 the refined minimum is only**1.04436 times** that
floor, at (0.7265625,1). Its maximum-angle edge is now
(0.734375,1) -> (0.7265625,1). The alpha0.01 maximum-angle edge contracts
to (-1,-0.578125) -> (-1,-0.5859375).

Thus refinement removes these sampled angular stops, but one newly visible
point is barely above the amplitude floor. This is not a continuous-path
clearance proof, a stable physical charge or permission to erase the old
insufficient records. All1,296 forward/reverse, A/B, F2/F4, three-row
sampled-loop readouts are retained. Finer grids do not inherit graph admission.

## 2. The stable +2 region is reference-error limited

At alpha0.08,0.10,0.20 every sampled arm (eight A/B arms across four seeds)
recovers+2 for both F2/F4 at all three resolutions. At0.04, F2 is8/8 and
F4 is5/8; this lower bracket is not silently folded into the stable band.

Each resolution predicts the same1,024 held-out physical boundary points.
Directly measured audit values define the frozen-reference target; the
known injected quadratic defines the separate ideal target. At alpha0.10:

| Boundary samples | Sampling-only coefficient RMSE, median | F2 reference RMSE, median | F4 reference RMSE, median |
| ---: | ---: | ---: | ---: |
| 256 | 4.464989e-6 | 0.006501992 | 0.006973274 |
| 512 | 1.144409e-6 | 0.006501992 | 0.006973274 |
| 1,024 | 3.814697e-7 | 0.006501992 | 0.006973274 |

Sampling RMSE is equal for F2/F4 to the displayed precision and falls by
about11.7 times overall. The reference error does not change with sample
count because both the reference and audit points are fixed. At1,024
points it is roughly17,000–18,000 times the sampling error at these medians.
These are absolute coefficient errors, not normalized effect sizes.

Phase RMS against the **ideal injected field**, median over the eight arms:

| alpha | F2 phase RMS | F4 coefficient phase RMS |
| ---: | ---: | ---: |
| 0.04 | 21.109 deg | 26.984 deg |
| 0.08 | 10.334 deg | 11.392 deg |
| 0.10 | 8.227 deg | 8.992 deg |
| 0.20 | 4.091 deg | 4.418 deg |

All stable-panel phase comparisons retain1,024 valid audit points. These
truth-relative RMS values differ from the earlier A/B median angle metric.
At0.10 the eight-arm ranges are4.391–10.050 degrees forF2 and
3.782–24.273 degrees forF4; the medians do not erase the latter tail.
F4 is the spin-two coefficient phase, not physical director rotation.

## 3. Correct outer charge can coexist with the wrong internal structure

The84 local units are seven fixtures xfour new geometry seeds xthree
grids. They contain504 distinct ideal/A/B xF2/F4 reconstructions, addressed
by all three field rows as1,512 records after exact reference equality is
checked. Geometry seeds100–103 are new; the four A/B reference pairs are
reused, not new independent noise trials.

The charge-blind locator sees only measured coefficients and grid
coordinates. It seals possible-zero components before component/outer
loop readings; only the scorer receives known centers and charges. The
fixed0.10 spatial-unit matching tolerance is a development scoring rule.
No expected count or oracle-centered loop is passed into reconstruction.

At256 cells per side:

| Known injected structure | Ideal reference: exact local recovery | A/B: exact local recovery | A/B: correct outer charge |
| --- | ---: | ---: | ---: |
| one center,+2 | 8/8 | 0/16 | 16/16 |
| separated pair,+1/+1 | 8/8 | 0/16 | 16/16 |
| close pair,+1/+1 | 8/8 | 0/16 | 16/16 |
| reverse pair,-1/-1 | 8/8 | 0/16 | 16/16 |
| dipole,+1/-1 | 8/8 | 0/16 | 16/16 |

In all16 noisy-reference single +2-center cases, the measurement resolves
**two charged components instead of one**, while its outer value remains+2.
For geometry seed100, F2/A puts the two+1 components near
(-0.210938,-0.019531) and(0.082031,0.527344), although the injected+2
center is(-0.014556,0.072626). The ideal-reference estimate is
(-0.013672,0.074219), error0.001822.

These are deviations from the **injected target geometry**. They do not
mean the locator hallucinated roots of the measured residual: subtracting
an imperfect reference changes that residual field itself. Nor does0/80
mean every coordinate is wrong; the exact-structure rule requires correct
count, matched positions and charges together. Raw matches, misses,
extra components, zero-charge candidates and unresolved reasons remain.

With the ideal reference, the close pair is separately recovered in0/8,
6/8 and8/8 cases at64,128,256 cells respectively. Earlier stops arise from
overlapping component loops, not disappearance of the outer+2. At256
cells all40 ideal localized fixtures have the right structure, with maximum
matched position error0.003668 spatial units. This is the regime where
finer sampling genuinely improves this particular reconstruction.

Controls are also informative. The nonzero constant field has no recovered
charged cores in all16 noisy-reference cases at256 cells. The identically
zero injected field is globally below the floor under the ideal reference,
with no defined winding; imperfect references instead yield a resolved
charged component in10/16 cases. Do not score an undefined zero-field
outer winding as0. The null is retained, not promoted to a physical defect.

## Interpretation and next bounded question

The three parts now give a concrete fidelity budget: refinement can resolve
a sampling stop or separate nearby candidates, but cannot remove a fixed
reference's field distortion. Total winding alone cannot establish that a
synthetic reconstruction preserves centers, separations or local charges.

The next useful design is reference-uncertainty control and independently
held-out localization, centered on the0.08–0.10 region. Separate the
uncertainty of total charge from position and split/merge uncertainty; do
not post-hoc change this panel's scoring rule to make it pass. A future
background-only calibration lane must declare its changed estimand. Tests
also verify why refitting the entire translated/split quadratic absorbs
its constant/linear displacement terms; such refitting is not a remedy
that can silently preserve the original target.

No D7/D8, SCI-S1/S2, Pythia-160M, verified-core, model-derived order
parameter, holonomy, physical phase/transition or scientific-authority
gate changes. This bench is progress toward instrument fidelity, not a
validated digital twin of model dynamics.

## Execution, verification and artifacts

Plan commit:`7bf29bd`; execution source:
`e3c1ceef6929d965fff0c794cbcd504b84b39ac3`. Furnace isolated checkout:
`/home/ryospiralarchitect/scratch/spirallens-spatial-fidelity-20260906-0K3KWR/checkout`.
No GPU/model use, one CPU child and one BLAS thread, nice10. The campaign
took81.779224 seconds, peak child RSS184,852,480 bytes. Compressed raw arrays
total288,326,744 bytes and remain in the sibling `campaign/` on Furnace.

The198-test focused suite passes on both Mac and Furnace, including30 new
fidelity tests. During development, the seed7 close-pair test initially
expected128-cell separation too early; it was corrected to preserve the
actual overlapping-loop stop and256-cell recovery. No gate was loosened,
and no registered measurement unit needed retry.

Post-run verification checks207 source bindings,18 input report/array
pairs,204 output report/array hashes, and replays all1,800 distinct loop
readouts/local reconstructions from the saved arrays. Source and input
hashes are checked before and after measurement. The returned compact
archive has exactly516 files; local verification checks each extracted
byte, all102 attempt/terminal pairs,102 report hashes and regenerated
summary/visual projections. Raw-array replay occurred on Furnace, not Mac.

Local evidence:`artifacts/p4-spatial-fidelity-20260906/campaign/`, including
every report, attempt, terminal result and both logs. The interactive view
shows all three spatial grids and F2/F4 simultaneously, with seven fixture
and four seed choices, truth/ideal/A/B overlays and explicit unresolved
points. It is checked at736/360px in light/dark themes, including all28
fixture/seed selections, actual marks, clipping, legend and pinned detail.

| Binding | SHA-256 |
| --- | --- |
| Protocol | `4047e7f318bc5b89a4716667299267eb2171c8862f5ba3d63e3fddaed601e3f4` |
| Launch plan | `6d4c363960a5d8a91d3cd054702c061a46dd25efeac7b111271bc5c555cb4029` |
| Manifest | `3fa9be889c484aafe8b77572e9b21411b46153a334d63b2d043180c16ed99023` |
| Summary | `1a6fd2261096909d8c82314d7230bf9815a83591cd293d94763bf6c2d848e670` |
| Visual data | `1862c1f1e18b5d47e594b35940b75307499b609121f1825caf62444e36dfe07a` |
| Furnace verification | `371beaf35b5a9765dd39c966e8e200113303403f331d70e8aaebe535083c074e` |
| Returned archive,1,674,167 bytes | `28008551f2993b017688557c4ccb2bd52af4da1947246989df70b4251a35f347` |
| Local returned-evidence verification | `9c2caae06d0154372bdd38e1cee07c037671ba08c60d31cfdb1362297256ae8b` |
| Independent exact-anchor verification | `e4a42f40e821a9c7fafa208212ba228cb16390647fa090ffdf663287b11e5c9e` |
| Compact-summary helper | `04c631acd891b8bdf72c3c7ef09e5abf5810f05fcf509d46d64bed138a1b9e4a` |
| Interactive spatial view | `ad27fb9c7c2157de8aa0056094beb99472b3d05d91c6936203eb65dba711b39d` |
| Final visual checks | `4972d9786f47700d980e0b0455530d9c0b1cd515996b0f50f6acf14b072ab1de` |
