# P4 estimand-comparison development prototype v0.1

Decision date: 2026-09-04. Status: implemented local synthetic development
slice; **not qualification**. The nine noiseless development constructions
and six self-test checks have run; focused-test completion is recorded below.

This is the next bounded step after the
[partial-pattern prototype](P4_PARTIAL_PATTERN_PROTOTYPE.md). It implements the
baseline-accounting question in section 5 of the
[minimum 70M observation plan](P4_70M_MINIMUM_OBSERVATION_PLAN.md): which
observed pattern is already supplied by the declared coordinate map or a
locally fitted affine response, and which pattern remains under an explicit
residual construction? It does not answer whether that remainder is learned,
semantic, causal, or a property of a native model manifold.

The predecessor's implementation and report identities remain unchanged. This
successor does not perform a representation-graph three-by-three comparison,
new reception qualification, model observation, remote connection, transfer,
download, or Furnace job. P4 v0.3 remains `planned_not_frozen_not_run`; consumed
D7 outcomes, D8, SCI-S1/S2, and Pythia-160M gates do not advance.

## 1. Why this comparison is necessary

The input-coordinate map `(x, y)` already winds around the origin on an input
circle. Likewise, origin-centering a response by subtracting its value at the
origin forces a zero there. Recovering either construction can validate a
measurement path, but cannot establish a discovered core or learned nonlinear
structure.

The experiment therefore retains five distinct estimands and a separate
origin-centering control rather than correcting a reported integer or
attaching one field's amplitude to another field's direction:

| Estimand | Construction | Interpretation boundary |
| --- | --- | --- |
| Full field | Estimate both response sections from evaluation probes in the separately fitted plane | Includes structure imposed by the declared input and response construction |
| Pass-through baseline | Use ambient mean `(x, y, 0)` and isotropic covariance `I3`, then estimate both sections in the frozen plane | The input comparator has an F2 response but zero F4 anisotropy; it is not an F4 identity field |
| Local-affine baseline | Fit an intercept and first-order coordinate terms from baseline-fit probes on a fixed local stencil | A fit-only approximation; evaluations outside the stencil's convex hull are explicitly extrapolations |
| Affine residual | Subtract the fitted affine section at the declared section/tensor stage and recompute the complete field readout | An operational remainder, not a semantic or causal subtraction |
| Pass-through residual | Subtract the specified pass-through section at the same declared stage and recompute the complete field readout | A mismatched comparator can create a pattern, so residual winding alone is not evidence of structure beyond the input |
| Origin-centering control | Subtract the evaluation section at the declared origin | Explicitly uses the evaluation origin; not a fit-only baseline and not independent of the full evaluation field |

The affine model includes an intercept. Calling it a first-order response does
not imply that its value at the origin is zero, that an origin response was
subtracted, or that it is an exact derivative. It is a finite-stencil fit with
its design and rank conditions retained.

The pass-through field and the affine fit are separate comparators. Neither
is selected after observing a favorable residual. No best baseline, field,
loop, or direction is chosen by its winding result.

The origin-centering control deliberately exposes the forced-zero trap. Its
zero at the origin is imposed by its definition, not discovered by a fit-only
procedure. It must remain named separately from the five estimands and must
retain its evaluation-origin dependency.

If the origin's fitted plane or reference is unsupported, that dependency
makes both entire origin-centered fields unavailable and their readouts
insufficient, even on an otherwise supported outer boundary. No origin value
is fabricated from the unsupported frame. Independently eligible full,
pass-through, and geometry branches remain available. A failed non-origin
affine-stencil row instead blocks only the affine baseline and its residual;
it does not erase a supported origin-centering control.

## 2. Three input roles, with fit-only boundaries

The prototype separates three representation-probe roles:

1. **Plane-fit:** determine the rank-two representation plane, reference chart,
   and independent geometry. No response from the later roles may choose the
   plane or its reference.
2. **Baseline-fit:** estimate the baseline response sections in that frozen
   plane, then fit the local-affine maps using only the declared stencil.
3. **Evaluation:** estimate the full response sections and evaluate the
   already-defined baseline and residual readouts. Evaluation responses never
   fit the affine coefficients or choose their stencil.

The fixture generator uses separate probe batches and noise streams. Batch
identities, numeric fingerprints, stencil membership, and fit parameters are
retained for replay. Input validation and disjoint storage guard the local
implementation boundary; they do not attest the independent provenance of
arbitrary external arrays. This is not a qualified external-model intake.

The baseline stencil is fixed from declared domain coordinates before reading
baseline-fit or evaluation responses. It contains the five rows
`(0, 0), (+0.5, 0), (-0.5, 0), (0, +0.5), (0, -0.5)`. The affine design is
`[1, x, y]`; its columns, coordinate units, and rank rule belong to the
specification. Ordinary least squares is applied to section values restored
to the pinned, fit-only canonical reference, not raw components in
vertex-dependent gauges.
A fit must not expand the stencil to rescue a low-rank or unfavorable result.
Rank failure produces an unavailable fitted baseline and residual, while an
otherwise evaluable full or pass-through field retains its own result.

