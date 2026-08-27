# P4 M1 Graph-Scale Transport Development Prototype v0.1

**Development state:** implementation present; deterministic synthetic plumbing
`pass`

**P4 v0.3 state:** `planned_not_frozen_not_run`

**Decision date:** 2026-08-28

**Claim ceiling:** Level 0 development plumbing

**Protocol-freeze, launch, execution, model, subject, network, Pythia-70M, and
Pythia-160M authority:** false

This prototype implements only M1 of the design-only
[P4 phase-capture measurement chain](P4_PHASE_CAPTURE_MEASUREMENT_CHAIN.md):
field-blind graph-scale transport, multi-nuisance worst-case selection, and one
fresh synthetic held-out application. It does not construct or read F2, F4, an
order parameter, a core, a loop observable, holonomy, winding, a phase-like
regime, a transition, a control outcome, or a subject outcome.

The implementation is the single executable file
`scripts/prototype_p4_graph_scale_transport_v0_1.py`, SHA-256
`05cba8a7de365357a33a613efa4720489368ed44dc86f2f89c25498384482516`.
It uses NumPy and the existing canonical SpiralLens graph constructors; it
writes no artifact and has no model, network, or official-lifecycle path.

## 1. Transport law

Each candidate law contains four positive reduced rational numbers
((\kappa,\sigma,\rho,\tau)). For an input with (n) rows, the prototype derives

\[
k=\operatorname{clip}_{[2,n-1]}\lceil\kappa(n-1)\rceil,
\qquad
k_s=\operatorname{clip}_{[1,n-1]}\lceil\sigma(n-1)\rceil,
\]

\[
s=\operatorname{median}_i d_{i,(k_s)},
\qquad
r=\rho s,
\qquad
m=\operatorname{clip}_{[1,k]}\lceil\tau k\rceil.
\]

Mutual-kNN receives (k), fixed-radius receives (r), and shared-neighbor
receives ((k,m)). The local scale uses float64 Euclidean distances, a declared
distance/vertex-identity/row tie order, and a fixed even-sample median rule.
Nonfinite or nonpositive scale/radius yields `insufficient`; it does not fall
back to an absolute graph parameter.

The law may read only vertex identity, vertex count, numerical substrate
coordinates, their distance/order statistics, and the declared boundary vertex
identities. Its API has no field, F2/F4, amplitude, direction, core, loop,
holonomy, winding, phase, charge, control, or subject-outcome argument.

## 2. Development selector

The synthetic development fixture evaluates 54 unique dimensionless laws
against four calibration cases that vary seed, density warp, deterministic
coordinate noise, and sampling density. This is a bounded plumbing fixture,
not a factorial sensitivity study and not a proposed official input.

A law is eligible only if all three graph families pass every structural gate
on every calibration case. The broad development gates are:

| Gate | Development value |
| --- | ---: |
| mean degree | [1,16] |
| largest-component fraction | at least 4/5 |
| two-core fraction | at least 1/2 |
| cycle rank | at least 1 |
| boundary endpoint support | at most 3 graph hops per declared domain edge |
| largest/smallest graph edge-count ratio | at most 3 |
| largest-component fraction spread | at most 1/4 |
| two-core fraction spread | at most 2/5 |
| common two-core fraction | at least 2/5 |
| pairwise edge-set Jaccard | at most 49/50 |

These values were chosen to exercise the mechanism after the M1 strategy was
designed. They are explicitly `development-only-not-frozen`; their synthetic
success is not prospective calibration for P4 v0.3.

Among laws that pass all calibration cases, selection minimizes the
coordinatewise worst case in this fixed lexicographic order:

1. edge-count ratio across the three graph families;
2. summed absolute mean-degree deviation from the development target 6;
3. deficit in the common two-core fraction;
4. sum of graph component counts; and
5. canonical dimensionless parameter key.

