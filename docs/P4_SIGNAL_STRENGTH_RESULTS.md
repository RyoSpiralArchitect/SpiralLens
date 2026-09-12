# P4 signal-strength cross sections: prospective exploratory results

Decision date: 2026-09-04. **429/429 paired units / 858 arm measurements
completed**, preserving **77,220 loop/hypothesis paired records**, in
758.909836 seconds (12 minutes 38.91 seconds). No experimental unit failed,
timed out or remained unrun. Synthetic development / Level 0 only.

The main result is a separation of stages: recovering the injected sampled
winding is easier than making the residual direction insensitive to the
reference. More probes move the sampled recovery boundary downward in this
fixed panel, but a recovered integer is not a small-angle certificate.

## 1. Prospective contract and construction

The [33-level plan](P4_SIGNAL_STRENGTH_PLAN.md) was committed at `2731277`
before the new strength observations. Implementation and execution used
`ada7e04ece44948267054e487aa3ac0ed1ea7eca`. This is a prospectively fixed
exploratory synthetic panel, not a calibrated statistical confirmation.
Prior reference-sensitivity results motivated the design.

Only the injected component changes: on a flat substrate, the clean fields
are `F2=F4=z+0.25*alpha*z^2`. Alpha=1 is byte-identical to the earlier clean
quadratic anchor. Alpha=0 leaves a linear full field; it is neither an
all-zero full field nor the old curved-coherent control. Each strength
generates its own probe means/covariances and receives its own reference
fits. Previously measured residuals were not multiplied by alpha.

All units use side65 / 4,225 vertices, k8, all nine field/loop-graph cells,
five fixed loops in both directions, six estimands and both F2/F4 fields.
Primary readouts below use outer-forward, containing 256 sampled vertices.
The core adjacency, support, branch and amplitude rules are unchanged.

The noisy panel has P8/P32/P128 × seeds 0–3 × all 33 strengths = 396 pairs.
The noiseless P128/seed0 stripe adds 33 pairs. P4SS A/B/V standard-noise hashes
match across every strength and nested P for the same seed; the twelve
A/B/V stream hashes are mutually distinct across roles/seeds. Thus there
are **four seed pairs / eight baseline streams and four validation
streams**, not 858 independent trials. Noiseless copies consume no random
draws. Graph rows, strength points, reversed loops and P prefixes are
correlated. Repeating a clean cube does not create independent observations.

All six reference fits were sealed before V/evaluation moments; each arm
sealed 36 charge-blind core records before any loop readout. Held-out V
never selected a reference, strength, graph or threshold.

## 2. Complete finite-grid recovery descriptors

For each trace, require every one of the nine graph cells to have both
reference arms eligible at sampled winding +2. The table gives
`preceding sampled alpha -> first sampled alpha satisfying that condition`.
In **all 26 hypothesis traces**, that first sampled point also begins the
suffix that stays +2 through every remaining sampled strength. There were
no sampled post-recovery breaks or re-entries. This is not evidence of
continuity or monotonicity between samples.

| P / seed | F2 sampled bracket | F4 sampled bracket |
| --- | --- | --- |
| 8 / 0 | 0.125 -> 0.15 | 0.25 -> 0.35 |
| 8 / 1 | 0.08 -> 0.1 | 0.15 -> 0.2 |
| 8 / 2 | 0.1 -> 0.125 | 0.125 -> 0.15 |
| 8 / 3 | 0.1 -> 0.125 | 0.125 -> 0.15 |
| 32 / 0 | 0.06 -> 0.08 | 0.08 -> 0.1 |
| 32 / 1 | 0.05 -> 0.06 | 0.08 -> 0.1 |
| 32 / 2 | 0.04 -> 0.05 | 0.08 -> 0.1 |
| 32 / 3 | 0.05 -> 0.06 | 0.08 -> 0.1 |
| 128 / 0 | 0.03 -> 0.04 | 0.015 -> 0.02 |
| 128 / 1 | 0.025 -> 0.03 | 0.06 -> 0.08 |
| 128 / 2 | 0.02 -> 0.025 | 0.04 -> 0.05 |
| 128 / 3 | 0.03 -> 0.04 | 0.04 -> 0.05 |
| 128 / 0, noiseless | 0.000003 -> 0.00001 | 0.000003 -> 0.00001 |

