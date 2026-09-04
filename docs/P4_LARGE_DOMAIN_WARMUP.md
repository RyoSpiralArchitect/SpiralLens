# P4 large-domain synthetic Furnace warmup

Decision date: 2026-09-04. Status: implementation validated on both hosts;
**27 of 27 prospectively bounded Furnace cases completed**. Synthetic development only,
claim ceiling Level 0. No model or GPU observation is part of this warmup.

The user chose to enlarge a single domain and its associated matrices before
moving to repeated small-model observations. This is not a search that stops
when a favorable pattern appears. The finite size/neighborhood/construction
panel below is fixed before its Furnace readouts, and missing or failed cells
remain in the result. Model choice, model access, and a real-model iteration
protocol are separate decisions that this synthetic run does not authorize
or qualify.

This is a separate successor to the
[graph-cross development prototype](P4_GRAPH_CROSS_PROTOTYPE.md). The
[earlier Furnace preflight](P4_FURNACE_SCALE_PREFLIGHT.md) remains a failed
strict cross-host comparison; its failed artifact is neither replaced nor
reclassified by the new implementation.

## 1. The fixed question and 27-case panel

The question is what becomes measurable, unstable, or computationally
unavailable when the same declared square is sampled more densely and the
field-neighborhood budget is changed. The three constructions are:

- `quadratic_excess`, no probe noise: a declared nonlinear-component anchor;
- `curved_coherent`, no probe noise: a coherent curved-plane control;
- `curved_coherent`, probe noise `0.03`: the same nominal coherent control
  with independently drawn noise in the plane-fit, baseline-fit, and
  evaluation probe roles.

The noise-bearing construction does **not** yet isolate the three noise
locations from one another. It must not answer which role caused a residual
pattern. Such a role-separated panel remains a subsequent experiment.

| Panel | Grid side | Vertex count `n` | kNN/shared-neighbor `k` | Cases |
| --- | --- | --- | --- | --- |
| Resolution/locality ladder | 17, 33, 65, 129, 257 | 289, 1,089, 4,225, 16,641, 66,049 | 8 | 5 sizes × 3 constructions = 15 |
| Neighborhood-budget cross | 65, 257 | 4,225, 66,049 | 16, 32 | 2 sizes × 2 budgets × 3 constructions = 12 |

Every case uses `seed=0`, `warp=0`, and no graph-coordinate noise. Reusing a
seed at different array sizes is **not coordinate-paired noise**: the stream
is consumed in different array layouts, and a shared physical coordinate
need not receive the same perturbation. No independent replication or
false-positive-rate estimate is supplied by these 27 cases.

At fixed `k`, increasing `n` changes both spatial resolution and physical
neighborhood radius. It also changes the number of boundary samples. This
is a coupled resolution/locality exploration, not an isolated sample-size
law. The `k=16/32` cases probe that coupling without selecting a winning
budget from the observed outcomes.

## 2. What remains the same, and what is new

The field graph and loop-support graph each have the same three families:
mutual-kNN, fixed-radius, and shared-neighbor. The core's declared square
triangulation remains a single fixed adjacency. Each case is therefore
**3 × 3 × 1**, not the full core-adjacency cross or completed M8/M9.

All nine graph cells are retained. A loop-support graph is asked whether
every edge of the exact same oriented boundary exists; it does not create
a replacement loop or choose a favorable path. Numerical readouts are
deliberately shared across supported columns within a field-estimation row.
The nine cells are not independent repeats.

The synthetic graph substrate remains
`(x + warp*x^3, y + warp*y^3, 0.2*x*y,
0.15*sin(pi*x)*sin(pi*y))`. Graph construction reads that substrate, not
F2/F4, residual amplitudes, core candidates, winding, or holonomy.

The radius graph uses `1.15` times the median fourth-nearest canonical
Euclidean distance regardless of `k`. Shared-neighbor adjacency connects
**any pair** sharing at least three members of their directed kNN sets;
it is not restricted to mutual neighbors. Increasing `k` therefore affects
the mutual and shared families but does not redefine the radius statistic.

