# P4 partial-pattern development prototype v0.1

Decision date: 2026-09-04. Status: implemented local synthetic development
slice; **not qualification**. P4 v0.3 remains `planned_not_frozen_not_run`.
The existing [measurement-chain design](P4_PHASE_CAPTURE_MEASUREMENT_CHAIN.md),
[M1 prototype](P4_GRAPH_SCALE_TRANSPORT_PROTOTYPE.md), consumed D7 outcomes,
SCI-S1 and Pythia-160M gates are unchanged.

The purpose is to make partial patterns observable through a runnable chain,
not to require all target phenomena to appear. More compute may later broaden
the search; Furnace was explicitly set aside for this slice. No remote
connection, transfer, model inspection/download, activation capture, or job
submission is needed or performed by this prototype.

## Executable scope

`scripts/prototype_p4_partial_patterns_v0_1.py` provides one small, model-free
chain:

1. Generate separate fit/evaluation probes in ambient three-dimensional
   representation space over an ordered, declared square domain.
2. Estimate a rank-two plane and reference chart using **fit probes only**.
3. Estimate both F2 (held-out mean response projected into that plane) and F4
   (held-out centered covariance's in-plane traceless tensor). Neither wins.
4. Bind each numeric field to its own amplitude, direction eligibility,
   reference, domain, probe fingerprints, and interpolation convention.
5. Seal both charge-blind low-amplitude component records before reading any
   winding result.
6. Read continuous relative holonomy and sampled winding on five independently
   predeclared boundaries, forward and reversed; retain each branch separately.

This uses existing F2/F4, Procrustes, exact-domain boundary binding, continuous
holonomy, and sampled-winding primitives. It does not change those library
APIs or their claim boundaries. The stable F4 projection explicitly constructs
diagonals `(a, -a)` before deriving spin two, avoiding subtraction-roundoff
artifacts for nearly isotropic tensors without changing the estimand.

The only graph in this first slice is a radius graph on the **declared input
coordinates**, with radius 1.01 times grid spacing. Exact boundary binding
requires every directed boundary segment (`max_span=1`); endpoint paths are
not substituted. The five fixed supports are outer, inner, two disjoint local
boxes, and an off-core box. They are selected without field outcomes. They
are test supports, not inferred cores or generic homology classes.

This is **not** the M1 law applied to a representation graph and is **not** the
three-field-graph by three-loop-graph panel. Those remain explicit next steps.
The diagnostic development states `eligible`, `insufficient`, and
`not_evaluated` are local prototype states, not official gate transitions.

## What the constructed cases distinguish

The generator supplies probe moments, not a final field to the measurement
entry point. All observations below are synthetic construction recovery only.

| Construction | F2/F4 field readout | Independent geometry |
| --- | --- | --- |
| F2-only / F4-only | active section winds +1; other section abstains | flat |
| coherent, smooth drift, pure gauge | sampled winding 0; no sampled depression | flat |
| amplitude depression | one sampled low-amplitude component, winding 0 | flat |
| curved fit plane, coherent section | no sampled depression, winding 0 | nonzero continuous holonomy |
| flat-plane defect fixture | one depression, sampled winding +1 | flat |
| opposite-sign dipole | local +1 and -1, enclosing loop 0; two depressions | flat |
| zero field | direction/winding insufficient; core unresolved | still evaluable |
| collapsed fit support | fields and geometry insufficient | insufficient |
| coarse sampling | loop readouts abstain under the declared density gate | insufficient |

For the noiseless 17-by-17 curved-plane fixture, outer-loop relative holonomy
is approximately 0.8054316832 rad. It is not an integer winding. Both field
readouts remain approximately zero winding. F4 reports the integer of its
**doubled director angle**, not a silently divided F2-like charge.

The dipole's inner box crosses its two zeros and therefore abstains even
though its outer and two smaller boundaries remain usable. This is retained,
not removed to make every loop agree. Reversing an eligible boundary changes
the signed winding/holonomy consistently. Local rotations and reflections
are removed with a fit-only fixed reference; F4 is transformed through its
tensor, never as an ordinary F2 vector.

## Meaning of a core candidate and a null

A core candidate here is only a connected set of sampled vertices below the
development amplitude cutoff, on the declared triangulation. It is not a
verified zero, continuous-field core, or topological defect. Global low
amplitude, unsupported fitting, or a low-amplitude region touching the domain
boundary produces `unresolved`, not a list of discoveries. A zero-candidate
record means no qualifying sampled depression, not proof that no between-
sample zero exists. Coarse-grid component records remain sampled diagnostics
even when the loop-resolution gate abstains.

Winding reliability concerns only the supplied boundary samples and their
declared principal-angle interpolation. Maximum domain spacing and branch
margin are development guards, **not** a band-limit certificate. Failed
amplitude/branch gates preserve unrounded totals, residuals and minimum
amplitude in a diagnostic member while leaving resolved value unavailable.
An eligible zero is a synthetic sampled null; insufficient is not absence.

`flat_defect` deliberately encodes the coordinate identity `(x,y)` into the
probe mean (and analogous spin-two channels). Identity already winds around
the origin: recovering it does not demonstrate learned structure. This is
an instrument control, not a discovery. Likewise, future origin-centering
`h(x)-h(0)` creates a zero by construction. The four distinct full,
pass-through, local-linear, and newly recomputed residual estimands are
specified in the [70M plan](P4_70M_MINIMUM_OBSERVATION_PLAN.md); their complete
comparison is not yet implemented. A test erases evaluation probes and checks
that newly derived zero fields abstain while fit-only geometry is retained;
that mutation is not a fitted residual experiment. Never mix full-field
amplitude with residual angle or subtract winding integers.

## Narrow descriptive sensitivity panel

The demo additionally crosses two amplitudes (0.25, 1), two probe-noise scales
(0, 0.15), two grid sides (9, 17), and three independent noise seeds for each
of the flat-defect and coherent constructions: 48 synthetic units, each read
with both F2 and F4. The 32 summary rows retain trial-level core, all loops,
geometry, reasons, and fingerprints. Only **outer-loop sampled winding** has
aggregate detection/false-positive rates in this slice; other branches do
not yet have calibrated sensitivity summaries.

Coverage and abstention use all three seed trials. Detection rates and Wilson
intervals condition on eligible trials and must be read with those
denominators. F2/F4 and the loop choices are repeated measurements, not extra
independent trials. At zero noise, seeds reproduce identical inputs: no
binomial interval is issued. At nonzero noise, three seeds provide only a
very small illustrative interval, not a validated error rate. The entire
surface is development data; it is not held-out qualification or evidence
for a model null. No threshold may transfer automatically to P4 or 160M.

## Run and inspect

With the checkout's core dependencies available in its own environment:

```bash
PYTHONPATH=src .venv/bin/python -B scripts/prototype_p4_partial_patterns_v0_1.py --self-test
PYTHONPATH=src .venv/bin/python -B scripts/prototype_p4_partial_patterns_v0_1.py --demo
.venv/bin/python -I -B -m pytest -q -p no:cacheprovider tests/test_p4_partial_patterns_prototype_v0_1.py
```

The first command gives a small self-test result; the demo emits the complete
finite JSON trace to stdout. Neither command persists a run artifact. The
report contains numerical payloads, same-field hashes, exact boundary
receipts, support masks, core seals, forward/reverse results, reasons and
development thresholds. These are reproducibility aids, not signed evidence
or externally attested observation provenance. Shared-memory fit/evaluation
arrays are rejected, but caller-declared batch-role identities cannot prove
the provenance of arbitrary external probes. The cross-fit claim is bounded
to the generator's separate arrays/noise streams and the fit-only function
boundary. No external model-intake interface is qualified.

## Next bounded steps

1. Review this first end-to-end synthetic slice and retain its partial/null
   outcomes as development evidence.
2. Implement separate full/pass-through/local-linear/residual comparisons and
   expand the source representation and noise controls.
3. Join the representation-graph 3-by-3 panel, preserving exact oriented
   boundary identity; prospectively cross density, warp, noise, and seeds.
   Restrict the locality claim to a measured finite range: `k ∝ n` is not a
   shrinking-neighborhood limit.
4. Freeze fresh qualification fixtures and a per-branch sensitivity surface
   before considering the [minimum 70M observation plan](P4_70M_MINIMUM_OBSERVATION_PLAN.md).

Phase-like regimes, checkpoint transitions, model-derived order parameters,
verified cores, causal/semantic effects, scientific/topology/publication
authority, and D7/D8 or SCI advancement remain absent. Partial findings may
motivate a new version with a new holdout, not retuning a consumed protocol.
