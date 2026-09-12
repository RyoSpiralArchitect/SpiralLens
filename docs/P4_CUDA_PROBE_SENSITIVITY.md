# P4 paired probe sensitivity and thin CUDA adapter

Decision date: 2026-09-04. Status: **31 of 31 planned Furnace stages completed**,
including all 28 CPU reference cases. Synthetic development only, claim ceiling Level 0.
This is a separate successor to the
[large-domain Furnace warmup](P4_LARGE_DOMAIN_WARMUP.md). It asks whether more
observations at each fixed point, and separating where noise enters, can
explain the warmup's measurement failures. It also evaluates a narrow CUDA
implementation against the same CPU inputs and measurement gates.

The fixed CPU sensitivity panel and the CUDA validation are separate lanes.
Every panel case uses NumPy regardless of the measured CUDA performance or
parity. No CUDA auto-selection, model access, real-model iteration, or new
scientific authority is authorized by a favorable synthetic result.

## 1. Fixed questions and prospective panel

The previous size sweep used eight probes per point. Increasing the number
of points changed spatial resolution, locality, and boundary sampling, but
did not increase observations per point. Here the domain and graph budget
stay fixed within each probe-count comparison.

| Lane | Domain | Probe counts per point | Construction / noise role | Cases |
| --- | --- | --- | --- | --- |
| CPU role-separated sensitivity | side 65 and 257; 4,225 and 66,049 points | 8, 32, 128 | curved coherent; noise in all roles, plane only, baseline only, or evaluation only | 24 |
| CPU noiseless controls | side 65; 4,225 points | 8, 128 | quadratic excess and curved coherent | 4 |
| Full CPU/CUDA parity | side 65 and 257 | 128 | side 65 clean quadratic excess; side 257 curved coherent with all-role noise | 2 |
| Matched dense-operation benchmark | side 257; 66,049 points | 8, 32, 128 | curved coherent with all-role noise; one covariance and one moment call | 3 benchmark points |

The campaign has 31 child stages: two full parity stages, one three-point
benchmark stage, and 28 CPU reference cases. All use `k=8`, `warp=0`, and
`seed=0`. Noisy cases use probe-noise scale `0.03`. All cases and failure
denominators are recorded before launch; there is no stop-on-positive rule,
adaptive parameter selection, or promotion of a favorable subset.

The three roles are:

- **plane:** the observations used to fit and pool each local two-plane;
- **baseline:** the five-point observations used to estimate the affine
  reference independently of evaluation;
- **evaluation:** the observations whose F2/F4 moments are subsequently
  evaluated against the fixed references.

Role isolation is a synthetic intervention on these declared input arrays.
It is not a causal attribution about a neural model or a complete noise
model for one.

## 2. Paired input construction

`scripts/prototype_p4_probe_sensitivity_v0_1.py` defines a new `ProbeSpec`.
Its finite ladders allow sides 17/65/257, probe counts 8/32/128, and neighbor
budgets 8/16/32; the actual campaign is the narrower panel above. All other
pattern, seed, warp, and noise checks are inherited from the bounded
large-domain specification. `noise_role=none` requires zero noise.

Each role's clean eight-probe cube is repeated 1, 4, or 16 times. This
preserves the intended noiseless probe distribution: it does not introduce
new probe directions. The repeated arrays are exact copies; floating-point
reductions at different widths can still differ by roundoff.

The new noise protocol is
`role-seedsequence-vertex-major-max128-first-P.v0.1`. Three independent
streams are spawned from the seed, one for each role. Each stream has the
conceptual shape `(vertex_count,128,3)`, and a P-probe case uses the first P
observations at each vertex. Generation is chunked by 4,096 vertices to
bound temporary memory while preserving the exact stream ordering.

Consequently, for the same fixed domain and seed:

- the P8 arrays are exact prefixes of P32 and P128 at every vertex;
- enabling one noise role uses exactly that role's realization from the
  all-role case, while other roles retain their clean arrays;
- baseline and evaluation streams remain distinct;
- CPU and CUDA receive exactly the same host float64 input bytes.

This is a **new noise protocol**, including at P8. Its noisy P8 inputs are
not the prior warmup's RNG-byte replay. Reusing the seed across different
domain sizes still does not pair the same physical coordinate's noise.
The panel contains no independent seed replicates or calibrated uncertainty
estimate. Repeated cube directions and reused graph cells are not
independent replications.

