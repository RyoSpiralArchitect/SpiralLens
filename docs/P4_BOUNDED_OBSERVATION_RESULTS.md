# P4 bounded-observation development controls

Date: 2026-09-13. Synthetic / Level 0. Local deterministic prototype,
not a new independent-cohort campaign, calibrated confidence result or model run.

The useful change is executable separation of three cases: a bounded witness,
an absent witness, and a witness whose declared bound is deliberately false.
Noise now propagates through the polynomial fit into the center/separation
outer ranges under an explicit post-adapter error contract. #122 is unchanged.

## Implemented and exercised

The [specification](P4_BOUNDED_OBSERVATION_PLAN.md) was committed at `c7d22a7`
before the new fixtures. Execution source is
`4fb8e659367b85dc85681ecafa1ea9b97f794664`.

- A separately declared witness supplies a triangle-inequality reference bound.
  The selected reference is never corrected using geometry truth or an ideal
  coefficient. Declared independence is not verified physical independence.
- Equal-cost five-point witness crosses use h=0.5 and h=1.0. At a declared
  pointwise error radius 1e-6, their constant row radii both equal 1e-6+1e-12;
  the two slope radii are 2e-6+1e-12 and 1e-6+1e-12, respectively. This is
  the fit's error-propagation law, not an observed general accuracy gain.
- Declared norm errors on nine fit and sixteen held-out moment observations
  propagate through the actual quadratic design. There is no fitted scalar
  tolerance, Gaussian-to-hard-bound conversion or retrospective radius choice.
- Missing witness/error support remains unavailable. Curvature compatible with
  zero is unresolved, not a verified affine field or proof of no structure.

## Outcomes and their denominators

There are 1,152 paired development readouts: two placements, four coefficient
stress modes, four evaluation-error radii, nine fixtures, F2/F4, and bounded
versus absent witness. All use inherited development geometry seed 7; only
the bounded-noise roles use the new namespace. This is **not a new independent
geometry cohort or 1,152 independent trials**. Seventy-two measured moment
inputs are reused sixteen times each. Both hypotheses receive matched
post-adapter errors, so this is not a new F2-versus-F4 performance comparison.

| Witness lane | Readouts | Quadratic cases with ranges | Center misses | Separation misses | Single falsely requires two |
| --- | ---: | ---: | ---: | ---: | ---: |
| Declared witness bound holds in fixture | 432 | 192 | 0 / 192 | 0 / 192 | 0 / 48 singles |
| Shared bias violates witness bound | 144 | 64 | 0 / 64 | 48 / 64 | 12 / 16 singles |
| Witness absent | 576 | 0 | unavailable | unavailable | no split decision |

The valid-contract lane retains all 48 zero controls as `zero_not_excluded`.
Linear and constant controls remain curvature-unresolved; dipoles are outside
the supported curvature family and cubics fail held-out quadratic compatibility.
Those outcomes are retained, not counted as successful root recovery.

In the deliberately shared-bias lane, all 144 witness bounds are false by
construction. At the three smaller error radii, the quadratic separation
ranges miss truth in all 48 cases although their centers remain covered.
At the largest error radius 1e-3, broader ranges cover all sixteen quadratic
cases, but this does **not** rehabilitate the false witness contract. This is
another concrete example of correct midpoint or plausible interval coverage
not establishing reference validity. Absent-witness records have no witness
contract to violate; their witness-coverage score is null, not false or true.

At h=1.0 with an unshifted reference, all six pair readouts at each of the
three smaller evaluation radii require two, while both singles retain one.
At radius 1e-3 all eight quadratic readouts retain the single-center alternative.
Noise therefore appears as lost resolving power rather than a forced binary
finding. These are paired fixture behaviors, not calibrated detection rates.

## Validation and reproducible evidence

All 185 new tests pass: 91 witness-budget, 70 polynomial-error and 24 runner
tests. They include exact report replay, absent evidence, malformed inputs,
underdeclared held-out noise, shared-bias failure, and canonical type tampering.
The complete local P4 plus generated-view regression passes 1,158 tests;
eight CUDA tests are explicitly skipped because this Mac has no CUDA device.
Ruff checks and formatting pass. The workflow adds seven new source/plan/test
hash bindings and the three test modules without changing predecessor bindings.
Remote clean-wheel results, if any, are reported separately from local testing.

The exclusive-created local report is
`artifacts/p4-bounded-observation-20260913-hudFVb/development-report.json`:

- Bytes: 8,102,356.
- File SHA-256: `8e7df9d435e8b14ef2b49f49614dd833ad76f9cc9baf31c914da677c7f1834c1`.
- Canonical report seal: `0df23e1fb7168ab16056840c1721862b2d962d14623d9dc0c7a7c666af9f5ad1`.
- Specification SHA-256: `3a0d0a3dd1b9d7b7a74da21e2ac5e1ffcc9b294c27af97f223b3347412e1bbdb`.
- 216 source/configuration bindings; full measurements, witness fits,
  reference budgets, readouts, post-inference scores and all summary slices.
- Complete deterministic regeneration and canonical comparison passed.

The report is retained locally, not added as an 8 MB Git payload. Reproduce
from the execution-source checkout with the worktree's dependencies:

```sh
PYTHONPATH=src:scripts .venv/bin/python scripts/run_p4_bounded_observation_v0_1.py --output /absolute/new/development-report.json
PYTHONPATH=src:scripts .venv/bin/python scripts/run_p4_bounded_observation_v0_1.py --verify /absolute/new/development-report.json
```

The output parent must exist; an existing file is never overwritten. Replay
binds the source tree and Python/NumPy/SciPy versions, so it is intentionally
not a promise of cross-environment byte identity. Historical source changes
require a new report, not rewriting the old one.

## What this does not establish; next bounded step

The new hard bounds apply to bounded **moment-space** error, not #122's
Gaussian noise injected into raw probes. Actual raw-probe-to-moment propagation
and an independently validated witness/transfer-error budget are still missing.
Wider placement cannot identify common affine bias. Finite-point family
compatibility cannot verify global holomorphic structure, and the current
float64 allowance is not a formal numerical proof.

Next, specify and test the raw-probe/adapter error model and witness transfer
checks, then freeze new independent calibration/evaluation cohorts and a
bounded campaign. The campaign is not frozen/not run. Do not enlarge the old
envelope, reinterpret old nulls, modify old local-loop scores, or claim an
improvement rate from this one development geometry.

The research-watch split is retained in the plan: condition-specific evaluation
now, output Fisher geometry and constructed-cycle controls later. No Furnace,
GPU, real model, automation change or external intervention was used. Evidence
for model core/phase/transition/holonomy/winding remains unestablished, and no
scientific authority is granted. D7/D8, SCI-S1/S2 and Pythia-160M gates are unchanged.
