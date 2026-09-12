# P4 graph-cross development prototype v0.1

Decision date: 2026-09-04. Status: implemented local synthetic development
slice; **not qualification**. The four self-test checks have passed. P4 v0.3
remains `planned_not_frozen_not_run`.

This successor connects the
[estimand-comparison prototype](P4_ESTIMAND_COMPARISON_PROTOTYPE.md) to a
three-field-graph by three-loop-support-graph panel. It is a bounded synthetic
implementation of part of M8 in the
[measurement-chain design](P4_PHASE_CAPTURE_MEASUREMENT_CHAIN.md), not the
complete M1–M9 qualification program. The
[M1 v0.1 development prototype](P4_GRAPH_SCALE_TRANSPORT_PROTOTYPE.md), its
observed law `m1-development-law-046`, and existing frozen protocols remain
unchanged. No development choice here prospectively qualifies that law.

The question is: **which partial patterns remain measurable when the graph
used to estimate the field and the graph asked to support its boundary are
changed independently?** An unsupported cell is part of the answer, not a
reason to discard one graph family or choose a more favorable field.

No model, tokenizer, activation capture, remote connection, transfer, Furnace
job, or external service is used. The added resource availability does not
change this local-only development scope. Consumed D7 outcomes, D8, SCI-S1/S2,
and Pythia-160M gates do not advance.

## 1. What is crossed

The two axes have different computational responsibilities:

| Axis | Three graph families | What the choice changes |
| --- | --- | --- |
| Field-estimation graph | mutual-kNN, fixed-radius, shared-neighbor | Neighborhood support contributing to the fitted representation plane and its derived fields/connection |
| Loop-support graph | mutual-kNN, fixed-radius, shared-neighbor | Whether the same predeclared oriented boundary has every required edge |

These are nine retained cells per synthetic construction, not nine independent
trials. Within each cell, F2 and F4 remain co-primary and the predecessor's
full, pass-through, local-affine, affine-residual, and pass-through-residual
estimands remain distinct. The evaluation-origin-centered control is also
retained with its imposed-origin-zero warning.

The field graph must enter the actual plane-estimation calculation. Merely
attaching three different graph labels to one previously fitted field is not
this comparison. The same field-graph result is deliberately reused across
its three loop-support columns: changing support alone must not secretly
refit a field or its baseline. Numeric equality between two field-family
results can occur on a flat, noiseless construction; equality is not itself
proof that the graph was ignored.

When different loop graphs all support the exact same boundary, their
numerical readouts intentionally agree for a fixed field-graph row. The
column axis tests support, not arbitrary numerical diversity. No alternative
paths or perturbations are introduced merely to make columns differ.

Likewise, the loop graph does not supply a replacement loop. All columns are
asked about the same declared boundary, with the same vertex identities,
orientation, and domain location. There is no graph-specific cycle search or
selection by a favorable holonomy or winding value.

## 2. Field-blind construction and fit-only estimation

Graph construction reads only the declared synthetic substrate coordinates,
vertex identities, and numerical distance/order information. It precedes
field readouts and cannot inspect fitted F2/F4 values, amplitudes, component
candidates, holonomy, winding, or residual outcomes. This ordering is a local
implementation boundary, not external provenance attestation.

The substrate is a declared synthetic representation of the sampling domain.
It is not a graph qualified on real model activations, and its support must
not be described as model-manifold locality. The field-blind graph substrate
and response probes are separately identified even when both ultimately
derive from one controlled construction.

For declared domain coordinates `(x, y)`, the four-coordinate graph substrate
is `(x + warp*x^3, y + warp*y^3, 0.2*x*y,
0.15*sin(pi*x)*sin(pi*y))`, plus separately generated Gaussian graph noise
scaled by `graph_noise * grid_spacing`. These coordinates are not the fitted
F2/F4 response. The bounded development parameters are fixed before readout:

| Item | Development value |
| --- | --- |
| mutual-kNN neighborhood size | `k = 8` |
| scale statistic | median fourth-nearest-neighbor distance |
| fixed-radius threshold | `1.15 * scale` |
| shared-neighbor parameters | `k = 8`, minimum shared neighbors `3` |
| minimum field-pool neighbors | `2`, in addition to the center |
| maximum field-pool distance | `0.75`, in the declared two-dimensional domain's Euclidean units |

The locality guard uses domain distance, separately from the four-dimensional
Euclidean metric used to build graphs. These are fixed finite-domain
development choices, not a new qualified parameter-transport law. They are
neither the M1 v0.1 law `046` nor permission to reuse its observed success as
prospective calibration.

Only plane-fit probes may determine the fitted plane and reference. The
field-estimation graph controls which plane-fit neighborhoods contribute to
that estimate. Baseline-fit probes and the fixed affine stencil then fit the
baseline in the already frozen reference; evaluation probes provide the
full response sections. Neither later probe role may change graph parameters,
plane neighborhoods, reference choices, or the affine stencil.

The estimator centers each vertex's raw plane-fit probes separately, forms
that vertex's covariance, and averages those covariances over the center and
its graph neighbors. Thus between-vertex shifts of probe means do not
silently become plane-fit variation. Deterministic eight-point covariance
carriers feed the pooled covariance through the existing fit API. They are a
numerical representation of reused fit information, **not eight new
independent observations**.

The center must have supported raw plane-fit probes before pooling, and the
pooled fit must independently satisfy its support, degree, and locality
conditions. Averaging differently oriented rank-one neighbors cannot rescue
an unsupported rank-one center into an eligible measured plane. The full,
baseline, residual, and origin-centered readouts use the same field-graph
fit; unsupported rows remain unsupported rather than receiving invented
field values.

Every residual is a new same-field numeric object. Its amplitude, direction
eligibility, sampled low-amplitude components, and winding are recomputed.
F4 retains tensor-stage subtraction and its doubled-angle convention. The
prototype neither subtracts winding integers nor borrows full-field amplitude
for a residual direction.

The connection remains derived from that field graph's plane-fit result. Its
relative holonomy is a separate geometry branch, not a correction to winding
and not a newly fitted geometry of each residual field.

## 3. Exact boundary support, including failure

The declared square domain and its oriented boundaries are fixed before any
graph is evaluated. Binding requires each actual directed boundary segment
with `max_span=1`. A short route between a segment's endpoints, a common
two-core, or a nonzero cycle rank cannot substitute for this exact receipt.
Removing a required boundary edge must make the affected loop unavailable;
the code may not reroute it through an interior hub.

The five predecessor supports remain separately identifiable: outer, inner,
two local boxes, and an off-core box. Every evaluated support retains forward
and reverse results. They are predeclared test supports, not loops inferred
from the largest observed charge and not generic homology classes.

A loop-support failure blocks loop quantities dependent on that boundary.
It does not delete a field numeric payload, an independently sealed sampled
component record, or another supported boundary. Conversely, a field's
zero-amplitude or fitting failure remains visible even if the loop graph has
all the required edges. Geometry and defect retain their own eligibility:
an eligible geometry result cannot repair an undefined defect field, and an
unavailable defect field does not erase eligible geometry.

An eligible sampled zero, an insufficient readout, and an unavailable fit
remain different states. No average over successful columns can turn a
required unavailable cell into agreement.

## 4. The core-adjacency limitation

The sampled low-amplitude component rule still uses the predecessor's fixed
declared-domain triangulation. This is a graph-dependent adjacency rule even
though it is fixed across the nine cells; it is **not graph-free**.

The plane-estimation choice may change the resulting field amplitudes and
therefore its sampled component candidates. That dependence does not mean
component connectivity inherits the field graph: connectivity still comes
from the separate fixed triangulation. This slice consequently does not
complete M8 core-graph robustness. A later qualification must either add the
required core-adjacency axis or explicitly define and qualify an estimator
whose core adjacency inherits the field graph.