Across all four seed pairs together, the earliest persistent sampled
strengths are F2/F4 **0.15/0.35 at P8**, **0.08/0.10 at P32**, and
**0.04/0.08 at P128**. These are finite-panel descriptors, not general
detection limits. F4 is not uniformly harder than F2: at P128/seed0 it
recovers first at 0.02, before F2 at 0.04; the other seeds differ.

The next table retains every registered strength. Each entry is
**F2 pair count / F4 pair count**, each out of the four noisy seed pairs,
where each counted pair itself has all nine cells at +2 in both arms.

| Alpha | P8: F2 / F4 | P32: F2 / F4 | P128: F2 / F4 |
| ---: | ---: | ---: | ---: |
| 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.000001 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.000003 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.00001 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.00003 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.0001 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.0003 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.001 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.002 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.003 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.004 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.006 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.008 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.01 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.0125 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.015 | 0 / 0 | 0 / 0 | 0 / 0 |
| 0.02 | 0 / 0 | 0 / 0 | 0 / 1 |
| 0.025 | 0 / 0 | 0 / 0 | 1 / 1 |
| 0.03 | 0 / 0 | 0 / 0 | 2 / 1 |
| 0.04 | 0 / 0 | 0 / 0 | 4 / 1 |
| 0.05 | 0 / 0 | 1 / 0 | 4 / 3 |
| 0.06 | 0 / 0 | 3 / 0 | 4 / 3 |
| 0.08 | 0 / 0 | 4 / 0 | 4 / 4 |
| 0.1 | 1 / 0 | 4 / 4 | 4 / 4 |
| 0.125 | 3 / 0 | 4 / 4 | 4 / 4 |
| 0.15 | 4 / 2 | 4 / 4 | 4 / 4 |
| 0.2 | 4 / 3 | 4 / 4 | 4 / 4 |
| 0.25 | 4 / 3 | 4 / 4 | 4 / 4 |
| 0.35 | 4 / 4 | 4 / 4 | 4 / 4 |
| 0.5 | 4 / 4 | 4 / 4 | 4 / 4 |
| 0.65 | 4 / 4 | 4 / 4 | 4 / 4 |
| 0.8 | 4 / 4 | 4 / 4 | 4 / 4 |
| 1 | 4 / 4 | 4 / 4 | 4 / 4 |

All original non-+2 admission categories remain in the compact records.
A count of zero here does not mean zero winding, absent signal, or an
unmeasurable field. At alpha=0, all noisy outer-loop arms are measurable,
but none of the twelve pairs recover +2 in both arms. F2 has five pairs
with admitted agreement and seven with admitted disagreement; F4 has one
agreement and eleven disagreements. Agreement alone does not identify
the intended quadratic component.

## 3. Magnitude and direction do not collapse into winding

For the same vertex and coefficient frame, `D=norm(rB-rA)` and
`rho=D/min(norm(rA),norm(rB))`. A ratio or angle is null when either endpoint
direction is undefined; the existing amplitude floor is 1e-6. No epsilon
replacement or ratio clipping is used.

Every number below is a range of **per-field-row medians over vertices**,
over the four seed pairs and all three field rows at P128. These are
descriptive ranges, not confidence intervals or twelve independent trials.
The median of pointwise ratios is not the ratio of separate medians.
Angles are absolute principal coefficient-angle differences in degrees.
**F4 degrees are spin-two coefficient phase, not physical director
rotation, and are not halved.**