For smaller P, generating the maximum-width stream remains deliberate
pairing overhead. End-to-end timings include this generation work; a
dense-operation speed ratio excludes it and must be labeled accordingly.

## 3. What the CUDA adapter changes

`scripts/p4_dense_moment_adapter_v0_1.py` provides
`DenseMomentAdapter(backend="numpy"|"cuda", batch_vertices=8192)`. It accepts
canonical finite float64 probe/frame arrays and returns host float64 arrays.
CUDA is optional and explicit. NumPy does not import PyTorch; requesting
CUDA without a usable PyTorch/CUDA runtime fails rather than falling back.

Only two dense operations change backend:

1. centered per-vertex three-dimensional probe covariance;
2. projected F2 means and F4 traceless two-dimensional covariance moments.

Graph construction, sparse pooling, eigendecomposition, frame support,
five-point affine fitting, field/core seals, connected components, loop
coverage, winding admission, and geometric transport remain on the CPU.
Neither graph identities nor failed measurement gates are repaired by CUDA.

Each adapter call uses bounded vertex batches. CUDA timing includes host
validation, host-to-device transfer, reductions, device-to-host transfer,
and synchronization. The receipt records calls, batches, elapsed times,
device/runtime versions, dtype, and process PyTorch allocator high-water
memory. That memory figure is not total device use, a per-stage incremental
peak, or a hardware-capacity measurement.

