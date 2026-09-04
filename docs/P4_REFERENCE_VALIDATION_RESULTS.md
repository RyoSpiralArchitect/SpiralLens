# P4 independent reference validation: paired results

Decision date: 2026-09-04. Status: **32 of 32 paired units completed,
64 arm measurements**, in 181.703443 seconds. Synthetic development / Level 0 only.
This result record accompanies the immutable
[prospective paired protocol](P4_REFERENCE_VALIDATION_PLAN.md). It must not
rewrite that protocol or substitute a favorable subset for the registered
32-unit denominator.

The motivating observation was reference sensitivity in the
[paired probe/CUDA screen](P4_CUDA_PROBE_SENSITIVITY.md): a noisy affine
reference could produce an admitted nonzero residual winding even though
plane and evaluation observations were clean. The present screen measures
that dependence with independently drawn reference arms A/B and a third,
spatially held-out observation set V. It does not choose a winning reference
or reinterpret a synthetic winding as a model phase or verified core.

## 1. Prospective registration and PR history

The work is developed in [draft PR #122](https://github.com/RyoSpiralArchitect/SpiralLens/pull/122).
The history separates previous experiments, new prospective registration,
implementation, and subsequent observations:

| Commit | Purpose |
| --- | --- |
| `49501d7` | Previously completed P4 graph-cross, sparse scaling, paired probe sensitivity, and thin CUDA work |
| `36f2de0` | Register the new A/B/V reference-validation protocol before its panel |
| `5392938` | Refresh generated status digests for the experiment records |
| `465238b` | Implement, test, and source-bind the independent A/B/V screen before Furnace execution |

The full numerical implementation commit is
`465238be0fe9b63bbe83fbd40408b2484d7d75e8`. Furnace fetched that exact public
repository commit into a new isolated checkout; this run does not rely on
an uncommitted source archive. Prior numerical sources and the committed
prospective protocol remain byte-pinned; this result document is a separate
artifact.

## 2. Experimental unit and fixed denominator

Each unit contains two reference arms and one held-out validation role.
The paired arms share exactly the same clean plane-fit and evaluation
probe bytes, domain, graphs, support, and loop definitions. Only the
five-point reference fit's observations differ between A and B.

| Panel | Side / vertices | Construction | Seeds | Probes per point | Noise | Paired units |
| --- | --- | --- | --- | --- | --- | --- |
| Primary reference repeats | 65 / 4,225 | curved coherent and quadratic excess | 0, 1, 2, 3 | 8, 32, 128 | 0.03 | 24 |
| Resolution sentinels | 257 / 66,049 | both constructions | 0, 1 | 128 | 0.03 | 4 |
| Noiseless controls | 65 / 4,225 | both constructions | 0 | 8, 128 | 0 | 4 |

Total: **32 paired units and 64 arm measurements**. Every arm retains
3 × 3 field/loop graph cells with a single core adjacency, all five loops
in both directions, and all six estimands for F2 and F4. All use `k=8` and
zero warp. Graph cells, nested probe widths, deterministic cube repetitions,
and shared domains are not extra independent replications.

The new `ReferenceSpec` permits only the registered constructions,
probe-count ladder, domain-size ladder, and noise values 0 or 0.03. The
runner's case list is the narrower exact panel above. A failed stage or an
unavailable arm remains in its original denominator.

## 3. A/B/V inputs and actual chronology

`scripts/prototype_p4_reference_validation_v0_1.py` is a separate CPU-only
successor. It leaves prior module globals and source files unchanged,
reusing the frozen measurement bytecode through isolated per-call bindings.
The dense adapter is explicitly NumPy for this entire screen; no CUDA
selection or model access occurs here.

The protocol's seed tag is `0x50345256` (ASCII `P4RV`).
`SeedSequence([seed, tag]).spawn(3)` creates A, B, and V streams in that
order. Each consumes a conceptual `(N,128,3)` noise sequence and uses the
first P draws at each vertex. Chunking by 4,096 vertices changes memory
use, not stream order. Only V's eight held-out rows are retained and
evaluated. Within a fixed domain and seed, the P8/P32/P128 inputs are
prefix-paired; different domain sizes are not coordinate-paired.

Clean eight-probe cube directions are repeated across P. When noise is
zero, A/B are duplicate deterministic controls and the receipt reports
zero independent noise/reference draws. Neither those duplicates nor the
repeated cube directions count as additional independent experiments.

The five fit coordinates are
`(0,0), (-0.5,0), (0.5,0), (0,-0.5), (0,0.5)`.
The held-out coordinates, in fixed order, are
`(-0.5,-0.5), (-0.5,0.5), (0.5,-0.5), (0.5,0.5),
(-0.25,0), (0.25,0), (0,-0.25), (0,0.25)`.
Each must occur exactly once in the domain; the two index sets must be
disjoint. Their row/coordinate hashes are retained.

The implementation follows this sequence:

1. Construct shared domain/graphs and clean inputs; freeze input arrays.
2. Fit and seal the three graph-row baselines for A and all three for B.
3. Read V moments on its eight held-out rows and evaluate both fixed
   references' prediction errors.
4. Read arm A evaluation moments, seal its 36 charge-blind core records,
   and evaluate all loops.
5. Repeat the evaluation/core/loop sequence for B using its already-sealed
   reference; compare the complete A/B records.

The event record is generated at the actual preparation/moment/loop calls.
V is never used to refit, choose a graph, select an arm, or tune a threshold.
The existing plane support, affine-fit, amplitude, branch-cut, and loop
coverage gates remain unchanged. Inherited analytic isotropic pass-through
F4 remains zero; noisy or measured residuals are not clamped to zero.

## 4. Registered comparisons and held-out diagnostics

For each F2/F4 residual readout, the outer-forward summary retains five
mutually exclusive categories over all nine cells:

- both admitted, equal sampled winding;
- both admitted, different sampled winding;
- A only admitted;
- B only admitted;
- neither admitted.

The last category is not agreement. Paired records retain both arms'
states, reasons, coverage, and values at every loop/direction; an absent
winding is never replaced with zero. Other estimands and geometry remain
available in the full arm reports.

Where both affine references exist, the artifact also checks the exact
algebraic target
`residual_A - residual_B = -(affine_A - affine_B)`
by recording the maximum absolute numerical discrepancy and both delta
arrays. This locates the paired change in reference subtraction on an
unchanged evaluation field. It is not a proof of a physical invariant.

For each field-graph row and F2/F4, both affine predictions are evaluated
on the same V observations. The report retains all eight Euclidean vector
errors, their root mean square, and the maximum error, along with baseline
seals, V/input/stencil hashes, prediction arrays, and observed values.
The same registered noise scale applies to the independently drawn V
observations. These are uncalibrated noisy held-out diagnostics, **not an
admission test**, confidence interval, or new score for choosing an arm.

In particular, small prediction errors do not automatically identify the
direction of a near-zero residual. A/B agreement is also not independence
from the choice of reference. All results must retain those distinctions.

## 5. Execution results

All 32 prospectively registered units completed; none failed, timed out,
or remained unrun. All numerical results below come from the CPU reference
implementation, using Python 3.14.4 and NumPy 2.5.2 on Furnace. No baseline
was selected after seeing the readouts or held-out errors.

### Every registered paired outcome

The table gives the fixed outer-forward affine-residual comparison.
Each five-count tuple is **equal / different / A-only / B-only / neither**:
the first two categories require both arms to be admitted; every tuple
sums to nine graph cells. `Curved` means `curved_coherent`; `quadratic`
means `quadratic_excess`. Full individual values, reasons, all other loops,
and all estimands remain in the corresponding `unit-XX/report.json`.

| Unit | Construction | Side | Seed | P | Noise | F2: E/D/A/B/N | F4: E/D/A/B/N |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 00 | Curved | 65 | 0 | 8 | 0.03 | 0/9/0/0/0 | 0/9/0/0/0 |
| 01 | Curved | 65 | 0 | 32 | 0.03 | 0/9/0/0/0 | 0/9/0/0/0 |
| 02 | Curved | 65 | 0 | 128 | 0.03 | 6/3/0/0/0 | 9/0/0/0/0 |
| 03 | Curved | 65 | 1 | 8 | 0.03 | 0/9/0/0/0 | 0/9/0/0/0 |
| 04 | Curved | 65 | 1 | 32 | 0.03 | 0/9/0/0/0 | 9/0/0/0/0 |
| 05 | Curved | 65 | 1 | 128 | 0.03 | 6/3/0/0/0 | 6/0/3/0/0 |
| 06 | Curved | 65 | 2 | 8 | 0.03 | 9/0/0/0/0 | 0/9/0/0/0 |
| 07 | Curved | 65 | 2 | 32 | 0.03 | 0/9/0/0/0 | 0/9/0/0/0 |
| 08 | Curved | 65 | 2 | 128 | 0.03 | 0/9/0/0/0 | 0/9/0/0/0 |
| 09 | Curved | 65 | 3 | 8 | 0.03 | 9/0/0/0/0 | 0/9/0/0/0 |
| 10 | Curved | 65 | 3 | 32 | 0.03 | 0/9/0/0/0 | 9/0/0/0/0 |
| 11 | Curved | 65 | 3 | 128 | 0.03 | 0/9/0/0/0 | 0/9/0/0/0 |
| 12 | Quadratic | 65 | 0 | 8 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 13 | Quadratic | 65 | 0 | 32 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 14 | Quadratic | 65 | 0 | 128 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 15 | Quadratic | 65 | 1 | 8 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 16 | Quadratic | 65 | 1 | 32 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 17 | Quadratic | 65 | 1 | 128 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 18 | Quadratic | 65 | 2 | 8 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 19 | Quadratic | 65 | 2 | 32 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 20 | Quadratic | 65 | 2 | 128 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 21 | Quadratic | 65 | 3 | 8 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 22 | Quadratic | 65 | 3 | 32 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 23 | Quadratic | 65 | 3 | 128 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 24 | Curved | 257 | 0 | 128 | 0.03 | 0/9/0/0/0 | 9/0/0/0/0 |
| 25 | Curved | 257 | 1 | 128 | 0.03 | 9/0/0/0/0 | 0/9/0/0/0 |
| 26 | Quadratic | 257 | 0 | 128 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 27 | Quadratic | 257 | 1 | 128 | 0.03 | 9/0/0/0/0 | 9/0/0/0/0 |
| 28 | Curved | 65 | 0 | 8 | 0 | 6/0/0/0/3 | 9/0/0/0/0 |
| 29 | Curved | 65 | 0 | 128 | 0 | 6/0/0/0/3 | 9/0/0/0/0 |
| 30 | Quadratic | 65 | 0 | 8 | 0 | 9/0/0/0/0 | 9/0/0/0/0 |
| 31 | Quadratic | 65 | 0 | 128 | 0 | 9/0/0/0/0 | 9/0/0/0/0 |

All **16 quadratic paired units**—14 noisy and two noiseless—retain
sampled winding **+2** for both F2 and F4, in all nine cells of both arms.
That is stability of the explicitly injected synthetic component across
this finite reference screen, not evidence of a component in a real model.

The curved construction behaves differently. At side 65 and P128, seeds
2 and 3 still have different A/B winding in every graph cell for both
F2 and F4. Seeds 0 and 1 retain three F2-discordant cells each. One arm's
internal nine-cell agreement therefore does not establish independence
from the reference fit. In side-257 unit 24, for example, all nine F2
cells give A=0 and B=−1; in unit 25 all nine F4 cells give A=+1 and B=−1.

The three A-only F4 cells in unit 05 arise because B has
`branch_cut_or_undersampling_ambiguity`. In the noiseless curved controls,
both arms instead fail `amplitude_at_or_below_floor` in the same three
F2 cells. Those six unit/cell entries remain **neither admitted**, not
agreement. The other six F2 cells and all nine F4 cells in those controls
give zero winding. No unavailable readout was converted to zero.

### Held-out prediction improves without guaranteeing reference stability

For the primary side-65 curved panel, the following are descriptive
minimum-to-maximum ranges of the per-arm held-out Euclidean RMSE across
the four registered seeds and three field-graph rows. They are not
confidence intervals; the graph rows and nested probe widths are reused
measurements, not additional independent trials.

| P | F2 held-out RMSE range | F4 held-out RMSE range |
| --- | --- | --- |
| 8 | 0.017393–0.024973 | 0.028686–0.054607 |
| 32 | 0.006231–0.011839 | 0.014168–0.023546 |
| 128 | 0.004550–0.007099 | 0.005925–0.012803 |

The error ranges decrease over this probe ladder, but the A/B winding
table does not converge monotonically to agreement. For instance, P128
unit 08 has F2 RMSE approximately 0.00625 for A and 0.00455 for B, while
all nine cells give A=+1 and B=−1. This is evidence that better prediction
of the observed field did not by itself ensure a reference-stable residual
direction in this construction. It supplies neither a universal failure
law nor a calibrated threshold for deciding when a direction is real.

Conversely, a small absolute affine prediction error is not the goal of
the nonlinear anchor. The noiseless quadratic controls have held-out
Euclidean RMSE approximately **0.089076** for both fields and arms, while
their residual winding is stably +2. The affine reference intentionally
cannot explain the injected quadratic component. Ranking constructions or
choosing a baseline solely by lower held-out RMSE would conflate this
intended residual with reference error; this run performed no such ranking
or selection.

All 32 units' event records begin with the six A/B baseline seals before
any V or evaluation moment read. Across every available graph-row/F2/F4
decomposition, the maximum absolute discrepancy in
`residual_A - residual_B = -(affine_A - affine_B)` is
**5.551115123125783e-17**. That numerical identity and the identical shared
evaluation inputs locate these paired changes in the reference subtraction;
they do not attach scientific authority to the resulting winding.

### Validation and resource observations

The pre-run focused tests on Furnace passed: **42 passed** in 2.20 seconds.
The local focused run passed the same 42 tests in 3.23 seconds, including
actual moment/loop-call chronology, V/B mutation isolation, noisy prefix
pairing, and exact-noise-free A/B duplication. Those tests establish
implementation behavior, not a panel-level scientific finding.

The broader targeted local regression passed **564 tests**, with **8
CUDA-dependent tests skipped**, in 104.90 seconds. This is a selected
measurement/runner regression, not a full-repository or clean-wheel claim.

Execution uses
`/home/ryospiralarchitect/scratch/spirallens-reference-validation-20260904-9VtDwQ/checkout`
on branch `SpiralReality/furnace-reference-validation`, with outputs in its
sibling `campaign` directory. The prospective run receipt binds the exact
implementation commit, 199 source/protocol/test entries, and the immutable
protocol hash. This screen does not use the GPU or alter a model runtime.

The largest reported process peak RSS is **1,620,086,784 bytes**
(1,545.04 MiB), in side-257 curved unit 25. The 32 compressed raw-array
artifacts total **2,279,683,782 bytes** (approximately 2.123 GiB). The
campaign directory measured **2,348,799,296 bytes** before the manifest's
own write, approximately 2.187 GiB. No configured resource limit was hit;
this is not a hardware-capacity or Mac-infeasibility result.

### Source and artifact receipts

All 32 raw NPZ sizes and hashes were checked on Furnace; those arrays
remain in the remote `campaign/unit-XX/arrays.npz` directories. The compact
local collection is `artifacts/p4-reference-validation-20260904/campaign/`,
containing the plan, manifest, and every unit report. Verification covered
the 199 bound source/protocol/test entries, exact protocol and implementation
commit, and all 32 report hashes. The run checkout was clean after execution.

| Artifact | SHA256 or commit identity |
| --- | --- |
| Exact run commit | `465238be0fe9b63bbe83fbd40408b2484d7d75e8` |
| Immutable prospective protocol | `a2b9deb11e338e77a7228a47eb414fbdc4826a8ad6f3310c1beef12d7ab10212` |
| Reference measurement source | `1b9b0ed52cf3929edc3f66ddcfd760af61bd51a5b564747a87af0476d079805c` |
| Bounded runner source | `268c6f3dc69037e60e45a8b28af0dd2eba877c0dd187da58ceb8b09afa8a3c23` |
| Focused test source | `5a0ee59924e443d021d9d8ed0aca860040858e204b356b89966b6eb1c6f0562c` |
| Prospective run plan | `b67fc15fe22e57410fe65e47980abd117a1b33d07a16b63b9bda532a7f779c3d` |
| Campaign manifest | `a6268fa2cd5f7f0644fc7412c8c907afeb2d8d0f3f5763b7d3827d944300e857` |
| Compact report bundle | `4c60f59df5070fc4934278029d66d18d67fbb333d4ddf0ba74154176463bcd97` |

These receipts bind the observed execution; a published PR, a matching
hash, or a passing local test is not itself scientific validation. No
GitHub CI completion claim is made by this result record.

## 6. Reproduction and evidence layout

The one-pair CPU entry point uses a new output directory:

```bash
PYTHONPATH=src python scripts/prototype_p4_reference_validation_v0_1.py \
  --side 65 --probe-count 32 --seed 0 --pattern curved_coherent \
  --baseline-noise 0.03 --output /new/reference-pair-directory
```

`report.json` contains both full arm reports, paired readouts, held-out
diagnostics, chronology, source/input hashes, and runtime information.
`arrays.npz` retains shared clean inputs, A/B reference arrays, held-out V
observations and predictions, fitted coefficients, field/core arrays, and
the paired deltas. Equal shared derived arrays are stored once; the report's
per-arm array-layout map restores each predecessor-shaped arm data view.
The files are created once, without overwriting an existing directory.

The registered campaign limits remain one child at a time, one BLAS/OpenMP
thread, 180 seconds per unit, 1,200 seconds overall, a 16 GiB child virtual
address-space cap, a 2 GiB per-file limit, and an 8 GiB pre-unit disk check.
The disk check is admission before the next unit, not a hard filesystem
quota. Failed, timed-out, and unrun units must remain in the manifest.

No result here changes D7/D8, SCI-S1/S2, the Pythia-160M gate, or the
claim ceiling. Model-derived order parameters, verified cores, phase, and
transition remain unestablished. Any further change of reference stencil,
uncertainty estimator, noise protocol, or selection rule needs its own
prospectively fixed panel.