All component records retain the predecessor's meaning: charge-blind sampled
low-amplitude regions, sealed before loop readout. They are neither verified
continuous zeros nor model-derived cores. A globally zero residual remains
direction-ineligible with unresolved cores rather than many discoveries.
The three field-graph rows each retain twelve component records (five
estimands plus the origin-centered control, each with F2 and F4). All 36
seals precede every winding readout; repeated loop-support columns reuse
those seals without turning them into additional inferred cores.

## 5. What an agreement summary may say

All graph-family pairs remain present, including insufficient and partially
supported cells. There is no selected best graph, best F2/F4 branch, best
baseline, or best loop. Summaries must identify their exact denominator and
retain the underlying nine-cell outcomes.

A complete agreement summary requires all nine cells to be eligible, all
three families to have distinct edge sets, and agreement under the stated
comparison. If only the eligible subset agrees, that is recorded as
eligible-subset agreement, not graph-cross stability. Winding comparison
uses the eligible sampled integers; each underlying unrounded readout remains
available. Continuous geometry comparison instead uses the actual transport
matrices, with maximum pairwise Frobenius distance at most the fixed
development tolerance `0.02`. This tolerance is not calibrated for model
geometry. Neither integer rounding nor equal defect windings imply equal
geometry.

Three different properties must not be conflated:

- **Edge diversity:** the named families actually have distinct edge sets on
  the declared substrate. This can be checked numerically; it is not a claim
  that they represent independent hypotheses or equally valid neighborhoods.
- **Evaluability:** the specified field/support/observable gates admit a
  particular readout. A cell count is a coverage report, not a detection rate.
- **Pattern agreement:** eligible readouts agree under a declared comparison,
  with every missing required cell still explicit. Similar synthetic outcomes
  are not statistical replication, uncertainty calibration, or topology.

The same probes, domain samples, field estimate, loops, and F2/F4 branches are
reused within the cross. Increasing the number of graph cells must not inflate
the number of independent observations. No binomial interval or model
false-positive rate follows from the nine cells themselves.

## 6. Development result and replay boundary

The single successor script is
`scripts/prototype_p4_graph_cross_v0_1.py`. With the checkout's core
dependencies available in its own environment:

```bash
PYTHONPATH=src .venv/bin/python -B scripts/prototype_p4_graph_cross_v0_1.py --self-test
PYTHONPATH=src .venv/bin/python -B scripts/prototype_p4_graph_cross_v0_1.py --demo
PYTHONPATH=src .venv/bin/python -B scripts/prototype_p4_graph_cross_v0_1.py --nuisance-panel
.venv/bin/python -I -B -m pytest -q -p no:cacheprovider tests/test_p4_graph_cross_prototype_v0_1.py
```

Each command emits its result to stdout; the prototype does not persist a
run artifact. The full demo trace retains graph edges and construction
receipts, row-specific pooled covariances and locality records, all twelve
fields per row and their component seals, exact boundary receipts, and every
forward/reverse loop cell. The compact nuisance panel has the narrower
retention scope described below.

The full demo defines ten cases, all on a 17-by-17 domain: eight default
constructions (`quadratic_excess`, `input_identity`, `affine_offset`,
`no_signal`, `f2_nonlinear_only`, `f4_nonlinear_only`, `collapsed_support`,
`collapsed_substrate`), another `quadratic_excess` with warp `0.75`, and
`curved_coherent` with probe noise `0.03`. The last case perturbs probes, not
graph coordinates; it is separate from the graph-noise panel below. The ten
cases imply 90 retained graph cells, not 90 independent synthetic trials.
The complete local demo ran all ten cases and emitted 19,195,808 bytes of
finite JSON to stdout, with no stderr output. It did not persist an artifact.

The following outer-loop results have been observed in the local development
run. All winding integers retain their own field's convention; F4 is doubled
angle. A cell count is the number of eligible repeated graph measurements.