| Alpha | F2 median rho range | F2 median angle, degrees | F4 median rho range | F4 coefficient angle, degrees |
| ---: | --- | --- | --- | --- |
| 0 | 1.8771–2.5891 | 74.887–121.48 | 1.9203–2.9803 | 84.557–110.55 |
| 0.001 | 1.9231–2.6572 | 74.962–119.78 | 1.9943–2.9824 | 84.396–110.53 |
| 0.01 | 2.0258–2.4515 | 60.774–106.34 | 1.7136–2.3824 | 51.469–104.58 |
| 0.02 | 1.1091–2.1258 | 35.797–77.545 | 0.89952–2.0567 | 24.203–95.551 |
| 0.03 | 0.80086–1.4614 | 27.966–46.28 | 0.58996–1.9626 | 14.772–77.095 |
| 0.04 | 0.6117–1.0252 | 22.263–33.993 | 0.41016–1.6393 | 11.105–48.895 |
| 0.05 | 0.50189–0.78637 | 18.094–26.839 | 0.31112–1.3042 | 8.6877–39.137 |
| 0.08 | 0.31301–0.46383 | 11.304–16.481 | 0.17877–0.80814 | 5.4708–28.239 |
| 0.1 | 0.24373–0.36225 | 9.0171–13.165 | 0.13852–0.65172 | 4.2946–22.845 |
| 0.2 | 0.11535–0.16765 | 4.5824–6.4976 | 0.06743–0.3116 | 2.1337–11.136 |
| 0.5 | 0.044626–0.065092 | 1.8281–2.5681 | 0.026656–0.11739 | 0.8737–4.3554 |
| 1 | 0.022081–0.032182 | 0.90907–1.2832 | 0.013039–0.057243 | 0.43837–2.1529 |

At alpha 0.04, every P128 F2 pair has recovered +2 across all nine cells,
yet the median relative change remains **0.61170–1.0252** and the median
angle **22.263–33.993 degrees**. At alpha 0.08, all P128 F4 pairs also recover,
yet their coefficient-angle medians still span **5.4708–28.239 degrees**.
Integer agreement therefore precedes small directional sensitivity in this
construction; no angular acceptance cutoff was introduced.

The absolute reference difference did not disappear at this boundary.
For P128 F2, row-median D spans **0.0072954–0.010675** across seeds, essentially
unchanged over the entire alpha ladder. The largest within-trace change
in median D across all P/seed/field-row traces is 1.345e-15. This is consistent
with the matched additive-noise construction and linear F2 mean reduction.
By contrast, F4 median D changes by as much as 0.0010878 in a single trace,
consistent with its strength-dependent clean covariance. Shared raw noise
does not make every derived moment error invariant.

P128 F2 arm-A amplitude medians grow from **0.0033998–0.0071576** at alpha 0
to **0.31190–0.31289** at alpha 1, while reference-difference scale stays
similar. Relative perturbation and angular sensitivity shrink accordingly.
This maps the instrument's signal-to-reference balance; it does not
separate real model structure from artifacts by a learned threshold.

## 4. The noiseless floor is not a physical onset

The noiseless arms are exact duplicates. At alpha 0 and 1e-6, no outer-loop
endpoint directions are defined. At alpha 3e-6, **108/256 vertices** have
defined directions in every field row for both F2 and F4, but both loops
remain insufficient. At alpha 1e-5 all 256 directions are defined and all
nine cells admit +2 in both arms. Null directions were never entered as0.

The analytic clean affine residual is `0.25*alpha*z^2`; the symmetric
five-point stencil removes none of its quadratic component. On this
outer square the minimum residual amplitude is `alpha/4`, so the fixed
floor lies at alpha 4e-6, between the registered 3e-6 and 1e-5 samples.
The observed bracket is consistent with that instrument floor. It is not
a phase transition and does not show that the quadratic component begins
to exist at 1e-5.

## 5. All-loop denominator and unavailable outcomes

These counts include all 429 pairs, nine graph cells and ten oriented
loops, separately for each hypothesis (38,610 records each).
They are correlated record counts, not probabilities.

| Hypothesis | Both admitted, equal | Both admitted, different | A only | B only | Neither admitted |
| --- | ---: | ---: | ---: | ---: | ---: |
| F2 | 27,882 | 10,080 | 108 | 162 | 378 |
| F4 | 27,720 | 10,404 | 72 | 36 | 378 |

There were no mixed admission categories among graph cells within a
fixed unit/loop/hypothesis in this flat panel. That repeated agreement
does not establish graph-independence or general robustness. Full reports
retain actual winding values, reasons, every estimand and held-out
diagnostics. Compacts retain all row/loop summaries, support/direction
counts and nulls. Raw NPZ supports exact pointwise perturbation replay;
long derived point arrays were not redundantly serialized at every strength.