A fitted affine expression can be evaluated across the whole declared domain.
Its interpolation region is the stencil's convex hull:
`abs(x) + abs(y) <= 0.5`. Rows outside that hull retain an extrapolation label,
and loops retain their outside-hull support information, even if the
synthetic construction happens to be exactly affine there. An unsampled row
inside the hull is not automatically an extrapolation merely because it is
not a stencil vertex.
Such numerical evaluation is not evidence that a real response is locally
linear at the extrapolated points. The finite stencil is not a differentiability
or Taylor-error certificate.

## 3. Subtraction is defined separately for F2 and F4

F2 and F4 remain co-primary. They share the declared input coordinates and the
fit-only reference construction, but have different transformation laws and
independently bound numeric payloads.

For F2, let `z_full(x)` be the estimated local two-component response section
and `z_baseline(x)` the selected-by-specification affine or pass-through vector
section. Each residual is
`z_residual(x) = z_full(x) - z_baseline(x)` in the same frozen reference. Its
amplitude, direction-defined mask, sampled low-amplitude components, and loop
readouts are recomputed from `z_residual`, not copied from `z_full`.

For F4, independently estimate the response covariance and form the symmetric
in-plane traceless tensor `Q` before subtraction. Each residual is
`Q_residual(x) = Q_full(x) - Q_baseline(x)` in the same frozen reference.
Its spin-two pair is reconstructed from that residual tensor under
the predecessor's doubled-angle convention, with a newly computed amplitude,
direction-defined mask, component seal, and loop readouts. The operation is
neither subtraction of ordinary F2 vectors nor the covariance of residual
activations. It also does not subtract raw covariance matrices and claim that
the result is itself a covariance. A traceless residual tensor need not be
positive semidefinite. The pass-through comparator's isotropic covariance
produces zero F4; the F2 coordinate response must not be reused as its F4
section.

Local rotations and reflections must act consistently on the frame, F2
vector, and F4 tensor. Gauge alignment or comparison must not use evaluation
outcomes. A residual direction paired with full-field amplitude would define
no field measured by this protocol and must not appear in the output.

Every estimand binds its own section values, same-object amplitudes,
direction mask, field specification, probe/fit references, domain, and
interpolation convention. The connection remains a separate, shared,
full-plane-fit-derived object. It is not re-estimated from residual directions,
does not describe a newly estimated residual representation geometry, and its
continuous holonomy is not a correction to defect winding.

## 4. Read out complete branches, including zero residuals

Each of the five estimands and the origin-centering control enters the
same-field amplitude/core/loop path independently: twelve field records per
case with both F2 and F4 retained. Every sampled low-amplitude component record
is sealed before any winding result is read. All predeclared forward/reverse
loop outcomes are retained for both sections.
Their development states do not become official gate transitions.

In particular, an identically zero residual is direction-ineligible. Its
core record is unresolved, not a collection of discovered cores; its defect
readout is insufficient, not an eligible zero winding. The separate geometry
branch may still be evaluable from the fit-only plane and supported boundary.

An eligible zero winding is a sampled synthetic null under the declared
amplitude and branch conditions. It is different from an insufficient field,
an unavailable affine fit, or a loop that fails sampling support. A low-amplitude
component is only a sampled component under the development cutoff, not a
verified continuous zero or topological defect.

Winding is recomputed on each residual field's eligible boundary. The report
must not calculate `winding(full) - winding(baseline)` and call the result
residual winding. Winding is nonlinear and depends on the actual residual
field and its boundary eligibility. Continuous holonomy and integer defect
winding likewise remain different quantities.

## 5. Observed construction recovery and development checks

The fixed construction panel is `input_identity`, `affine_offset`,
`quadratic_excess`, `f2_nonlinear_only`, `f4_nonlinear_only`,
`curved_coherent`, `no_signal`, `collapsed_support`, and `undersampled`.

The `no_signal` construction is especially important: subtracting the
nonzero pass-through comparator from a zero full F2 field produces the
negative coordinate map, which itself winds around the origin. Baseline
subtraction can therefore introduce a pattern. This is an explicit mismatch
control, not evidence that a signal was hidden in the zero full field.

The noiseless demo produces the following **outer-loop sampled** results.
All numbers are construction recovery, not observations of model structure.
F4 numbers retain the doubled-angle convention. `Insufficient` is not an
eligible zero winding.