| Construction | Affine-residual F2 / F4 | Independent geometry |
| --- | --- | --- |
| Default `quadratic_excess` | Both `9/9` eligible, each with winding `+2` | `9/9` eligible with zero relative holonomy |
| `quadratic_excess`, warp `0.75` | Both `4/9` eligible with winding `+2`; each retains `5` insufficient cells | `4/9` eligible with zero relative holonomy; incomplete support |
| `curved_coherent`, probe noise `0.03` | F2 `6/9` eligible with winding `+1`; F4 `9/9` eligible with winding `+1` | `9/9` eligible but graph-row disagreement |

The default quadratic construction has edge counts `1116`, `544`, and `1386`
for mutual-kNN, fixed-radius, and shared-neighbor respectively; the warped
quadratic has `1004`, `966`, and `1398`. The warped case is not complete
agreement merely because its four eligible cells retain the expected
synthetic winding. It demonstrates why all nine required cells must remain
visible.

The warped quadratic's actual outer affine-residual cross is below; F2 and
F4 have this same eligibility pattern and both wind `+2` in eligible cells.
Rows choose the field estimator; columns choose exact boundary support.

| Field graph / loop-support graph | mutual-kNN | fixed-radius | shared-neighbor |
| --- | --- | --- | --- |
| mutual-kNN | `+2` | insufficient | `+2` |
| fixed-radius | insufficient | insufficient | insufficient |
| shared-neighbor | `+2` | insufficient | `+2` |

The noisy curved-coherent case has three distinct fitted-frame fingerprints.
Its outer holonomy angles are approximately `0.744831`, `0.765005`, and
`0.648859` radians in field-family order. The maximum pairwise matrix
Frobenius distance is approximately `0.164163`, above the predeclared
development tolerance `0.02`. Thus genuine row-specific estimation can
produce complete geometry disagreement even when the boundary is supported
in every column. Equal winding integers would not remove that disagreement.

Crucially, the same **nominal coherent/null construction** produces winding
in its affine residuals. These residuals include the consequences of probe
noise, neighborhood-dependent plane estimation, and subtraction. This is a
development sensitivity or artifact warning, not evidence of discovered
nonlinear structure. Even F4's complete nine-cell residual agreement does
not elevate that interpretation: the cells reuse the same probes and are
not independent confirmations. Distinguishing those contributions requires
further controlled measurements, not selecting the more favorable branch.

The self-test reports four passing checks. The focused graph-cross test
suite reports **69 passed**. A related targeted regression reports **287
passed**, including those 69 new checks and the predecessor partial-pattern,
estimand, M1, measurement-design, referent, domain/exact-binding,
holonomy/winding phantom, and graph-construction/diversity checks. Lint,
format, and whitespace checks are clean. This is a targeted regression,
**not a full-repository test run**. The checked predecessor source, test,
and documentation fingerprints remain unchanged, as do the existing M1,
frozen-protocol, and qualification paths.

Any replay trace is a local numerical record, not signed evidence, external
attestation, or authority to freeze or launch an official protocol. Declared
role identities and array separation do not attest arbitrary external probe
provenance.

## 7. Narrow crossed nuisance panel

The separate development panel ran with fixed `curved_coherent` and crossed
grid side `{9, 17}`, warp `{0, 0.75}`, graph-noise scale `{0, 0.2}`, and graph
seed `{0, 1}`: 16 cases, each retaining all nine graph cells. Probe noise is
zero in this panel so that the crossed nuisance concerns graph construction,
not a simultaneously altered response-probe distribution.

The compact output retained every outer-loop cell for all five estimands,
both F2/F4 branches, and independent geometry, together with graph-input
fingerprints, graph-family and locality diagnostics. Each field family's
locality record includes its pooling fingerprint, maximum neighbor domain
distance, neighbor-mass-fraction range, and raw/pooled supported-row counts.
The finite JSON output was 945,607 bytes. This is a finite exploratory panel
with no held-out partition and no parameter reselection. It does not
calibrate a critical threshold or supply a qualified M9 surface.

