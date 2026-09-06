# P4 spatial fidelity: frozen references, field error, and local structure

Decision date: 2026-09-06. Status at commitment: specified, not run.
Synthetic development / Level 0. Commit before new measurements. This is a
targeted exploratory successor, not independent scientific confirmation.

## Three questions and the separation that matters

1. Does genuine spatial refinement resolve the two P128 stopped edges?
2. In the +2 region, how much error is sampling error and how much remains
   because the fitted reference differs from the ideal background?
3. Can a charge-blind local reconstruction distinguish one double zero,
   two separated zeros, a close pair, reversed charge and a net-zero dipole?

Keep the original A/B reference coefficients frozen. A new fitted reference
at every spatial resolution would confound these questions. In particular,
refitting a translated/split quadratic can absorb its constant and linear
terms; the local-structure lane therefore injects a new residual over the
same background z and uses the previously sealed references, without refit.
This is controlled reference-error transfer, not fresh reference validation.

## Immutable inputs and outer-loop panel

Strength campaign manifest SHA-256:
`f0b5bc294ef7c18ca1ff2bbab99c9fe7aa9d3dabfa029aee11850718147357a7`.
One-arm zoom manifest SHA-256:
`7b5a8529f0332109cbef71804dbf3b365ca3064c8717b87f827df1a3ffbc3125`.

Read the full reports and retained arrays, verify their manifest-bound
hashes, field seals, coordinates, frames, support and affine coefficients.
Require the known constant xy frame in both arms and all three field rows;
otherwise stop rather than invent a frame at the new points. Require exact
row equality before deduplicating the local-structure reference arrays.

The 18 outer conditions are P128/noise0.03/side65/k8:

- alpha0.04,0.08,0.10,0.20 at each original seed0,1,2,3 (16 conditions);
- alpha0.00825 and0.01 at seed0, from zoom units68 and82 (two stop controls).

At each condition keep both F2/F4, A/B, all three original field rows and
both loop orientations. Sample the identical physical square [-1,1]^2
boundary at 256,512,1024 points, beginning at (-1,-1), forward CCW.
Use nested physical points and generate clean P128 probes at the new
positions, then measure with the existing NumPy moment adapter. Do not
interpolate the old measured residual arrays to create observations.
There is no new noisy baseline, no changed noise-to-coordinate assignment,
and no new graph/loop admission at the finer positions.

This gives 18 x3 resolutions x3 rows x2 hypotheses x2 arms x2 orientations
= **1,296 sampled-loop readouts**. The original256-point observations must
match stored full/residual fields within absolute1e-12, and original scalar
states, reasons and eligible integers must replay. Keep insufficient null.

Retain max adjacent angle, min amplitude and their physical edge/point,
eligible integer and failure reasons. The gates remain amplitude>1e-6 and
max principal edge angle<pi-0.15; these are finite sampled diagnostics, not
continuous winding certification or inherited nine-cell graph admission.

## Error decomposition in the stable region

The scoring truth for the old centered construction is r*=0.25*alpha*z^2.
For each fixed reference r_A/r_B, report coefficient-vector error to r*,
amplitude error, phase error only where both amplitudes exceed the floor,
and the A/B residual difference and coefficient phase angle. Preserve the
phase denominator; never assign direction to a zero. F4 phase remains the
spin-two coefficient phase, not a physical director rotation.

Use 1,024 fixed audit positions: odd-indexed points of the2,048-point
boundary. They are disjoint from all primary grids. Measure their probes
directly once. At every primary resolution score periodic piecewise-linear
coefficient reconstruction on these same audit positions against (a) the
direct frozen-reference field and (b) ideal r*. Report complex RMSE,
amplitude RMSE and circular phase RMS/max with valid counts separately.
Sampling error can decrease while the reference-induced field error stays.
Do not label a three-resolution trend as an asymptotic proof or use it to
retune any threshold. Alpha0.04 and0.20 bracket the central0.08–0.10 band.

## Local-structure panel and truth-blind reconstruction