Field estimation pools centered per-vertex plane-fit covariances over the
center and its graph neighbors. The original center must be supported,
there must be at least two neighbors, and all participating graph edges
must be no longer than `0.75` in declared two-dimensional domain units.
Graph receipts and pooled-covariance/locality records identify that reuse;
pooling does not create independent observations.

Three five-point affine baselines, at `(0,0)`, `(±0.5,0)`, and `(0,±0.5)`,
are sealed before evaluation moments. The full, pass-through, local-affine,
affine-residual, and pass-through-residual estimands remain separate, with
the origin-centered control also retained. F2 and doubled-angle F4 are
both measured. All 36 charge-blind low-amplitude component seals are made
before any winding or holonomy readout. A component remains a development
candidate, never a verified core.

### Sparse implementation boundary

The new backend is `scripts/p4_sparse_graph_backend_v0_1.py`; the new
measurement script is `scripts/prototype_p4_large_domain_v0_1.py`. Neither
raises the old exhaustive constructors' caps nor monkeypatches a sealed
kernel to bypass its limits.

The domain keeps the predecessor's vertex ordering, oriented triangular
faces, and five rectangular boundaries. Sparse integer boundary maps
explicitly satisfy `d1 @ d2 = 0`. Each declared loop is also checked against
the induced boundary of its selected faces. The core component calculation
uses the same triangulation's sparse adjacency.

For the three graph families, exact-query KD-tree searches supply bounded
candidate sets. Canonically ordered float64 Euclidean norms and row-ID tie
breaking make the final decisions. A conservative rounding/underflow
enclosure widens retrieval only; it does not widen the accepted radius or
alter the neighbor order. Full boundary ties are considered. Shared-neighbor
counts use bounded sparse products, not dense all-pairs set intersections.
These are new development receipts, not native qualified graph/domain
receipts or an approximate-neighbor claim.

The backend hard limits are 300,000 vertices, `k≤32`, 64,000,000 adjacency
nonzeros per graph, 64,000,000 total query candidates, 2,000,000 candidates
per query batch, 500,000,000 shared-neighbor scalar products in total, and
2,000,000 per product batch. A crossed limit raises a recorded resource
failure; it does not silently thin a graph, drop a case, or increase a cap.
The launch plan is narrower: its largest domain has 66,049 vertices.

### Explicit pass-through F4 representation change

The predecessor's floating projection of an isotropic tensor could leave
tiny, essentially zero traceless components with undefined directions.
Those below-floor supplemental diagnostics caused the earlier strict
cross-host comparison to fail, although admitted values agreed.

This successor declares isotropic pass-through F4 analytically as
`traceless(I2) = 0`. Its F4 amplitude is exactly zero and does not acquire a
direction from projection roundoff. This is a recorded algebraic
representation change in a new script, **not a relaxed comparator, a
retroactive pass, or a newly observed physical absence**. Real response
moments and noisy residuals are still evaluated numerically; their possible
patterns are not zeroed by this change.

## 3. Resource and execution contract

The Furnace run used one CPU worker with BLAS/OpenMP thread counts
set to one and lowered scheduling priority. It does not load a model,
allocate CUDA tensors, train, or use the GPU. The external Linux runner,
`scripts/run_p4_large_domain_warmup_v0_1.py`, imposes a 16 GiB address-space
limit, a 300-second CPU limit, and a 2 GiB limit per output file on each
child case. The child's wall timeout is the smaller of 300 seconds and
the remaining 1,800-second campaign budget.

The 8 GiB campaign artifact budget is a **pre-case admission check**, not
a filesystem quota or continuously enforced global disk ceiling. An admitted
case can take the total past that budget; subsequent cases then remain
`not_run`. The runner retains timeouts, nonzero exits, and cases not started
after the wall/disk budget. It does not delete failed evidence to make room.

On an isolated Furnace checkout with its intended environment available,
the runner entry point is:

```bash
PYTHONPATH=src python -B scripts/run_p4_large_domain_warmup_v0_1.py --output /absolute/new/campaign-directory
```

The output directory must be new. Before any case observation, `plan.json`
records all 27 specifications, unchanged development thresholds, resource
limits, and hashes of every Python source under `src` plus the six participating
scripts. The source lock is rechecked before every case. Any source drift
stops further launches and is recorded rather than silently mixed into one
campaign.

