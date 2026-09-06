# P4 independent reference validation: prospective paired protocol

Decision date: 2026-09-04. Status at registration: planned, not observed.
Synthetic development / Level 0. This document is fixed before the new
Furnace panel. Results belong in a separate report and must not rewrite
this prospective record.

## Question

The paired-probe screen showed admitted nonzero affine-residual winding
when only baseline-fit observations were noisy and plane/evaluation probes
were clean. Test how much the residual readout changes when two independently
drawn reference fits see the same fixed clean evaluation, and measure their
prediction errors on a third, spatially held-out observation set.

This is an instrument/reference-sensitivity experiment. It does not test a
neural model or claim that true geometry is absent whenever a residual
direction is unavailable. It does not select a better baseline using the
held-out observations, fit a threshold after results, or seek a positive
winding before stopping.

## Fixed panel and experimental unit

Every unit contains two reference arms A/B and one validation role V.
Both arms use identical clean plane-fit and evaluation probe arrays, the
same domain, k=8 graphs, five loops in both directions, and fixed core
triangulation. Both F2/F4 and all six estimands are retained. The core
adjacency axis remains fixed: 3 × 3 × 1, not full graph qualification.

| Panel | Side | Construction | Seed | Probes per point | Baseline/validation noise | Paired units |
| --- | --- | --- | --- | --- | --- | --- |
| Primary repeated references | 65 | curved coherent, quadratic excess | 0, 1, 2, 3 | 8, 32, 128 | 0.03 | 24 |
| High-resolution sentinels | 257 | curved coherent, quadratic excess | 0, 1 | 128 | 0.03 | 4 |
| Noiseless controls | 65 | curved coherent, quadratic excess | 0 only | 8, 128 | 0 | 4 |

Total: **32 paired units, 64 arm measurements**, each with nine graph cells.
The seeded A/B/V noise draws are the repeated synthetic units; nested P,
shared domains, graph cells and deterministic cube repetitions are not
additional independent replications. Report each size/construction/P/seed
combination, not a pooled discovery rate or a fitted significance claim.

## Input and role separation

Clean eight-probe cube directions are repeated to P=8/32/128. A new explicitly
tagged seed protocol spawns separate A/B/V streams from each registered
seed. Each role consumes a conceptual `(N,128,3)` stream, selecting the
first P draws per vertex. Implement chunking without changing that ordering.

Within the same domain, input prefixes are paired across P. Across domain
sizes, a reused seed is not coordinate-paired. Neither this A/B/V protocol
nor its P8 input is a replay of previous noisy screens. Bind the implementation
and actual input hashes before interpreting its results.

The reference training stencil remains the five exact coordinates
`(0,0), (-0.5,0), (0.5,0), (0,-0.5), (0,0.5)`.
The eight fixed validation coordinates are
`(-0.5,-0.5), (-0.5,0.5), (0.5,-0.5), (0.5,0.5),
(-0.25,0), (0.25,0), (0,-0.25), (0,0.25)`.
Assert exact vertex membership and disjointness from the training stencil.
V uses separate random noise, and only the eight held-out observations enter
validation. Its values must not enter frame estimation, A/B coefficients,
field/core seals, winding or loop selection.

## Chronology and unchanged gates

Construct the shared domain/graphs and clean plane/evaluation data. Fit and
seal all three graph-row baselines for **both** A and B before reading any
evaluation moments, held-out V values, winding or holonomy. Each arm then
uses its already-fixed reference. Its 36 charge-blind core seals precede
its own loop readouts. Do not choose an arm after seeing either result.

Retain predecessor support/eigengap/locality/amplitude/branch-cut gates and
the analytic zero isotropic pass-through F4. Failed cells remain unavailable,
not zero. No new held-out acceptance threshold is introduced in this panel.

## Registered outputs

- Full per-arm reports: graph/domain identities, support, affine coefficients,
  chronology, fields/core memberships, all loops and every estimand/F2/F4.
- A/B residual comparison with the full nine-cell denominator: both admitted
  and equal winding, both admitted and different winding, A-only admitted,
  B-only admitted, and neither admitted. Preserve reasons and values rather
  than treating two unavailable values as agreement. Summaries may focus on
  the fixed outer-forward loop but retain all other readouts in artifacts.
- Where both references exist, verify the algebraic decomposition
  `residual_A - residual_B = -(affine_A - affine_B)` on the identical full
  evaluation field, reporting maximum absolute numerical discrepancy.
  This identity only locates the change in the reference subtraction; it
  does not establish a physical topological invariant.
- For each field-graph row and F2/F4, evaluate both affine predictions on
  the same V stencil. Retain individual Euclidean errors, root mean squared
  vector error, and maximum error, with V/input/stencil/fit hashes. These
  are uncalibrated held-out prediction diagnostics, not pass/fail tests or
  confidence intervals. In particular, small held-out errors need not make
  the direction of a near-zero residual identifiable.
- Keep all raw inputs necessary to replay, shared input identities, per-arm
  derived arrays and V observations. Deduplicate equal shared arrays, but
  do not discard failed or discordant arms.

## Execution and decision boundary

Use CPU NumPy reference computation for this new paired panel. The optional
CUDA adapter remains available from the prior independently validated work;
this protocol does not infer new whole-chain CUDA coverage or speed.

Before execution, bind the committed protocol, numerical sources and fixed
32-unit list in a plan receipt. Use a fresh isolated Furnace checkout and
output directory; leave existing workloads and managed model runtimes alone.
Run one child at a time, with one BLAS/OpenMP thread, 180-second per-unit and
1,200-second campaign wall budgets, 16 GiB child address-space limit, 2 GiB
per output-file limit and an 8 GiB pre-unit disk-admission budget. These
resource gates must retain timeouts, failed attempts and unrun units.

Independent validation is informative even if both references agree, both
fail, or held-out prediction errors are small while residual winding differs.
Any follow-up change in fit stencil, uncertainty estimator, seed count,
evaluation noise, or decision threshold requires a new prospectively fixed
panel. D7/D8, SCI-S1/S2, the Pythia-160M gate and all model/scientific authority
remain unchanged.