| Construction | Full and fitted-affine fields | Freshly measured contrasts or control |
| --- | --- | --- |
| `input_identity` | F2 winding `+1`; F4 insufficient; the pass-through comparator agrees | Both residual definitions have numerically zero amplitude, unresolved cores, and insufficient winding |
| `affine_offset` | F2 and F4 winding `0` | Affine residuals abstain; the evaluation-origin-centered control has winding `+1` and one imposed sampled origin component in both sections |
| `quadratic_excess` | F2 and F4 winding `+1` | Affine residuals wind `+2` in both sections; pass-through residual winds `+2` in F2 but `+1` in F4 because the pass-through F4 tensor is zero |
| `f2_nonlinear_only` | Both fields remain reported; neither is selected as a winner | Affine residual F2 winds `+2`; affine residual F4 is insufficient |
| `f4_nonlinear_only` | Both fields remain reported; neither is selected as a winner | Affine residual F2 is insufficient; affine residual F4 winds `+2` |
| `curved_coherent` | F2 and F4 winding `0` | Affine residuals abstain while independent geometry remains eligible |
| `no_signal` | Both full fields are insufficient | Pass-through residual F2 winds `+1`; F4 remains insufficient: this is the declared mismatched-subtraction artifact |
| `collapsed_support` | Fields and independent geometry are insufficient | The affine fit and residual values are unavailable, not synthetic zero arrays |
| `undersampled` | Numeric fields remain recorded | All loop readouts abstain under the predecessor's unchanged domain-spacing gate |

For `affine_offset`, the synthetic section is `2 + z`; the origin-centered
control is `z`. For `quadratic_excess`, the synthetic section is
`z + 0.25 z²`; the fixed symmetric affine stencil removes the affine part,
leaving a quadratic residual. Here `z = x + iy` is shorthand for the
two real F2 components or the F4 tensor's spin-two coordinates, not a claim
that F2 and F4 are the same kind of object. In particular, `1 - 1 = 0` would
give the wrong residual winding for the quadratic example: its actual
recomputed residual winds `+2`.

The local check coverage includes:

- Distinguishing coordinate-imposed full/pass-through winding from a
  recomputed, direction-ineligible zero residual.
- Preserving an affine intercept, while exposing the origin-centering
  control's imposed origin component.
- Measuring a nontrivial synthetic remainder without copying a full-field
  amplitude, direction, component seal, or winding integer into the residual.
- Preventing evaluation leakage: changing evaluation probes leaves fitted
  planes, affine coefficients, and independent geometry unchanged while
  permitting full/residual readouts to change.
- Applying F2 and F4 gauge/reference rules, including reflections and F4's
  tensor transformation law.
- Keeping extrapolation outside the stencil's convex hull explicit, rather
  than presenting it as local fit support.

These are development construction-recovery and boundary checks. They do not
estimate a model false-positive rate, establish residual-field identifiability,
qualify an M9 sensitivity surface, or select a future 70M threshold.

## 6. Run and inspect

With the checkout's core dependencies available in its own environment:

```bash
PYTHONPATH=src .venv/bin/python -B scripts/prototype_p4_estimand_comparison_v0_1.py --self-test
PYTHONPATH=src .venv/bin/python -B scripts/prototype_p4_estimand_comparison_v0_1.py --demo
.venv/bin/python -I -B -m pytest -q -p no:cacheprovider tests/test_p4_estimand_comparison_prototype_v0_1.py
```

The self-test reports six passing checks. The demo emits the complete finite
JSON trace to stdout; neither command writes a run artifact to disk. The
focused successor test suite reports **52 passed**; the source and focused
tests also pass the repository's Python lint check.

The report retains all five estimands in `estimands`, the separate
`controls.origin_centered`, both fields, coefficients and fit provenance,
same-field numeric payloads and hashes, charge-blind component seals,
forward/reverse loop diagnostics, and the independent shared `geometry`.
The affine-based field payloads' `baseline_extrapolated` masks and the
declared boundary row identities make outside-hull loop support
reconstructable. These are local replay records, not signed evidence or
externally attested provenance.

The demo is a noiseless construction panel. Noise perturbation checks do not
make it a sensitivity study, and none of the development floors or sampling
guards has been qualified for real-model residuals. Small nonzero residuals
are retained numerically; they are not clipped to zero to obtain an expected
classification.

## 7. What this local result permits next

The comparison makes one ambiguity inspectable in the synthetic measurement
chain: whether a pattern survives a declared input/baseline accounting
operation when every residual field is measured afresh. It also demonstrates
that a mismatched subtraction can introduce winding. It does not show that
any target phenomenon exists in a language model.

The next separately scoped development step would still need to integrate
the representation-graph panel with exact oriented boundary identities and a
crossed, finite density/locality range. Fresh prospective fixtures and
per-branch sensitivity qualification would precede any separately frozen and
authorized model-access protocol. Neither the availability of Furnace nor a
visually compelling residual bypasses those decisions.