At `n=66,049`, a hypothetical dense float64 pairwise-distance matrix alone
would occupy about 32.50 GiB (`8*n*n` bytes), before the much larger dense
domain boundary maps or any work arrays. This explains why the former dense
implementation is not the scale path. It does **not** establish that the
new sparse implementation cannot fit on the 24 GiB Mac, nor demonstrate
GPU acceleration or a hardware speedup. Actual sparse peak memory and time
must be reported separately from those hypothetical dense allocations.

No existing Furnace workload or managed model environment is to be changed.
An isolated checkout/run directory holds the transferred source and results.
The source snapshot, fixed plan, runtime description, and artifact hashes
must identify what actually ran; a resource observation is only a snapshot
of the machine at that time.

## 4. Retained evidence and interpretation

Successful cases retain `arrays.npz` and `report.json`. The arrays include
coordinates, faces, graph substrate, all three probe roles, graph edges,
row-specific frames/support/pooled covariances, numerical field values and
amplitudes, and low-amplitude component indices and labels. The report
binds the array artifact by hash and records:

- domain/graph receipts and hypothetical dense sizes;
- each baseline, field, charge-blind component seal, and locality summary;
- five exact loops in both directions, all six estimands, both F2/F4, and
  independent geometry for every one of the nine cells;
- amplitude quantiles at `0`, `0.25`, `0.5`, `0.75`, and `1`, plus the number
  of vertices whose direction is above the fixed amplitude floor;
- an explicitly outer-forward-only aggregate, timing, and peak process RSS.

An insufficient branch has no admitted number. It is neither zero nor
evidence that a phenomenon is absent. Agreement among an eligible subset
is not complete agreement. Complete integer winding agreement also does
not erase continuous-geometry disagreement or make a coherent-control
residual into discovered structure.

Failures and unstarted cases stay in the denominator of the declared
campaign. Their available logs and partial artifacts must remain available.
The archive is development evidence, not signed external attestation,
scientific authority, or authority to freeze a real-model protocol.

## 5. Observed results

All **27 cases completed**, with zero failed, timed-out, or unstarted cases.
The campaign took 63.725 seconds. The manifest records 762,387,392 bytes of
campaign artifacts (about 727 MiB). Its largest reported peak RSS was
590,352,384 bytes (about 563 MiB), in the side-257, `k=32`, clean curved
case. The kernel re-samples that process peak after raw-array compression
and hash calculation, immediately before writing the final JSON report.
It therefore includes array serialization but is not an external
end-to-end OS peak measurement covering final JSON writing and interpreter
teardown. The largest single case wall time was 6.69 seconds.

The largest domain's boundary matrices had shapes `66,049 × 197,120` and
`197,120 × 131,072`. Together their sparse CSR storage occupied 7,352,332
bytes, versus hypothetical dense float64 sizes of 104,156,631,040 and
206,695,301,120 bytes respectively. These storage comparisons are not
performance comparisons between hosts.

The largest shared-neighbor graph had 2,926,610 undirected edges and
5,853,220 adjacency nonzeros. No declared resource guard tripped in this
finite panel. That is a successful bounded sparse execution, not a measured
machine-capacity limit or a claim that still-larger inputs cannot fail.

The campaign retains 27 cases and 243 graph cells, not 243 independent trials.
The following tables concern only the outer loop in its forward orientation;
the complete reports retain the other loops, reverse directions, estimands,
component candidates, and all nine cells. `0/9` means **no admitted winding
value**, not winding zero.

### Declared nonlinear anchor persists

Across all nine size/budget configurations of clean `quadratic_excess`,
affine-residual F2 and F4 each had `9/9` eligible cells with winding `+2`.
Their independent geometry had `9/9` eligible zero-holonomy readouts. The
largest domain therefore retained this deliberately injected synthetic
anchor; no additional phenomenon needs to be invented to explain it.

### Clean curved control: geometry agreement and residual loss separate