The explicit synchronization waits for device-stream kernel completion;
this is why the reported timing is not merely asynchronous launch latency.
See the [official `torch.cuda.synchronize` API documentation](https://docs.pytorch.org/docs/2.14/generated/torch.cuda.synchronize.html).
That reference explains the API only: the actual measured runtime was
PyTorch `2.13.0+cu132`, not the documentation site's 2.14 version.

### Isolated predecessor orchestration

The successor creates a fresh per-call function namespace for the frozen
large-domain `prepare_row` and `measure_case` bytecode. Only `make_probes`,
`_covariance`, and `moments` are replaced; the cloned `prepare_row` is then
bound inside the cloned measurement's namespace. The predecessor module's
globals and source bytes are not modified. Test instrumentation can inspect
this isolated namespace without changing predecessor behavior.

All three affine baselines remain sealed before evaluation moments. All 36
charge-blind core seals remain fixed before loop readouts. The same five
loops, both directions, all nine field-graph × loop-graph cells, and the
single core adjacency remain. This is still **3 × 3 × 1**, not an independent
nine-replicate experiment or a full core-adjacency cross.

The predecessor's analytic isotropic pass-through F4 remains exact zero.
No measured residual or noisy tensor is clamped to zero. Model-derived order
parameters, verified cores, phase, and transition remain unestablished.

## 4. Prospective parity and timing interpretation

The new parity contract is fixed before the Furnace observations. It asks
for exact input bytes, array shapes/dtypes, graph/cell/loop identities,
discrete support/core membership, baseline admission and stencil identity,
readout admission states, reasons, and coverage. Baseline coefficients,
numerical arrays, and every admitted readout use absolute and relative
tolerances of `1e-9`.

Source/provenance hashes are not required to be equal across numerically
equivalent implementations. Below-admission supplemental directional
diagnostics are excluded prospectively: a below-floor field has no admitted
direction to compare. Its actual arrays, support/core outcomes, admission
state, reason, and coverage remain checked. An ineligible value is not
turned into zero or silently dropped from a denominator.

This contract does not reclassify the
[earlier strict Furnace preflight failure](P4_FURNACE_SCALE_PREFLIGHT.md).
That stricter failed artifact is retained. The current contract and
successor input protocol are independently identified and must not be
described as an unchanged rerun of it.

The dense benchmark fixes a CPU-derived frame array and reuses it for both
backends. Each point has one warmup per backend followed by three timed
repetitions, with order NumPy/CUDA, CUDA/NumPy, NumPy/CUDA. Its median ratio
covers one covariance plus one moment call, including transfers and
synchronization. It excludes graph construction, core/loop measurement,
source/array hashes, and serialization; it is not an end-to-end speedup.
All warmup and timed outputs are checked against the fixed NumPy reference;
parity is not inferred only from the final repetition.

The full parity stages additionally record one cold call per backend in
the order NumPy then CUDA. These times include initialization, canonical
input generation, graphs, measurements, and hashes, but not output-array
serialization. They are single observations, not warmed repeated
whole-pipeline performance estimates.

## 5. Resource and artifact contract

`scripts/run_p4_probe_sensitivity_v0_1.py` locks participating source hashes
and writes the full plan before any child. It runs one child at a time,
with one BLAS/OpenMP thread and lowered scheduling priority. Source hashes
are checked before each new stage. Environment flags keep model Hub access
offline; the experiment itself does not request model or dataset access.

The limits are 180 seconds per child, 1,200 seconds for the campaign, and
2 GiB per output file. The 8 GiB campaign disk check is a **pre-stage
admission check**, not a hard global filesystem quota. A started stage may
increase the total beyond that threshold before the next check. CUDA
virtual address space is not capped with `RLIMIT_AS`, because context
initialization reserves a large virtual range; bounded batch size does not
constitute a hard bound on total host or device memory.

Attempt and terminal records, standard output/error, stage results, plan,
and manifest are retained. A failed CUDA stage does not prevent the fixed
CPU reference panel from being attempted while resource budgets permit.
Failures, timeouts, and unrun stages remain in the planned denominator.

Each CPU sensitivity case serializes raw probes, graph edges, frames,
support, pooled covariances, all field arrays, amplitudes, core membership,
and loop reports once into a new directory. Existing outputs are not
overwritten. Compressed-array and report hashes bind the stored evidence.
Full parity stages retain both backend reports and comparison outcomes;
the dense benchmark retains point receipts and timings.

The run uses the isolated Furnace checkout
`/home/ryospiralarchitect/scratch/spirallens-cuda-probes-20260904-zNRa9Z/checkout`
on branch `SpiralReality/furnace-cuda-probe-sensitivity`. Its available
runtime is system Python 3.14, NumPy 2.5.2, SciPy 1.18.0, and PyTorch
`2.13.0+cu132` with an NVIDIA GeForce RTX 5090. No environment installation
or model-server reconfiguration is part of this run.

## 6. Observations and validation

### CUDA parity and scoped timing

Both prospectively declared full measurement pairs passed: exact discrete
admission/coverage/reason and support/core membership, and `1e-9` numerical
array/admitted-value tolerance. Maximum absolute array differences were
`6.8833827526759706e-15` for clean side-65 quadratic excess and
`2.942091015256665e-15` for noisy side-257 curved coherent. This is tolerance
parity on these two full cases, not bitwise equality of numeric results or
an unrestricted CUDA qualification.

All warmup and timed dense-operation outputs also passed the declared
numeric comparison. At 66,049 vertices, the warmed three-repeat medians
were:

| Probes per point | NumPy seconds | CUDA seconds | NumPy / CUDA |
| --- | ---: | ---: | ---: |
| 8 | 0.048089 | 0.009490 | 5.07× |
| 32 | 0.175987 | 0.021556 | 8.16× |
| 128 | 0.678252 | 0.072939 | 9.30× |

These are measured speed ratios for **one covariance plus one moment call**,
including validation/transfers/synchronization. CPU work outside those two
operations is excluded.

The full, single cold calls without array serialization tell a different
story:

| Full measurement case, P128 | NumPy seconds | CUDA seconds |
| --- | ---: | ---: |
| Side 65, clean quadratic excess | 0.725213 | 1.379412 |
| Side 257, noisy curved coherent | 10.135925 | 8.938473 |

The small case was slower with CUDA; the large case was faster in this
single ordered observation. CUDA/PyTorch initialization is included, and
graphs, hashes, and the remaining measurement chain still run on CPU.
Neither result establishes a warmed repeated whole-pipeline speedup.

### All 28 CPU sensitivity observations

All planned stages completed in **180.228256 seconds**, with no failed,
timed-out, or unrun stage. The tables below summarize the outer-forward
**affine-residual** readout across the nine graph cells. Each entry gives
`F2 winding [eligible/9] / F4 winding [eligible/9]`. A dash is unavailable,
not zero. Eligible subsets must not be substituted for the full denominator.
All five loops, both directions, other estimands, and core records remain
in the individual reports.

Side 65: 4,225 vertices, curved coherent, noise scale 0.03.

| Noise role | P8: F2 / F4 | P32: F2 / F4 | P128: F2 / F4 |
| --- | --- | --- | --- |
| All | −1 [9/9] / — [0/9] | — [0/9] / — [0/9] | — [0/9] / — [0/9] |
| Plane only | — [0/9] / — [0/9] | — [0/9] / 0 [3/9] | 0 [3/9] / 0 [3/9] |
| Baseline only | −1 [9/9] / +1 [9/9] | −1 [9/9] / 0 [9/9] | −1 [6/9] / 0 [9/9] |
| Evaluation only | — [0/9] / — [0/9] | — [0/9] / — [0/9] | — [0/9] / — [0/9] |

Side 257: 66,049 vertices, curved coherent, noise scale 0.03.

| Noise role | P8: F2 / F4 | P32: F2 / F4 | P128: F2 / F4 |
| --- | --- | --- | --- |
| All | — [0/9] / — [0/9] | — [0/9] / — [0/9] | — [0/9] / — [0/9] |
| Plane only | — [0/9] / — [0/9] | — [0/9] / — [0/9] | — [0/9] / — [0/9] |
| Baseline only | +1 [9/9] / −1 [9/9] | 0 [9/9] / +1 [6/9] | +1 [9/9] / −1 [9/9] |
| Evaluation only | — [0/9] / — [0/9] | — [0/9] / — [0/9] | — [0/9] / — [0/9] |

The four noiseless controls use side 65:

| Construction | P8: F2 / F4 | P128: F2 / F4 |
| --- | --- | --- |
| Quadratic excess | +2 [9/9] / +2 [9/9] | +2 [9/9] / +2 [9/9] |
| Curved coherent | 0 [6/9] / 0 [9/9] | 0 [6/9] / 0 [9/9] |

The missing noiseless-curved F2 cells fail the amplitude floor, not the
branch-angle condition. Repeating the clean cube does not recover those
three cells. The declared nonlinear anchor remains visible in all nine
cells for both F2 and F4 at both tested probe widths.

### What the role split establishes, and what it does not

**Reference noise can produce an admitted nonzero residual winding with
clean evaluation observations.** In the baseline-only lane, the plane and
evaluation arrays are clean; only the independently fitted affine reference
changes. For example, side 257 at P128 reports F2 `+1` and F4 `−1` in all
nine cells, although the nominal curved construction has no injected
quadratic-excess pattern. This is a concrete synthetic subtraction/reference
sensitivity, not an observed model phase or a verified core. Agreement
between graph cells does not remove that reference dependence.

Increasing P is not a monotone route to a desired answer. The baseline-only
values and eligibility change across the nested realizations, and all-role
and evaluation-only cases still have no admitted F2/F4 affine-residual
outer-forward readout at P128 for either domain size. This finite panel
does not show that recovery is impossible; it shows that the tested increase
from 8 to 128 observations did not recover those readouts.

For those all-role and evaluation-only failures, the reason is
`branch_cut_or_undersampling_ambiguity`. The smaller plane-only domain gains
partial eligibility as P increases, but never reaches a full nine-cell
residual result. Its unavailable cells also have branch ambiguity. The
larger plane-only domain additionally reaches the amplitude floor:

- side 257, P32: F2 has combined floor + branch failure in 9/9 cells;
  F4 has that combined failure in 3/9 and branch-only failure in 6/9;
- side 257, P128: F2 has combined failure in 6/9 and branch-only failure
  in 3/9; F4 has combined failure in 3/9 and branch-only failure in 6/9.

The partial baseline-only failures, side-65 P128 F2 and side-257 P32 F4,
are branch ambiguity in the remaining three cells, not amplitude-floor
failures. Failed directional readouts are retained; no absent-field or
zero-winding conclusion is substituted for them.

The geometry lane remains distinct from this winding behavior. For all 24
noisy curved cases it has 9/9 eligible cells. Side-65 graph-pair Frobenius
spreads range from approximately `0.03975` to `0.04358`, above the fixed
`0.02` agreement threshold. Side-257 spreads range from `0.01042` to
`0.01134`, below that threshold. Geometric agreement can therefore coexist
with unavailable or reference-sensitive residual winding; neither alone
establishes topology, semantics, phase, or transition.

The new side-65 P8 all-role F2 result, `−1` in nine cells, is not a correction
of the earlier warmup's P8 result: its noise bytes belong to the newly
declared maximum-width stream. Comparisons within the present P ladder are
paired; cross-protocol result differences are not a probe-count effect.

### Resource observations and retained evidence

The largest reported CPU-reference peak RSS is `1,259,581,440` bytes
(1,201.23 MiB), in side-257 P128 evaluation-only case 23. The full paired
comparison child reaches `2,856,857,600` bytes (2,724.51 MiB): it retains
both CPU and CUDA result arrays in the same process, so this is not a
single-backend incremental memory measurement. The largest adapter-reported
PyTorch GPU allocation high-water is `118,292,480` bytes (112.8125 MiB).
No configured time or file limit was reached; these runs did not locate
Furnace's capacity limit or establish that a Mac could not run the CPU lane.

The 28 raw compressed-array artifacts total `2,543,917,943` bytes; the
campaign directory was measured at `2,573,386,394` bytes (approximately
2.397 GiB). All raw NPZ sizes and SHA256 receipts were checked on Furnace.
Raw arrays remain there, under
`/home/ryospiralarchitect/scratch/spirallens-cuda-probes-20260904-zNRa9Z/campaign`.

The compact local report collection is
`artifacts/p4-cuda-probe-sensitivity-20260904/campaign/`. Verification covered
195 source-lock entries, 31 stage results, all 28 CPU measurement reports,
and four full-parity backend reports. The source archive is preserved
separately from the compact report bundle.

| Artifact | SHA256 |
| --- | --- |
| Source archive | `6bf924bf593144f157f94f85f725b6bb1db2478e1341db3743937dc0b7567bec` |
| Prospective plan | `5a8a62a8a7aa2e6a979a3b202905e7c239262cb344ab65766b63301f5d9a49a7` |
| Campaign manifest | `0098b1db6be5aa362d0965ec7d955e4766d95a8ffb89d2f70c6b7a4a1dccce86` |
| Compact report bundle | `6d6b8d7af2af050ae8a56820379056a47f2e979b3898a1481ff630a64259b4d8` |
| Dense adapter source | `9b350bd7d99deb2f99ef08d4e41fad90e1450b07d53a487545b63d97743de835` |
| Probe-sensitivity source | `a3c08d50d650cbdd846af7696fa9dee4405909d0757014498f37445dbdfa47ae` |
| Campaign runner source | `5e9fdc4ae693020e22d8a398a51c93d034acd2299e9189274b1ffb4b6ab6f42f` |
| Final focused test source | `04aac23c8be29472265d2a2979439df5c95926f971854b576d2ec4b1eefe904b` |

### Validation chronology

Before the campaign, the then-current focused tests passed on the actual
GPU host: **78 passed, 1 skipped**, in 2.93 seconds. Additional runner
mutation/validation tests were completed and transferred separately after
launch; they did not change the frozen numerical source or prospective
panel. After the campaign, the final focused test file passed on Furnace:
**90 passed, 1 skipped**, in 3.19 seconds. The skip is the unavailable-CUDA
failure-path check on a host where CUDA is available.

The targeted local regression finished with **508 passed, 8 CUDA-dependent
tests skipped**, in 97.45 seconds. This is not a full-repository or
clean-wheel test claim. The tests cover nested role-specific input bytes,
unchanged predecessor behavior and chronology, finite/bounded specifications,
batched numeric parity, explicit unavailable-CUDA failure, all graph cells,
and negative mutations of the runner's comparison contract.

The next scientific design decision should address reference-noise
stability explicitly, alongside evaluation-noise recovery, before treating
a residual winding as a target signal. Increasing a favorable subset's
compute budget or selecting a CUDA path does not settle that question.

## 7. Reproduction entry points

The default backend is NumPy. The explicit one-case interface is:

```bash
PYTHONPATH=src python scripts/prototype_p4_probe_sensitivity_v0_1.py \
  --backend numpy --side 65 --probe-count 32 \
  --noise-role evaluation --noise 0.03 --output /new/case-directory
```

Selecting `--backend cuda` requires a CUDA-enabled PyTorch runtime. The
fixed bounded campaign requires Linux and a new output directory:

```bash
PYTHONPATH=src python scripts/run_p4_probe_sensitivity_v0_1.py \
  --output /new/campaign-directory
```

Neither command downloads or runs a neural model. A favorable adapter
comparison only supports the explicitly tested synthetic operation and
measurement cases; broader CUDA use remains a separate validation decision.