## 6. Execution, validation and receipts

Furnace ran the immutable source checkout on Python 3.14.4 / NumPy 2.5.2 /
SciPy 1.18.0, CPU only, one child and one BLAS thread, nice10. No GPU/model
runtime was installed or used; no other workload was modified. The
registered 180-second unit, 2,400-second campaign, 8-GiB child address-space,
2-GiB file and 12-GiB pre-unit disk-admission bounds were not hit.

Peak reported child RSS was **199,016,448 bytes**. Outputs before the
manifest write occupied **7,484,820,420 bytes**. The returned compact archive
is **7,001,231 bytes** and excludes raw NPZ/full reports.

Validation before the registered campaign:

- New strength tests: 34 passed locally, including clean-anchor byte parity,
  analytic weak/zero moments, noise pairing, actual seal chronology,
  output tampering, fixed denominators, re-entry and incomplete-trace handling.
- All P4 test modules plus the generated-view module:789 passed, eight
  CUDA-absence skips, in 116.18 seconds. This is not a full-repository test claim.
- Furnace strength/reference/perturbation tests: 134 passed in 3.45 seconds.
- The source commit passed all three GitHub clean-wheel matrix jobs:
  [run 33866410018](https://github.com/RyoSpiralArchitect/SpiralLens/actions/runs/33866410018).
  Subsequent result-document commits have separate CI runs.

After execution, all 203 source bindings matched the launch plan.
All 429 full reports, 429 NPZ files and 429 compact reports passed another
hash check on Furnace (1,287 artifact checks). On the Mac, the transferred
archive hash, all 429 compact hashes, all 77,220 record denominators,
chronology fields and all twelve shared-noise stream identities were
verified. The HTML overview shows every unit; 736/360-pixel light/dark
checks cover all 858 marks, labels, overflow and selection behavior.
Its displayed numeric ranges are rounded; the JSON receipts retain the
full serialized precision.

Furnace raw evidence and isolated checkout:

`/home/ryospiralarchitect/scratch/spirallens-signal-strength-20260904-cHSocJ/`

Local compact evidence and derived summaries (ignored by Git):

`/Users/ryohiga/SpiralReality/spirallens-p4-partial-pattern-prototype/artifacts/p4-signal-strength-20260904/`

| Object | SHA-256 |
| --- | --- |
| Frozen plan document | `0b19fde1b97f7a752f30788f36af41428a2ea99a92f6df202a05eb114f463582` |
| Launch plan.json | `6b06f93b7c9d6686c09c53c93b85f22f43453ce42ffb53d6645f3b2f01e7deba` |
| Campaign manifest.json | `f0b5bc294ef7c18ca1ff2bbab99c9fe7aa9d3dabfa029aee11850718147357a7` |
| cross_sections.json | `8929fc4d9c6ef917052444f2435b60d5531801d3b445aa3a93b3824692edeecb` |
| Post-run verification.json | `e2b5239a27aa90c1fdb3d3b8cdd2214bfc859910210121afee7d8845b38922d8` |
| Compact archive | `0d56788d6efde320ebbacd1f9fcebd730d2211d3f71526b1faca00ac0a7d0f58` |
| Derived summary.json | `922dbb47627fa8dbe9fdec4efc79ab971cbd143bff936344476ed13cd28668af` |
| Local summary derivation | `07d5bac71d0a00cce6f0910d7c72b589dfdd474f3edd2724aceaeed3988344b3` |
| Inline overview fragment | `f808afe5d8bf88b349c1381aae03eec9438909af80f6851654304e4ab4200757` |

The source kernel/runner/test hashes remain bound in CI and the launch plan.
Campaign artifacts remain append-only evidence; no failed predecessor
evidence was replaced. No new model-derived order parameter, verified core, holonomy,
physical phase/transition, calibrated detection threshold or scientific
authority follows. D7/D8, SCI-S1/S2 and Pythia-160M gates remain unchanged.

The useful next question is the interval **after integer recovery but
before small directional sensitivity**. Any extension should separately
fix a noise/loop-scale or reference-uncertainty comparison before new
observations; this panel does not authorize picking a favorable arm,
retuning an admission gate, or claiming a real-model finding.