For the clean curved control at `k=8`, geometry was eligible in all nine
cells at every size. The maximum pairwise matrix Frobenius distance across
field-graph rows decreased through the ladder and crossed the fixed `0.02`
development agreement tolerance only at side 257:

| Side | `n` | Geometry matrix spread | Geometry agreement | Affine-residual F2 eligible | Affine-residual F4 eligible |
| --- | --- | --- | --- | --- | --- |
| 17 | 289 | 0.165814 | no | 9/9, all `0` | 9/9, all `0` |
| 33 | 1,089 | 0.084924 | no | 9/9, all `0` | 9/9, all `0` |
| 65 | 4,225 | 0.042901 | no | 6/9, all `0` | 9/9, all `0` |
| 129 | 16,641 | 0.021553 | no | 3/9, all `0` | 6/9, all `0` |
| 257 | 66,049 | 0.010801 | yes | 0/9 | 3/9, all `0` |

The residual losses here have an amplitude-floor reason. At side 257,
the F2 affine-residual amplitude medians across the three field rows are
approximately `3.78e-7`, `2.27e-7`, and `6.42e-7`, below the unchanged
`1e-6` directional floor. Those are whole-domain medians; the actual loop
admission also checks amplitudes at its own vertices. The recorded loop
reasons, not a median alone, establish the abstention.

Thus a coherent-control residual can shrink while independent geometry
becomes more consistent. A vanished residual direction is not evidence
that the nonzero geometric holonomy vanished. This is a concrete partial
pattern in the instrument, not a phase transition or qualified convergence
law.

### Noisy curved control: integer agreement does not survive refinement

| Side (`k=8`) | Affine-residual F2 | Affine-residual F4 | Geometry matrix spread |
| --- | --- | --- | --- |
| 17 | 6/9, all `+1` | 9/9, all `+1` | 0.164163 |
| 33 | 0/9 | 9/9, six `0` and three `+1` | 0.082332 |
| 65 | 0/9 | 0/9 | 0.043305 |
| 129 | 0/9 | 0/9 | 0.022264 |
| 257 | 0/9 | 0/9 | 0.008868 |

From side 65 onward, both residual branches are unavailable under the
branch-cut/undersampling ambiguity guard, despite non-negligible amplitudes.
For example, at side 257 the F2 residual medians are about `0.0151`, not
near the amplitude floor. Geometry still has nine eligible cells and falls
within the development agreement tolerance at side 257.

This is different from the clean control's low-amplitude abstention. More
vertices did not supply more probes per vertex or automatically improve
directional signal-to-noise. The observed transition from integer agreement
to disagreement to unavailable readout supplies a sensitivity warning; it
does not show a newly discovered defect or the physical disappearance of
one. Sizes are not noise-paired, and this finite panel does not isolate a
causal contribution from noise, locality, or boundary sample count.

### Increasing `k` is not automatically an improvement

At side 257, the clean curved control's geometry spread and maximum field-pool
distances were:

| `k` | Geometry matrix spread | Within `0.02` | Maximum domain distance: mutual / radius / shared |
| --- | --- | --- | --- |
| 8 | 0.010801 | yes | 0.015625 / 0.007813 / 0.024705 |
| 16 | 0.015520 | yes | 0.023438 / 0.007813 / 0.039836 |
| 32 | 0.030909 | no | 0.033146 / 0.007813 / 0.064424 |

All nine geometry cells were measurable in each row. The radius family
remained fixed, while the other two acquired wider, unequal physical
neighborhoods. `k=8` or `16` is not selected as a qualified winner; the
`k=32` disagreement is retained. Likewise, noisy residual F2/F4 remained
`0/9` at both side-65 and side-257 neighborhood-budget crosses.

The useful next experimental distinction is therefore **fixed physical
locality versus fixed neighbor count**, together with independently
located noise and per-vertex probe count. Those are prospective questions,
not retuned versions of this completed panel.

## 6. Validation and replay evidence

Implementation checks before the large-domain launch:

- Backend self-test: three small native comparisons pass exact graph edges,
  native edge hashes, coordinates, triangulation, and all five loop sequences
  (side 9 flat, side 17 flat, and side 17 with warp `0.75`).
