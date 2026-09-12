# P4 one-arm admission: registered local strength slices

Decision date: 2026-09-05. Status at commitment: specified, not run.
Synthetic development / Level 0. This is a targeted exploratory follow-up
selected from observed results, not an independent confirmation panel.
Commit this document before generating the new local strength observations.

## Question and selected windows

Does an isolated A-only outer-loop entry resolve into a narrow interval,
multiple admission changes, or a sampling-sensitive boundary? Track both
reference arms, both F2/F4, and the exact stopped spatial edges.

Selection source: the complete 429-unit strength campaign at implementation
`ada7e04ece44948267054e487aa3ac0ed1ea7eca`, manifest SHA-256
`f0b5bc294ef7c18ca1ff2bbab99c9fe7aa9d3dabfa029aee11850718147357a7`.
The primary outer-forward display has exactly these three A-only units;
other retained loops contain B-only entries. Selection is specific to the
outer loop and this observed grid, not evidence of an intrinsic A advantage.

| Window | P | Seed | Lower / center / upper alpha | Selected hypothesis | Old units |
| --- | ---: | ---: | --- | --- | --- |
| f4-p8-s1 | 8 | 1 | 0.002 / 0.003 / 0.004 | F4 | 41 / 42 / 43 |
| f4-p8-s3 | 8 | 3 | 0.08 / 0.10 / 0.125 | F4 | 121 / 122 / 123 |
| f2-p128-s0 | 128 | 0 | 0.008 / 0.01 / 0.0125 | F2 | 276 / 277 / 278 |

All three center failures are B-side
`branch_cut_or_undersampling_ambiguity`. Their sampled minimum amplitudes
are above the unchanged 1e-6 floor. B's neighboring admitted windings are
respectively -1 to 0, 0 to +1, and -1 to +1. These are endpoint observations,
not assertions about how many intervening changes occur.

For each window, divide lower-to-center and center-to-upper into sixteen
equal intervals using exact decimal arithmetic, then convert each value
once to float64. Include the center once: **33 points per window, 99 paired
units / 198 arm measurements**. The original nine anchors are replays;
90 strength conditions are new. Keep all points, including unavailable or
failed entries. No result-dependent refinement within this campaign.

## Construction and pairing

Use the unchanged flat construction `F2=F4=z+0.25*alpha*z^2`, side65
(4,225 vertices), k8, and baseline/V noise scale0.03. Each strength generates
its own clean probes, moments and separate A/B affine fits. Preserve the
P4SS noise namespace, vertex-major max128 draws and first-P selection from
the predecessor. The same raw A/B/V draws are reused across each window
and its old anchors. Do not create a new random namespace for this zoom.

Retain all nine graph cells, five loops in both directions, six estimands,
F2/F4 and original core adjacency. The primary paired denominator is
**17,820 loop/hypothesis records**. The three windows reuse three seed pairs
from the earlier four-seed panel; graph cells, strength points, reversals,
and replays are correlated observations, not independent trials.

All six reference seals precede held-out V and evaluation reads; each arm
seals its 36 charge-blind core records before loop measurements. V remains
diagnostic. Preserve every original gate, including amplitude floor1e-6
and maximum adjacent principal angle strictly below pi-0.15 radians.
Do not assign a winding value to an insufficient branch.

## Primary diagnostics

At every retained loop, hypothesis and graph cell, preserve A/B state,
reason and eligible sampled winding. Add continuous diagnostic distances
to the amplitude and angular gates, the minimum-amplitude sampled vertex,
and the maximum-angle edge with ordered vertex IDs, coordinates, signed
angle and endpoint coefficient vectors. Keep all tied extrema identifiable
in the retained arrays; a displayed argmin/argmax uses the first index.
These edge/vertex diagnostics are not qualified physical cores.

Verify diagnostics against sealed residual values, support, frames and
the original report. Keep existing reference-difference magnitudes and
coefficient angles. F4 coefficient phase is spin-two, not a physical
director angle. Missing fields or loop support remain unavailable.

Report every sampled run of A-only/B-only/other categories, with first/last
sampled alpha and preceding/following sampled brackets. Do not infer
continuous interval endpoints or certify an absence between samples. Show
all nine cell counts if they differ. Keep admitted A and B windings visible
around stopped entries, without filling their null values.

## Separately labeled sampling and symmetry controls

After the original measurements, perform algebraic A/B-label exchange on
the paired reports: A-only must map to B-only and vice versa; other paired
categories must stay unchanged. This is a labeling check, not a new draw.

For each arm, F2/F4 and field graph on outer-forward, replay the scalar
principal-angle estimator on (a) the complete ordered samples cyclically
shifted by one, and (b) every second sample at offsets0 and1. Keep the same
amplitude/branch thresholds. Cyclic shift must preserve reliability,
eligible integer and extrema up to floating-point tolerance. The two
128-point decimations explicitly change the sampled path; report their
changes relative to the original256-point estimator. They do not inherit
graph/loop admission and do not replace original measurements. This is a
coarsening sensitivity check, not spatial refinement or a measurement
between vertices. Denominator: 99 x 3 field rows x 2 hypotheses x 2 arms x
3 transformed sample sequences = **3,564 derived estimator checks**.
Any finer spatial construction needs a separate prospectively fixed panel.

## Execution, verification and outputs

Implement successor sources; leave all byte-pinned predecessors unchanged.
Before the panel, test exact decimal grids and old-anchor identity, noise
pairing, actual seal chronology, all-cell/loop retention, original nulls,
edge orientation, cyclic/reversal/swap behavior, decimation scope, and
tampered/missing artifacts. Small side17 fixtures test plumbing only.

Run on a new isolated Furnace checkout using the NumPy CPU reference,
one child / one BLAS thread, nice10. Bounds: 180 seconds per unit,
900 seconds overall, 8 GiB child address space, 2 GiB per file and
4 GiB pre-unit output-disk admission (not a filesystem quota). Preserve
attempts, failures, timeouts and all unrun registered positions.

Freeze source hashes and checkout revision in the launch plan. Verify
full-report, NPZ and compact hashes, unchanged source bindings, raw-noise
pairing and the nine old anchors against their retained source reports.
Retain full reports and arrays on Furnace; return all compact records,
diagnostic cross sections and verification receipts. Add a results document
and an interactive zoom beside the earlier display. Continue commits on
PR#122: plan, tested implementation, then completed results.

No D7/D8, SCI-S1/S2, Pythia-160M, verified-core, model-derived order
parameter, physical phase/transition or scientific-authority promotion is
implied by this synthetic panel.
