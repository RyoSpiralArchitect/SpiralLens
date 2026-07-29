# D7 Confirmation Execution Design

Status: `implemented_seed_free_design`, `not_frozen`, `not_admitted`,
`not_run`.

This document is the single detailed anchor for the spectral-moment D7
execution topology added after the PR #12 construction foundation. It records
what is now implemented, what the implementation revealed about the D6 v0.1
admission contract, and which obligations still block a claim-bearing
confirmation.

## 1. Scope

The new internal design closes the execution topology before any official
confirmation seed is selected:

- two abstract confirmation seed slots;
- the four D6-required joint core/loop semantics;
- boundary, state-geometry-warp, and structured-observation-perturbation
  factors;
- the exact three field-estimation graphs A;
- the exact three cycle-construction graphs B;
- primary-boundary and off-core loop roles;
- the current development field estimator, blind core kernel, and continuous
  sampled-loop kernel; and
- the same `GraphInput` and A-bound field-estimate join between core and loop
  predictions.

It does not implement a D7 admission, full-design freeze, source-readiness
receipt, official seed supplier, launch intent, attempt claim, result/failure
schema, terminal writer, D8 replay, model access, or scientific promotion.

## 2. Exact repeated-measures inventory

The canonical seed-free factory uses seed slots rather than numeric seed
values:

| Grain | Exact count |
| --- | ---: |
| Primary units | `2 × 4 × 2 × 2 × 2 = 64` |
| Core cells | `64 × 3 A = 192` |
| Loop cells | `64 × 3 A × 3 B × 2 roles = 1,152` |
| Total event lanes | `1,344` |
| Required stress strata | `6`, with `32` primary units each |
| D2 units after boundary collapse | `32` |
| D4/D5 scientific execution units | `64` |
| Non-prerequisite primary denominator | `48` |
| Prerequisite-failure primary units | `16` |

Graph cells, loop roles, and stress variants are repeated measures. They are
not independent samples. The two seed slots are blocks; this design does not
claim that their statistical independence has been proved.

## 3. Full parent-design reconstruction

The D6 decision stores hashes, not enough typed bytes to reconstruct all
runtime choices. The D7 builder therefore requires both:

1. an authoritative `LoadedScopeLimitedD6Decision`; and
2. the strict `LoadedQualificationProtocol` whose canonical identity is bound
   by that decision.

It reconstructs the five full design bodies with the same body builder used by
the D6 sealer and verifies every hash:

| Parent body | SHA-256 |
| --- | --- |
| D6 decision | `c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07` |
| D6 admission | `2e4aa2a272a38ed68b61f612d8a3a261cc6376f3d9a8097f5dce701a2c3f5aa4` |
| Protocol | `9908bb83bb5ff5642416aa09d9e468e0a9499185cec9305e69a54143f2578bd1` |
| Graph axes | `71e7e1a128d4bfb4473b1b809fc16dde58971d38ab0d5b3b1ec8794150e05247` |
| Required cells | `4d243f9ba2c0029480bd98e002914f5a100aa93ac981aae5517142eee0dae7ff` |
| Required stress strata | `cabe0827e0dc74f4d118fa3453f6e887eec553a7005fcba3c30e6fea976b982f` |
| Thresholds | `17b4fc193c4d02ab5526dc2f4502832701480ef01deaf3acd01a6e06458cf271` |
| Aggregation | `300c3b63f3897fe808b418369d2dbeac76df41160b456f6e5feec6d3995dcef3` |

The authoritative D6 loader has already loaded and verified the historical
terminal result, manifest, and consumption companions. Their raw bytes are not
direct arguments to, reread by, or retained in the seed-free design. The
design binds the resulting authoritative D6 identity, including the decision,
admission, and current-loader source identities; those upstream companions are
therefore an explicit indirect provenance dependency.

## 4. D6 v0.1 manifest incompatibility

Implementation exposed a contract problem that the hash-only foundation could
not resolve.

The D6 required-cells body contains:

- numeric selection seeds;
- selection control identifiers;
- seed-bearing primary-unit identifiers; and
- seed-bearing core and loop cell identifiers.

The D6 required-stress body also contains the selection primary-unit
identifiers inside each stratum membership. A new-seed, construction-diverse
D7 inventory therefore cannot be byte-identical to either parent body without
reusing selection identities and weakening evidence disjointness.

The design records two separate facts:

- a typed structural projection from parent seed ordinal, control semantics,
  stress tuple, A graph, B graph, and loop role is exactly equal to the D7
  seed-slot projection; and
