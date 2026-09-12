# P4 Furnace scaling preflight

Decision date: 2026-09-04. Status: **small cross-host execution completed;
strict parity failed; no large campaign launched**. Synthetic development
only; no model observation or scientific-claim promotion.

The user proposed using the now-available Furnace to explore substantially
larger synthetic computations. The Furnace skill required checking live
contention and isolating the work before execution. No existing workload,
managed model environment, system setting, or previous measurement kernel
was modified.

## Resources and the two meanings of scale

At the preflight check, the local Mac was an Apple M4 with 10 logical CPUs
and 24 GiB RAM. Furnace reported 24 logical CPUs, about 85 GiB available
out of 123 GiB RAM, and an RTX 5090 with 32,607 MiB VRAM and no active GPU
compute process. A separate CPU llama-server workload was present; its work
was left untouched. These are point-in-time resource observations.

The current graph-cross kernel is NumPy/CPU code. It does not automatically
use the GPU when copied to Furnace. Its fixed 17-by-17 measurement domain
and native memory limits remain unchanged. In particular, the native domain
constructs dense boundary matrices and checks their composition. Simply
raising a point-count cap would change the implementation's resource contract.

Two distinct next steps were presented to the user:

1. Increase **replication breadth**: repeat the unchanged three-by-three
   instrument across many independent seeds and separately located noise.
   This measures the incidence and coverage of residual patterns, not the
   behavior of a larger single domain. Seeds are paired across conditions;
   graph cells are not independent trials.
2. Increase **single-domain size**: implement a sparse/scalable domain and
   graph backend, preserving exact boundary semantics and tie handling, then
   establish small-case numerical equivalence before larger observations.
   This is a new implementation step, not an available launch switch.

Neither a GPU speedup nor the claim that the workload is impossible on a Mac
has been measured. No large-run configuration was silently selected while
that scale preference was outstanding.

## What was actually run

`scripts/prototype_p4_furnace_preflight_v0_1.py` generated four fixed,
model-free NPZ inputs on the Mac. The same bytes were transferred with the
Furnace skill's `spiral` transport and measured in a new isolated checkout:

- quadratic excess, default support;
- quadratic excess, support warp `0.75`;
- curved coherent control, probe noise `0.03`;
- collapsed plane-fit support.

Each side used the unchanged graph-cross kernel and retained its full report,
including all nine cells and every forward/reverse loop. Execution was
single-process with BLAS/OpenMP threads capped to one. The measurement
times were approximately `0.63–0.75` seconds per case on Mac and `0.63–0.91`
seconds on Furnace. These four timings include no throughput or GPU benchmark.

The Mac runtime was Python 3.13.13, NumPy 2.5.2, SciPy 1.18.1 on arm64.
Furnace used Python 3.14.4, NumPy 2.5.2, SciPy 1.18.0 on x86_64. It is a
heterogeneous-host check, not an isolation of one hardware difference.

Before numerical comparison, the helper checks the fixture and kernel hashes.
Discrete states, integers, identities and array shapes must match exactly;
floating values use the prospectively fixed `atol=rtol=1e-10`. Derived
SHA-256 strings are retained in each raw report but omitted from numerical
comparison: last-bit differences can propagate through those digests.

## Observed mismatch, preserved as failure

The strict comparator returned **fail**, with 228 differing paths. Every
difference was confined to the noisy curved-coherent case's **pass-through
F4 branch**, and specifically its ineligible-loop supplementary diagnostics
or additional failure-reason tags. The other three anchors had no comparison
differences. No threshold was widened and the failed report was not replaced
with a passing classification.

Local software validation passed 67 new fixture/parity-artifact tests and
the 69 existing graph-cross tests together: **136 passed**. The artifact
tests mock the expensive measurement call; the four cross-host executions
described above used the real unchanged kernel. Test success does not turn
the observed strict-parity failure into a pass.

The pass-through F4 amplitudes were at most about `4.81e-16` on Mac and
`4.58e-16` on Furnace, versus the existing eligibility floor `1e-6`. Across
all 90 loop-direction cells of that branch on each host, both implementations
returned `insufficient`, `value=null`, and an amplitude-below-floor reason.
The angle/winding diagnostics of these essentially zero vectors varied,
as did additional branch-cut or closure warnings.

This is consistent with floating-point perturbations of an isotropic tensor
producing arbitrary directions below the amplitude floor. It is **not** a
measured disagreement in an admitted winding value. All eligibility states
and admitted numeric values matched under the fixed comparison, after
excluding only the derived hashes as specified in advance. Nevertheless,
full diagnostic parity did not pass. A future narrower portability contract
must explicitly distinguish undefined-direction diagnostics from admitted
observables; that would be a new recorded decision, not a retroactive pass.

## Evidence locations and change boundary

Mac-side full fixtures, source snapshot, and both host outputs are retained
locally (ignored, not published) under:

`artifacts/p4-furnace-preflight-20260904/`

The strict comparison result is `parity.json` there. The exact fixture
manifest SHA-256 is
`ac25e4b06bb8c1ac0cac091b62199150b94595daa141bdda42518951d7486e0b`.

On **Furnace**, the isolated directory is:

`/home/ryospiralarchitect/scratch/spirallens-furnace-preflight-20260904-LVGbWi/`

Its `checkout` is a newly initialized isolated Git repository on branch
`SpiralReality/furnace-synthetic-preflight`, not an existing project checkout.
The original measurement helper snapshot is in the transferred
`source.tar.gz`. Subsequent local changes only strengthened fixture-list,
finite-value and artifact validation and added persistent comparison output;
the three numerical measurement scripts remained byte-identical.

The nested kernel's `furnace_accessed=false` describes its lack of a remote
launcher/call; the wrapper's `host_label=furnace` records where it actually
ran. This preflight **did execute on Furnace**, used no model and no GPU,
and did not launch a large campaign, change graph size, freeze P4, advance
D7/D8 or SCI, or establish a model-derived order parameter/core.