- Additional developer checks pass exact graph comparisons for nine random
  cases (three seeds × `k=8/16/32`) and for tied, repeated, and tiny substrates.
- Sparse domains at sides 13, 21, 33, and 65 pass exact boundary-map and
  selected-face-induced-loop checks, including non-dyadic grid spacings.

The final focused suite passed **71 tests on Mac** in 7.54 seconds and
**71 tests on Furnace** in 6.85 seconds before the campaign was launched.
It compares seven small constructions with the unchanged predecessor,
including warp, coherent/noisy controls, identity/no-signal, and collapsed
support. It checks all nine cells, five loops in both directions, all
estimands, exact graph edges and component membership, unchanged support
states, numerical arrays, and admitted observables. The suite also checks
chronology, explicit budget failures, fixed campaign membership, finite
artifacts, and non-overwriting serialization.

This is a **new successor implementation-parity contract on each host**.
Numeric probes, frames, fields, and coefficients use absolute tolerance
`1e-10`; admitted readout dictionaries use `atol=rtol=1e-9`. It is not a
byte-identical or full-diagnostic cross-host test. Below-floor pass-through
F4 is treated according to the explicitly changed algebraic representation
above; the previous failed strict comparison remains failed.

On Furnace, the first isolated-Python test invocation failed before collection
because user-site `pytest` was not visible. Retrying with the available Python
environment and external test plugins disabled passed the 71 tests. No
environment package installation or managed-environment change was made.
That invocation failure is operational evidence, not a failed measurement
or evidence about the synthetic fields.

The broader local targeted regression passed **425 tests in 96.73 seconds**,
including the new 71 and relevant predecessor, graph/domain, referent,
measurement-design, and phantom checks. This is not a full-repository run,
and a test pass is not scientific qualification.

The transferred source archive SHA-256 is
`aee92aa87c6023a3b8a8822abee65407ed2888d3ccb0b3402ba84450093c1970`.
The archive initially contained the 59-test draft. The final 71-test file
was transferred separately before testing and launch, with SHA-256
`3796d579f4f86a26353b449563309bd8349c5ba223f896dca4a489a38f7db79a`.
The numerical kernel, backend, predecessor, and runner bytes did not change
between the archive and the launched campaign. The campaign's `plan.json`
holds the authoritative per-source launch lock.

The Furnace work is isolated at
`/home/ryospiralarchitect/scratch/spirallens-large-warmup-20260904-Jdaxu0/`,
with separate `checkout` and `campaign` directories. The checkout uses a
new branch, `SpiralReality/furnace-large-domain-warmup`. No previous project
checkout was replaced.

The compact reports and execution records were returned to the Mac under
`artifacts/p4-large-domain-warmup-20260904/campaign/`. They include the plan,
manifest, every report, stdout/stderr, and attempt/terminal records. The
individual raw `arrays.npz` files remain on Furnace in the corresponding
`campaign/case-NN/` directories; they were **not** copied into the compact
Mac report bundle. Both locations are ignored local evidence, not published
results or receiver-independent attestation.

Verified receipt hashes:

| Artifact | SHA-256 |
| --- | --- |
| Prospective `plan.json` | `453bdce588a390cebf7deab5ce2ff399a76757d4642224a9da096cf007009164` |
| Completed `manifest.json` | `bf1171cc9ad460b703d4756f3701cadff118a282da21ca0069d924d2b48b7cab` |
| Returned compact `report-bundle.tar.gz` | `40423d5976b4fbc7bdb85c5ab389168b8984af245f4e4b06950e0b636a375fed` |

Every completed case's report hash is bound in the manifest, and every
report binds its Furnace-resident raw array artifact. Source and returned
report hashes were checked after transfer; all 27 raw array files were
also verified on Furnace against their recorded hashes and byte lengths.
The raw files remain replayable
at their recorded Furnace location; a Mac reader with only the compact
bundle cannot independently re-evaluate their numeric arrays without a
separate authorized copy.

P4 v0.3, M1 qualification, D7/D8, SCI-S1/S2, and the Pythia-160M gate do not
advance through this synthetic warmup. Phase/transition and model-derived
order parameter/core remain unevaluated.