The geometry summaries were **14 incomplete-support cases and 2
complete-disagreement cases**, with no complete-agreement case:

| Domain side | Warp | Graph noise | Cases | Eligible outer geometry cells per case |
| --- | --- | --- | --- | --- |
| `9` | both values | both values | `8` | `0/9` |
| `17` | `0` | `0` | `2` | `9/9`, but disagree across field-graph rows |
| `17` | `0` | `0.2` | `2` | `2/9` |
| `17` | `0.75` | both values | `4` | `4/9` |

The side-9 cases deliberately fall outside the inherited loop-resolution
guard: their outer boundary steps are `0.25` domain units, above its maximum
`0.2`. Field-fit support and missing exact boundary edges provide additional
reasons in some cells. Their `0/9` outcome therefore does not measure absence
of geometry, and cannot be read as a density-only scaling law.

The noiseless, unwarped cases also expose the finite locality range:

| Domain side | Maximum mutual-kNN pool distance | Maximum fixed-radius pool distance | Maximum shared-neighbor pool distance |
| --- | --- | --- | --- |
| `9` | `0.5` | `0.25` | approximately `0.790569` |
| `17` | `0.25` | `0.125` | approximately `0.395285` |

These are distances in the declared two-dimensional domain, not graph-
substrate distances. The side-9 shared-neighbor maximum already exceeds the
`0.75` pooling guard; with graph noise its maximum reaches `1.0` in this
panel. By contrast, all `289` raw and pooled rows are supported in every
field graph for the noiseless, unwarped side-17 case. Such measured support
and distance records support only descriptions of these finite runs,
not an asymptotic or real-activation locality claim.

The two fully evaluable cases are duplicate seed labels at zero graph noise,
not two independent disagreements. Their field-row outer holonomy angles
are approximately `0.743925`, `0.764704`, and `0.647388` radians, with maximum
pairwise matrix Frobenius distance `0.165814`. Both affine-residual sections
have `9/9` eligible sampled winding `0` in those noiseless cases. In the
other side-17 strata, both affine-residual sections have `0/9` eligible
outer-loop results; this is abstention, not evidence of zero winding or no
residual structure.

Comparing the zero-probe-noise, unwarped side-17 case with the demo's probe
noise `0.03` case makes the residual sensitivity concrete: an eligible
sampled-zero residual winding can become the previously reported `+1`
pattern. That comparison does not isolate whether plane estimation,
baseline fitting, or evaluation noise is responsible, because those probe
roles are perturbed together. It reinforces the need for role-separated
controls before interpreting a residual pattern as an object of interest.

At zero graph noise, the two seed labels reproduce the same graph inputs and
must not be counted as independent replications. At nonzero graph noise,
two seeds remain only two controlled realizations, not an estimated model
false-positive rate. No p-value or confidence interval is inferred from this
panel or from its repeated nine-cell measurements.

## 8. What remains before model observation

This development slice does not establish nuisance robustness outside its
recorded finite density, warp, graph-noise, seed, and graph-budget range, or a
shrinking locality limit. In particular, `k` proportional to sample count
preserves a neighborhood mass fraction and does not by itself establish
shrinking neighborhoods. The observed distance/support range must accompany
any later claim about locality, including any change to the fixed development
`k = 8` rule.

The remaining qualification surface also includes the outstanding core axis,
required gauge and architecture controls, rewire/shuffle/null controls,
loop-deformation and sampling-refinement companions, and per-branch detection
limits. A deterministic construction panel cannot replace those checks.

Partial, null, and insufficient outcomes may motivate a new development
version with a fresh holdout. They may not retune or promote a consumed
protocol. The [minimum 70M plan](P4_70M_MINIMUM_OBSERVATION_PLAN.md) still needs
its own prospective freeze, qualified sensitivity boundary, and explicit
model-access authorization. Phase-like regimes, transitions, learned
structure, native-manifold topology, and semantic or causal effects remain
unestablished.