No average-case objective can rescue a failed nuisance case. Pairwise Jaccard
is a gate, not an optimization target. Candidate and calibration-case order do
not affect the decision, and duplicate parameterizations fail closed.

## 3. Held-out application boundary

The selector returns a factory-produced in-memory decision binding the chosen
law, exact gates, calibration report, and canonical report digest. The held-out
function accepts only that decision, one case explicitly tagged
`held-out-confirmation`, and the same gates. It accepts no candidate set and has
no reselection or threshold-widening argument. Changed report bytes, changed
gates, a nonpassing decision, or the wrong case role fail closed.

This separation demonstrates a no-reselection API shape. It is not
cryptographic proof that a developer could not edit or rerun this development
program, and it is not the exact-one lifecycle required by an official P4
protocol.

## 4. What boundary support means here

For each graph family, the prototype asks whether every adjacent pair of
predeclared boundary vertex identities has some path of at most the declared
hop limit. This is a reception/refinement support check only.

The path may traverse interior vertices; different boundary segments may
overlap; the check does not bind one oriented simple cycle, preserve a homology
class, establish an inside/outside relation, or compute holonomy or winding.
Therefore `boundary_supported=true`, nonzero cycle rank, or common two-core
coverage is not topology evidence and cannot be promoted to M5-M8.

## 5. Deterministic synthetic observation

For the committed v0.1 source, the in-memory demo produced:

| Item | Observation |
| --- | --- |
| candidate laws | 54 |
| calibration nuisance cases | 4 |
| eligible across every calibration case | 6 |
| selected development law | `m1-development-law-046` |
| ((\kappa,\sigma,\rho,\tau)) | ((1/4,1/6,1,1/2)) |
| fresh synthetic held-out case | `m1-held-out-e`, 8 by 8 |
| held-out structural state | `pass` |

The selected-law fingerprint is
`ee546f8fcf17d212d317958a4f1a31f5f06b467e1945295b0fed40a4291581d4`;
the gate fingerprint is
`27044d1f5cfbc29f0c0e99d17a18e3146159180685a9a87e48c63b39f0e74a54`;
and the selection-decision fingerprint is
`1cf86cdda8de347313737c581eaa9295d03b314da274376cffcf5b5924504a03`.
These identify the deterministic development observation only.

This `pass` means the proposed transport/selection/held-out plumbing can
produce and carry one internally consistent decision on its own synthetic
fixture. It does not establish nuisance robustness on a qualified detection
surface, graph-family validity for model activations, a P4 v0.3 threshold, or
scientific sensitivity.

## 6. Adversarial coverage and next boundary

The test surface covers exact rational clipping, candidate/case-order
invariance, worst-case rather than average-case ranking, global-scale and
signed-coordinate covariance, joint row-permutation invariance, factory-only
selection, digest and gate mutation, duplicate laws, role separation, zero
local scale, boundary failure, no-eligible-law behavior, deterministic output,
no filesystem writes, forbidden model/network/lifecycle imports, and unchanged
P4 v0.2 evidence hashes.

The next decision is not to run P4 v0.3. A later, separately reviewed freeze
would still need prospective nuisance definitions, candidate bounds, numeric
gates, an official fresh held-out identity, detection-surface requirements,
resource bounds, exact source/input chronology, and exact-one lifecycle
authority. Until then, the development law and all numeric values in this file
remain replaceable engineering observations with no scientific or topology
authority.

## 7. Explicit nonclaims

- P4 v0.3 is not frozen, launched, attempted, or executed.
- No Pythia model, tokenizer, activation, subject input, or network resource was
  accessed.
- F2, F4, order parameter, core, holonomy, winding, phase-like regime, and
  transition remain unevaluated.
- A synthetic `pass` is not a qualified positive, qualified null, graph
  calibration result, milestone, release, or publication claim.
- P4 v0.2 remains consumed and unchanged; its accessed confirmation is not
  reused for selection.