- exact parent cells/stress hash satisfaction remains `false`.

Structural equality is not silently reinterpreted as D6 v0.1 admission. A
reviewed, versioned successor admission or rebinding amendment is required
before freeze.

The parent aggregation body also names a `selection-seed-block`, and the
selection implementation registry cannot become the D7 registry because the
generator construction must differ. Their D7 application remains a separate
review obligation.

## 5. Stress translation

Every stress value is explicit. The generator spec has no nominal defaults.

| Axis | Nominal | Stressed | Translation |
| --- | ---: | ---: | --- |
| Boundary | central `(2,2)-(4,4)` | wide `(1,1)-(5,5)` | selects matched cycle support; does not change generator arrays |
| State geometry | `0.0` | `0.1` | `q_w = q + w sin(πq)/π`; changes states only |
| Observation perturbation | `0.0` | `0.01` | D6 nuisance operator `a cos(√2 α + phase(seed,row))`; changes fit/evaluation values only |

The prerequisite-failure unit remains in its requested perturbation stratum,
but its effective perturbation scale is zero. Both requested and effective
values, plus the suppression flag, are retained.

The spectral state vector is normalized by
`1 / sqrt(ambient_dimension) = 1 / sqrt(12)`. This is a construction rule, not
a learned threshold. Without normalization the locked radius `0.48` graph has
no edges. With the declared rule, the seed-free maximum axis-adjacent
distances remain below `0.48` under both warp levels with an explicit margin.
The full development inventory additionally exercises actual graph and cycle
construction rather than treating that distance check as sufficient.

## 6. Prediction path and oracle boundary

The implemented development path is:

```text
explicit stress spec
  -> label-free prepared estimator inputs
  -> GraphInput
  -> exact 3A / 3B matched-support executions
  -> current development Cartesian first-harmonic field estimator
  -> blind core inputs and sealed core predictions
  -> blind loop inputs and sealed continuous sampled-phase predictions
```

The blind core and loop kernels have no oracle parameter. The preparation API
does not construct an oracle-truth record, and no oracle record is supplied to
graph, field, core, or loop kernels. The orchestration layer still carries
case and unit identity in order to select a synthetic control and is not
claimed to be label-blind. The generator necessarily constructs the latent
signal used to synthesize observations; the narrower and testable statement is
that no oracle-truth record reaches the blind prediction kernels.

The field estimator is the current development implementation. It is not
called D7-locked or source-closed until the next PR publishes the D7-specific
implementation registry and closure.

The path stops before scoring and aggregation. It does not call D4/D5 collapse,
create a `GateResult`, create a `QualificationResult`, or publish a terminal.

## 7. Development-only conformance

Permanently excluded development seeds `9001` and `9002` were run through the
complete inventory:

- `64` primary predictions;
- `192` sealed core predictions;
- `1,152` sealed loop predictions;
- zero unmatched cycle representatives; and
- the expected development prediction-class distribution for all four
  controls.

This is implementation conformance only. The receipt is explicitly
claim-ineligible, produces no D7 result, and cannot be substituted for a
future unopened-seed confirmation.

## 8. Seed chronology

The official seed values remain absent. The required order is:

1. commit and verify the complete seed-free source closure;
2. publish and strictly reload a no-overwrite readiness artifact;
3. invoke the seed supplier once;
4. require exactly two unique, sorted, nonnegative signed-int64 seeds;
5. reject every development seed and both parent selection seeds;
6. bind the numeric seeds to `confirmation-seed-slot-00` and
   `confirmation-seed-slot-01`;
7. create the concrete full design and launch artifacts without executing;
8. commit that design;
9. issue the freeze receipt in a receipt-only descendant commit; and
10. execute only after the authoritative loader verifies the ancestry.

Seed values may be public after freeze. The controlled fact is chronology, not
permanent secrecy.

## 9. Next blocking PR

The next PR must resolve, before any official seed supply:

- reviewed construction-diversity and source-closure comparison;
- the versioned D6 cells/stress structural-rebinding contract;
- D7-specific implementation-registry and aggregation application;
- concrete result and failure schemas;
- no-overwrite readiness, launch, attempt, and execution-start chronology;
- absent terminal namespace verification;
- atomic terminal publication;
- the two-commit design/freeze-receipt lineage; and
- strict isolated replay requirements.

Until those are complete, the canonical state remains:

```text
implemented_seed_free_design
not_frozen
not_admitted
not_run
exact_parent_manifest_incompatibility_unresolved
```