At fixed alpha0.10 use each original seed0–3 A/B reference, plus the exact
ideal background coefficient matrix [[0,0],[1,0],[0,1]]. Pair these with
four previously unused geometry seeds100–103. They are new geometry draws,
not independent new noise/reference draws. Generate geometry with
NumPy SeedSequence([geometry_seed,0x50345346]), drawing center x,y uniformly
in [-0.25,0.25], then orientation uniformly in [0,pi). No outcome selection.

Let c be that center, d=(separation/2)*exp(i*orientation), and a=0.025.
All clean observed coefficient fields are background z plus one of:

| Fixture | Injected residual | Scoring truth |
| --- | --- | --- |
| double | a*(z-c)^2 | one center, charge+2 |
| wide | a*(z-c-d)*(z-c+d), separation0.4 | two centers,+1,+1 |
| close | same, separation0.08 | two centers,+1,+1 |
| reverse | conjugate of wide | two centers,-1,-1 |
| dipole | a*(z-c-d)*conj(z-c+d), separation0.4 | two centers,+1,-1 |
| constant | a*exp(i*orientation) | no isolated zeros |
| zero | 0 | everywhere degenerate, no isolated core truth |

Measure actual P128 probes/moments on square grids with64,128,256 cells
per side (65,129,257 vertices per side). Generate in bounded batches.
Keep F2/F4 and ideal/A/B. Reuse the same six measured fields across the
three field rows only after exact reference/frame equality is verified.
There are **84 fixture/grid units**, **504 distinct field reconstructions**,
and **1,512 row-addressed reconstruction records**. They are correlated.

The reconstructor receives only grid coordinates and measured residual
values, never fixture names, centers, charges or expected counts. A cell
is a charge-blind possible-zero cell if both coefficient components span
zero among its four corners, with1e-12 roundoff allowance. Join cells by
8-neighbor connectivity. Keep each component, its bounding box and the
mean of its cell centers; do not fit an oracle-centered loop. Fields wholly
at/below the1e-6 floor are globally unresolved, not isolated-core positives.

Seal the input hash, possible-zero mask and all component locations before
reading any loop charge. Around each component take its bounding rectangle
expanded by one grid cell, using measured grid-boundary vertices. Boundary
clipping, overlap with another component's loop, component extent>0.5 or
an insufficient loop are explicit unresolved conditions. Do not silently
drop these components. A reliable zero-charge component is retained but
not counted as a recovered charged core; it can conceal a close dipole.

Only after reconstruction and loop readout may the scorer load the truth.
Report raw candidate and resolved charged-component counts, positions,
boxes, charges, misses, false positives and localization distances. Use
one-to-one minimum-total-distance matching with a fixed0.10 spatial-unit
maximum match distance (dummy unmatched assignments allowed); this is a
development scoring convention, not a new scientific admission threshold.
Report charge correctness separately and preserve all unmatched positions.
Also score the outer boundary: correct total charge alone must not count as
correct local structure. A split double zero and a true separated pair are
different targets even when both outer loops report+2.

## Execution and receipts

Implement successor files only. Tests precede the campaign: nested-grid and
anchor parity, exact background/moment convention, finite inputs, missing
or tampered source evidence, fixed-reference identity, forward/reverse and
zero controls, charge-blind extraction, seal-before-charge chronology,
truth-side scoring, merge/split behavior and full planned denominators.
Test fixtures do not use the four registered held-out geometry seeds.

Execute on an isolated Furnace checkout, NumPy CPU, one child and one BLAS
thread, nice10. Bounds:180seconds per unit,1,800seconds campaign,8GiB child
address space,2GiB per file,4GiB pre-unit disk admission. Do not disturb
other jobs or managed runtimes. No model or GPU is required by this panel.

Retain the102 planned unit positions (18 outer+84 local), including failed,
timed-out and unrun units. Launch plan binds committed source and protocol,
input manifests and exact selected artifacts. Check input/source hashes
before and after measurement; preserve original evidence unmodified.
Retain raw measured fields on Furnace, return compact outputs and receipts;
verify reconstruction replay from arrays and audit metrics independently.
Commit plan, tested implementation, then results on existing PR#122.

This is an instrument-fidelity synthetic bench, not a validated digital
twin of model dynamics. No D7/D8, SCI-S1/S2, Pythia-160M, verified-core,
model-derived order parameter, holonomy, physical phase/transition or
scientific-authority gate is changed.
