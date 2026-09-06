# P4 reference perturbation: fixed exploratory reanalysis plan

Decision date: 2026-09-04. Status at commitment: analysis specified, not run.
This document is frozen before computing the new diagnostics. The 32 input
pairs and their winding outcomes already exist and informed this question;
this is **post-hoc exploratory reanalysis**, not preregistered confirmation
on new observations. Synthetic development / Level 0 only.

## Question and immutable inputs

How large is a change of affine reference compared with the residual it
leaves, and how much does that residual's direction change at the same
sampled vertices of the same fixed loops?

Use all 32 pairs from `P4_REFERENCE_VALIDATION_RESULTS.md`, in original order,
without resampling, fitting, model access, choosing an arm, or changing a
measurement gate. The original numerical source commit is
`465238be0fe9b63bbe83fbd40408b2484d7d75e8`.

The input campaign manifest SHA256 is
`a6268fa2cd5f7f0644fc7412c8c907afeb2d8d0f3f5763b7d3827d944300e857`;
the input plan SHA256 is
`b67fc15fe22e57410fe65e47980abd117a1b33d07a16b63b9bda532a7f779c3d`.
Every report and NPZ must match the original manifest before analysis.
Input files are read-only; results go to a new, non-overwriting directory.
Validate the retained array-to-arm mapping and field/frame/support hashes.
Require the two arms to share clean full fields, frames, support and paths.
Retain failed/missing units in the denominator instead of skipping them.

The fixed denominator is 32 paired units, each with 9 field/loop graph cells,
5 named loops in both orientations, and 2 affine-residual hypotheses (F2/F4):
5,760 loop/hypothesis records. Repeated graph cells, reverse traversal,
nested probe widths and noiseless copies are not independent replications.
Primary descriptive summaries remain outer-forward; every other loop and
direction is retained, not selected after looking at diagnostics.

## Same-frame sampled-point measurements

At each vertex, let `rA = full - affineA`, `rB = full - affineB`,
`d = rB-rA = -(affineB-affineA)`, `a=norm(rA)`, `b=norm(rB)`, and `D=norm(d)`.
Check the subtraction identity against the stored affine arrays; neither
arm is assumed to be ground truth. All quantities use the same recorded
two-dimensional coefficient frame at that vertex.

Retain the following numerical series along each fixed loop:

- `a`, `b`, `D`, and the signed amplitude change `b-a`.
- `D/a`, `D/b`, and `D/min(a,b)`, without clipping large values or replacing
  small denominators by an epsilon. A ratio is null if its denominator is
  at or below the existing amplitude floor, `1e-6`.
- Signed coefficient-space angle `atan2(det(rA,rB), dot(rA,rB))` in radians
  and a summary of its absolute magnitude, only where both amplitudes
  exceed the floor and both supports are valid.
- Radial and transverse components about A: `dot(d,rA)/a` and
  `det(rA,d)/a`, only where A has a defined direction. These are oriented
  diagnostics about a labeled arm, not a preferred reference.
- Endpoint angular slopes along the fixed reference segment,
  `det(rA,d)/a^2` and `det(rB,d)/b^2`, on their respective defined supports.

F2 angles refer to vector coefficient direction. F4 angles refer to the
spin-two coefficient phase, **not** a physical director angle; they are
not halved and must not be compared as if both hypotheses had the same
physical-angle convention. No across-vertex frame transport is inferred
from these pointwise comparisons.

At each retained vertex also describe the artificial affine-reference
segment `r(lambda)=rA+lambda*d`, `0<=lambda<=1`. The closest approach is at
`lambda*=clip(-dot(rA,d)/D^2,0,1)`; when `D=0`, set `lambda*=0`.
Retain lambda*, the minimum segment amplitude, and its ratio to `min(a,b)`
where the latter denominator is defined. Record how many supported vertex
segments reach the existing floor. This is an algebraic interpolation
between already observed references, not an additional observation, fit,
probability distribution, or claim about physically possible references.
Do not compute or select an intermediate-reference winding in this slice.

For every series, use fixed descriptive summaries: valid count, minimum,
25th percentile, median, 75th percentile, maximum. Also retain the required
vertex count, support count and separate defined-direction counts. Preserve
nulls and reasons; serialize no NaN/infinity. No adaptive bins, inferred
confidence interval, p-value, uncertainty cutoff or acceptance threshold.

## Missingness and interpretation

Copy the original A/B winding states/reasons/values without changing them.
Keep all five paired admission categories, including neither-admitted.
A graph-uncoverable loop remains unavailable; no numerical reanalysis may
promote it. For a covered loop with partial point support, only supported
point diagnostics may be reported, with their explicit coverage and an
incomplete status. Small-amplitude points retain amplitude diagnostics but
not invented directional values. Missing fields remain unavailable.

Large relative perturbation and angular disagreement can help locate
reference sensitivity. Neither a ratio above one nor a sampled vertex
segment approaching zero is sufficient to establish a winding change.
Conversely, positive minima at sampled vertices do not exclude a zero
between vertices or establish continuous spatial/reference-path topology.
Endpoint agreement is not evidence of independence from every reference.
The held-out V errors and original winding/core readouts are not recomputed
or used to select a favorable row, arm, path, threshold, or construction.

## Implementation, execution, and retention

Add a separate NumPy diagnostic kernel and read-only campaign analyzer,
with analytic-vector tests (identical, radial, transverse, antipodal,
near-zero, unsupported), reversal/arm-swap checks, schema/hash mismatch
checks, exact denominator checks and non-overwriting output behavior.
Keep all predecessor sources, plans and results byte-identical.

Commit this plan first; commit and test the implementation before invoking
it on the retained Furnace campaign. Use an isolated checkout, CPU only,
one child at a time, one BLAS thread, 120 seconds per unit, 900 seconds
overall, 4 GiB child address-space cap, 256 MiB per-file cap and a 1 GiB
pre-unit output-disk check (admission check, not a hard filesystem quota).
Read only the necessary NPZ entries; do not copy raw multi-GB inputs to Git.
Bind analysis source/plan/input hashes, attempt/terminal status and all
output digests. Return compact reports with per-loop arrays and summaries.

Results belong in a separate document; do not rewrite this frozen plan.
No D7/D8, SCI-S1/S2, Pythia-160M, scientific-authority, verified-core,
model-derived-order-parameter, phase or transition gate changes are allowed.
