# Post-D6 Descriptive Analysis and Value-Blind D7 Gap Plan

- **Status:** frozen planning artifacts; the fixed-path descriptive runner is
  implemented but no descriptive result or confirmation has run
- **Claim ceiling:** Level 0
- **Claim delta:** none
- **Scope:** the exact PR #9 Cartesian-surrogate terminal and PR #10 D6 decision
- **Non-claims:** no gate reclassification, D7 admission, D8 replay, P0 selection,
  representation transfer, subject preparation, topology, semantics, or Pythia
  scientific use

## 1. Why the plan is split

The official D0-D5 terminal is already open. Any analysis of its values is
therefore post-selection, even when every calculation is exact and read-only.
That analysis can describe the recorded construction, expose fragility, and
improve the instrument's diagnostics. It cannot choose the D7 construction,
thresholds, graph cells, exclusions, estimator, trivialization, or stress
schedule.

The D7 gap review has a different chronology. It may inspect the already
sealed D6 admission contract and tracked implementation surfaces, but it may
not inspect the terminal values or any unopened confirmation values. Combining
these two activities in one artifact would allow a descriptive result to leak
into the design of the independent confirmation.

PR #11 therefore freezes two separate canonical artifacts:

| Artifact | Canonical/source SHA-256 | Permitted use |
| --- | --- | --- |
| [`post_d6_descriptive_analysis_v0_1.json`](../protocols/post_d6_descriptive_analysis_v0_1.json) | `9b1a8d9c3857fd18fff7b4dfb20a75eade2f56f4933e05126830669cd8ccb981` | Post-selection description of the already-opened PR #9 terminal |
| [`d7_structural_gap_matrix_v0_1.json`](../protocols/d7_structural_gap_matrix_v0_1.json) | `018f06ce15cafb7830f522e41001c7a275bd85a76471c58e0fd04df009f67624` | Value-blind implementation scheduling against the D6 contract |

Both are declarations. They grant no consumer authority and expose no writer,
runner, family-admission helper, D7 promoter, or D8 promoter. Repository tests
verify their canonical bytes and exact tracked parents. The artifacts
themselves do not turn a caller-supplied digest into proof.

Here, value-blind describes the matrix's allowed inputs, not the reviewer's
memory or cognition. The operator has prior outcome exposure, and the matrix
records that fact. It claims only that terminal values were not used as matrix
inputs. It does not claim an independent blinded reviewer or a cryptographic
information barrier.

The descriptive plan itself was written after opened outcome values were used
to fix the recorded counts and scientific grains. It therefore records
`planning_used_opened_outcome_values=true`; only its runner and result remain
unexecuted. Because there is no independent operator or information barrier,
the complete D7 family descriptor, admission, protocol, source closure, and
lifecycle must be frozen and receipt-bound before that runner may execute.
This ordering prevents newly computed fine-grained descriptions from tuning
the D7 design. It does not erase the operator's earlier aggregate-result
exposure or turn D7 into a cognitively blinded experiment.

## 2. Exact parent evidence

The descriptive plan binds:

- PR #9 merge commit
  `22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993`;
- protocol `d0-d5-f2-cartesian-selection-v0-1`, canonical/source SHA-256
  `9908bb83bb5ff5642416aa09d9e468e0a9499185cec9305e69a54143f2578bd1`;
- terminal result `qualification-result-6b74f0569ed76cbf3ce3e09b`, SHA-256
  `44749d8d237b8b35874099c605f8de3d76130691ce8beb92e1ccf80fa368c13a`;
- result evidence root
  `131a51f5ea2546fe20ddba8006fe83e7b8e95042688162640c4bb24696876741`;
- terminal manifest SHA-256
  `518b66d715cf9bd05e12de62cb5681ec63ec7f978fd4d2538ba3c2594deed4b1`;
- terminal consumption SHA-256
  `a42ae9cffb6a2c87de6ed645e0982e85b09046a4ed5ad3f815a8a8ce38c0cadb`;
- launch authorization SHA-256
  `13d17daa0aeb09874e1526af88c2c1742d8e9460d0a373de17ece28b26d0269e`;
- PR #10 merge commit
  `f869d53d890ae35b43c3dbca2ce6363c78fea367`; and
- the D6 decision and embedded admission identities below.

Repository tests verify that the current protocol, terminal result, terminal
manifest, and consumption bytes equal their Git blobs at the recorded PR #9
merge commit, and that the current D6 decision equals its Git blob at the
recorded PR #10 merge commit. A matching working-tree hash alone is not
treated as exact-parent evidence.

The D7 matrix binds only the D6 decision and a value-blind source snapshot. It
does not include the terminal result, terminal manifest, or consumption in its
allowed inputs.

The D6 identities are:

- decision `cartesian-surrogate-d6-decision-v0-1`;
- canonical/source SHA-256
  `c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07`;
- decision source commit
  `7673ef81bbd67afce5d20255cc6ca6d68e453c3f`;
- first artifact commit
  `1fcff8bfedc7d3ae8386bc409595607b5b57b8c4`;
- selection-terminal binding SHA-256
  `85dedcc7003d000dc4260a9e9036e3170aadf28251e8c3c7c67afae5998b8c8d`;
- admission
  `cartesian-surrogate-independent-family-admission-v0-1`; and
- embedded admission SHA-256
  `2e4aa2a272a38ed68b61f612d8a3a261cc6376f3d9a8097f5dce701a2c3f5aa4`.

The authoritative D6 reload remains local archival evidence because its launch
descriptor binds `absolute_local_paths`. The PR #10 merge preserved the
decision source ancestry and the authoritative reload passed again on merged
main. PR #11 does not reinterpret that local reload as cross-worktree proof.

## 3. What has actually been observed

The official terminal records the following scoped gate outcomes:

| Gate | Attempted/pass | Evaluable | Expected prerequisite failures | Positive scope |
| --- | ---: | ---: | ---: | --- |
| D0 | 2/2 | 2 | 0 | engine and protocol contracts |
| D1 | 2/2 | 2 | 0 | Cartesian surrogate and representation development |
| D2 | 32/32 | 24 | 8 | Cartesian surrogate only |
| D3 | 2/2 | 2 | 0 | Cartesian surrogate and representation development |
| D4 | 64/64 | 48 | 16 | Cartesian surrogate only |
| D5 | 64/64 | 48 | 16 | Cartesian surrogate only |

These counts are gate bookkeeping, not six independent experiments and not
inferential sample sizes.

The positive statement is narrow:

> One Cartesian Fourier quadrature surrogate construction passed the frozen
> D0-D5 selection protocol, and D6 froze the exact requirements for a later
> construction-diverse confirmation.

The terminal did not observe a model-bound order parameter. D2 is a
charge-blind localized-core/no-core/prerequisite path. D4 is an unrounded,
continuous sampled-loop total. No same-substrate core-loop join, integer
winding, quantized charge, topology, semantic meaning, SAE relation, or causal
effect was observed.

## 4. Scientific grain contract

PR #11 froze the following descriptive grains before any analysis runner
existed. The later repository-only runner preserves those frozen grains.

### 4.1 D2 scientific input unit

There are 32 D2 scientific input units. Boundary variants are paired nuisance
repeats and collapse only after exact agreement of the declared outcomes and
the persisted `amplitude`, `identifiability_score`, and `support_counts` array
descriptors. Boundary-specific input, graph, estimator, oracle, and prediction
identities remain distinct and are reported rather than treated as byte
identity. The two seed blocks are not proved independent. The 32 units
therefore do not authorize an iid `n = 32` inference.

The analysis must report:

- 32 attempted and passed gate units;
- 24 evaluable core outcomes;
- 8 expected prerequisite failures; and
- boundary-repeat equality separately from scientific disposition.

### 4.2 D4-D5 loop execution unit

There are 64 loop-bearing executions. Boundary is retained because it changes
the loop execution. Each execution contains nine field-graph by cycle-graph
pairs, and every pair has both a `primary_boundary` and an `offcore_control`
loop role. This yields 18 crossed cells per execution and 1,152 total: 576 per
role. The graph pairs and both roles are repeated measurements of the same
execution, not independent observations.

The analysis must report:

- 64 attempted and passed gate units;
- 48 evaluable executions;
- 16 expected prerequisite failures;
- 18 crossed cells per execution, separated into nine cells for each loop role;
- within-execution graph-pair effects; and
- between-input worst cases without converting cells into replicates.

### 4.3 Construction-family and artifact units

The observed construction-family count is one. The PR #9 terminal plus PR #10
D6 decision form one artifact-interpretation unit, not a scientific sample.
No p-value, confidence interval, generalization error, or independent
confirmation count may be formed from graph cells, boundary repeats, events,
loops, stress cells, seed blocks, or artifact members.

Every future table must name its unit and denominator. A prerequisite-failure
row may be outside an evaluable denominator, but it remains mandatory and
cannot be silently excluded.

## 5. Frozen post-selection descriptive work

The descriptive artifact declares eight mandatory packages. Missing packages
must be published as explicit missing/blocked entries; they may not disappear
from the report.

### 5.1 Identity, lineage, and claim boundary

Rejoin the exact protocol, terminal result, evidence root, manifest,
consumption, launch authorization, D6 decision, and admission specification.

Required outputs:

- parent identity table;
- gate state and claim-scope table;
- authority/non-claim table; and
- a clear split between source identity, archival validation, historical
  reexecution, and current-source compatibility.

This package must not rerun D1 under current code or call historical parser
success current-engine compatibility.

### 5.2 D1 frozen-threshold margin atlas

For each analytic D1 check, report the signed distance from its already-frozen
threshold. Keep Cartesian surrogate and representation-development checks
separate.

The atlas may identify a check as numerically close to or far from its frozen
boundary. It may not change a threshold, choose a D7 design, or turn margin
size into a stronger claim.

### 5.3 D2 core and prerequisite matrix

Report the 32 scientific input units across:

- expected localized core;
- expected no core;
- expected prerequisite failure;
- predicted core/no-core/abstain;
- boundary-repeat equality;
- graph family;
- amplitude;
- identifiability; and
- support.

The high-amplitude identifiability-loss decoy must remain distinct from a
low-amplitude missing-support prerequisite failure. Low support may not be
relabeled as evidence for a core.

### 5.4 D3 transformation-law audit

Separate:

- ambient-basis reconstruction error;
- reference O(2) rotation/reflection error;
- loop-reversal sign error;
- determinant/sign rules; and
- array alignment error from observable-law error.

This is a covariance/invariance audit. It does not authorize an integer or
topology claim.

### 5.5 D4 crossed-graph descriptive matrix

Report the complete three-by-three field-graph by cycle-graph matrix separately
for `primary_boundary` and `offcore_control`: 18 crossed cells per execution.
Neither role may be omitted or collapsed into the other. Keep diagonal and
off-diagonal graph pairs distinct, and separate:

- graph adjacency difference;
- field-output RMS effect;
- loop-total span;
- matched-boundary status; and
- support/prerequisite status.

The analysis must demonstrate actual estimator consumption rather than merely
different graph IDs. No graph family may be selected for D7 from these
post-selection values.

### 5.6 D5 worst-case stress and coverage

Report worst cases by:

- boundary;
- state-geometry warp;
- structured-observation perturbation;
- graph pair; and
- loop role; and
- required stratum.

Coverage, abstention, recall, specificity, and prerequisite-failure counts must
remain separate. No denominator may be changed after inspecting a result.

### 5.7 Nonvacuity, abstention, and failure ledger

Rejoin every mandatory nonvacuity condition and typed failure route. Report
abstention reasons without treating a required prerequisite failure as a
missing or failed sample.

### 5.8 Evidence-independence map

Map which observations share:

- generator construction;
- seed block;
- boundary repeat;
- graph family;
- implementation;
- estimator;
- threshold;
- oracle; and
- evidence bundle.

The output must distinguish deterministic replay, same-family replication,
construction diversity, implementation diversity, and epistemic independence.
Only the first two have evidence in the current lane.

## 6. Descriptive-result publication boundary

PR #11 did not implement the descriptive runner or writer, and its frozen
canonical metadata remains unchanged. `D7-OPS-23` now has a repository-only,
fixed-path implementation that derives all 27 declared outputs from the exact
parents: 26 are available and the full-scope amplitude/identifiability/support
separation is explicitly blocked because its historical main-array values were
not persisted. Its three exact Python files are excluded from the wheel and
are members of the reviewed exact-current source/runtime re-anchor now tracked
on this branch. The Level-0 item-22 target is also persisted at
`publication-complete-unfrozen`, but neither source nor target is an execution
or result. Item 23 may run only after a distinct target
review/freeze-authorization commit and a strictly later committed receipt bind
the full-design, replay-target, and atomic target-publication records. The runner
separately verifies the frozen target tree and that its result path was absent
when the freeze first entered history. A launch intent or closed fused
descriptor is a later artifact, is not an item-23 prerequisite, and is not an
item-23 analysis input. The runner must then review the frozen descriptive
plan and publish one separate result artifact that:

- consumes exactly one additional allowed input class,
  `committed-d7-full-design-freeze-receipt`;
- freezes that receipt's exact repository-relative path, Git commit/blob, and
  SHA-256 before runner execution;
- binds that receipt without reading any D7 result or confirmation value;
- binds the plan SHA-256 and every parent SHA-256;
- records a source binding and exact read trace;
- reports all eight packages;
- uses a new, initially absent namespace;
- publishes atomically with no overwrite;
- leaves the PR #9 and PR #10 bytes unchanged;
- records `claim_delta=none`;
- records `official_gate_reclassification_authorized=false`; and
- is forbidden as a D7 design or admission input.

The future persisted result is exploratory descriptive evidence. Its purpose
is to make the observed construction legible, not to convert it into
independent confirmation. A caller-supplied receipt digest is not proof: the
runner must read and validate the committed blob and include it in the exact
read trace. That seven-file trace is explicitly the analysis-input trace.
Source/runtime re-anchor checks and Git tree chronology are recorded
separately. The item-23 lane does not enter item 22's seed-parsing observer: it
checks the immutable presence of the seed-bearing target tree without reading
or parsing its contents, and therefore does not recompute or claim to
reauthenticate the target digest graph. The committed freeze receipt is the
sole additional design-metadata input.

The source implementation also treats provenance and publication as live
bindings rather than pathname assertions. It rejects change-then-revert events
across the full reachable Git history of every plan-bound input, joins the
three repository-only files and all loaded `spirallens` modules to the supplied
checkout, and retains directory descriptors for both the result namespace and
the frozen transaction through publication. Before returning success it
rereads the result through the retained descriptor and requires the exact
published bytes, device, inode, byte count, and one-link regular-file contract.
Any exception after the no-replace publication point is an explicitly
unproved post-publication binding: the visible result is retained, rollback is
not inferred, and republishing to that namespace is forbidden.

## 7. Value-blind D7 gap vocabulary

The separate D7 matrix uses a closed, non-promotional vocabulary:

- `absent`: no required typed contract or execution surface exists;
- `contract_only`: D6 names the requirement, but no D7 evidence exists;
- `implementation_foundation_only`: reusable code exists, but it is neither a
  candidate nor admitted evidence;
- `evidence_present_but_ineligible`: evidence exists but cannot satisfy the
  requirement; and
- `blocked`: a downstream requirement cannot run before another missing gate.

There is no `partial pass`, percentage complete, weighted score, readiness
score, family ranking, or aggregate progress metric.

## 8. Current D7 structural gaps

| Requirement | Frozen status | What is missing |
| --- | --- | --- |
| Distinct construction family | `implementation_foundation_only` | Typed family descriptor and D6-bound admission |
| Distinct generator family | `implementation_foundation_only` | Confirmation-family identity and admission receipt |
| Pre-access family admission | `absent` | Canonical committed receipt before values |
| Sealed-before-access chronology | `contract_only` | Confirmation-specific access chronology |
| Required case semantics | `implementation_foundation_only` | Exact four D2-D5 semantics under one full path |
| Locked estimator/trivialization | `absent` | Spectral input path and conformance evidence |
| Confirmation implementation registry | `contract_only` | Confirmation source closure and registry |
| Locked graph axes | `absent` | Full field-graph and cycle-graph consumption |
| Charge-blind core path | `implementation_foundation_only` | Confirmation-family integration, source closure, and matched-support path |
| Separate loop path | `implementation_foundation_only` | Confirmation-family integration, source closure, and matched discrete support |
| Cells and stress strata | `contract_only` | Complete confirmation execution |
| Thresholds and aggregation | `contract_only` | Applied confirmation result |
| Evidence disjointness | `contract_only` | Closed confirmation inventory and receipt |
| No override/no exclusion | `contract_only` | Enforced D7 launch and terminal chronology |
| Exclusive attempt and terminal lineage | `implementation_foundation_only` | Confirmation-specific typed lifecycle |
| Typed D7 result/evidence root | `absent` | Result schema and terminal artifact |
| Confirmation store durability | `implementation_foundation_only` | Administrative deletion and multi-host guarantees |
| Isolated D8 replay | `blocked` | D7 pass and typed replay/source/namespace receipts |

The existing spectral-moment implementation is deliberately called an
implementation foundation. It is mathematically different from the Cartesian
construction, but it does not construct the required graph, core, loop, full
D2-D5 path, execution lineage, or evidence bundle. It is not a D7 candidate or
admitted family.

The existing qualification core and loop kernels are also implementation
foundations. `estimate_and_seal_core()` is truth-blind and
`estimate_and_seal_loop()` consumes a label-free representative loop, but
neither is integrated into an admitted confirmation family with matched
support, confirmation source closure, lifecycle, or evidence. D7 should reuse
and bind these kernels rather than reimplement them; their existence does not
count as confirmation.

Unopened Cartesian seeds remain same-family replication. A new source digest,
implementation label, or seed cannot create construction diversity.

## 9. D7 implementation sequence

The gap matrix may schedule engineering only. Before any confirmation value is
opened, a future sequence must:

1. define a typed confirmation-family descriptor with a genuinely different
   construction and generator identity;
2. bind it to the exact D6 decision and embedded admission specification;
3. freeze its complete source and implementation registry;
4. prove the required four case semantics can enter the locked surrogate
   estimator and trivialization;
5. integrate the existing separate truth-blind core and sampled-loop kernels
   on matched discrete support and bind them into the confirmation source
   closure;
6. implement every locked graph axis, cell, stress stratum, threshold, and
   aggregation rule;
7. publish a canonical family-admission receipt before confirmation access;
8. freeze the confirmation protocol, source readiness, seed-bearing target,
   full design, lifecycle policy, and declared result schema;
9. prohibit policy override and post-selection exclusion in the typed
   lifecycle; and
10. publish one D7 result or typed failure with a complete evidence root.

Steps 1-9 together form the minimum full-design freeze. Their committed
receipt must exist before the post-selection descriptive runner may execute;
the runner separately requires that its output namespace was absent at that
freeze's immutable introduction. Launch intent remains a later, distinct
artifact.
If any of those design bytes changes after descriptive execution, the prior
admission is invalid for this chronology and a new versioned design and review
are required; the change cannot be called a continuation of the frozen D7.

Any required `fail` makes D7 fail. Any incomplete required evidence makes D7
`insufficient` or keeps it `not_run`; it cannot be averaged into a progress
score.

## 10. D8 replay

D8 remains `not_run` because D7 has not passed and no replay surface exists.
The future replay must use:

- a fresh process;
- a separate initially absent namespace;
- typed source and runtime receipts;
- typed execution and attempt receipts;
- a closed member inventory;
- canonical manifest bytes;
- payload bytes; and
- exact byte-identical comparison of the complete bundle.

Two caller-supplied byte strings cannot pass D8. Replay establishes
deterministic reproduction of the D7 bundle; it does not count as a second
independent construction-family confirmation.

## 11. Three lanes that must not collapse

### Lane S — surrogate-engine qualification

Complete the construction-diverse D7 confirmation and isolated D8 replay. This
tests whether the qualification engine survives a different synthetic
construction.

### Lane R — representation-instrument selection

Compare F0-F4 on representation-shaped substrates, then run
representation-native qualification for the selected instrument. A Lane S
pass does not transfer D2-D5 to the representation estimator and does not
select P0.

### Lane E — public-example engineering

The Pythia-70M public-example lane has already validated bounded offline model
capture, storage, checksum, and reload. Its receipt records
`model_accessed=true` and `activation_values_persisted=true`, while candidate,
neighbor, instrument, graph, field, core, loop, holonomy, winding, semantic,
SAE, causal, integer, and D0-D8 analysis remain `not_run`.

Lane E is not an input to either PR #11 artifact. PR #6's descriptor-only
prepare mechanism is a framework-neutral access primitive, not an issued
subject protocol or project-level subject-preparation authority.

## 12. Full research sequence

Subject to review at each transition, the current full sequence is:

1. freeze these two PR #11 artifacts;
2. implement and commit the value-excluded D7 family descriptor, admission,
   protocol, full path, source closure, and lifecycle;
3. freeze and receipt-bind the complete D7 design and target while the
   descriptive-result namespace is still absent;
4. only then execute and publish the separate post-selection descriptive
   result; any later D7 design change requires a new version and review;
5. create the closed launch descriptor and run one unopened
   construction-diverse D7 confirmation;
6. run one isolated full-bundle D8 replay;
7. begin the separate representation-native F0-F4 selection lane;
8. independently confirm and replay the selected representation instrument;
9. establish a same-substrate field, charge-blind core, and loop join;
10. only if the convention permits it, test calibration-side integer stability
    and topology-invariance eligibility; this is an instrument gate, not a
    model-topology observation;
11. issue a reviewed subject manifest and run metadata-only subject
    `prepare-only`;
12. obtain separate subject execution authorization;
13. run semantics-free structural subject discovery and, only for a frozen
    candidate, apply the already-frozen topology rules without retuning; and
14. only after a structural candidate exists, run held-out semantic, SAE, and
    causal tests.

Negative or insufficient results do not invalidate the library. They constrain
the scientific claim while still exercising canonical codecs, source/evidence
bindings, lifecycle types, closed inventories, and replay receipts.

## 13. Library extraction roadmap

PR #11 intentionally adds no public analysis API. The two artifacts have only
one consumer and encode experiment-specific chronology. Promoting them now
would freeze post-hoc assumptions into the library.

The reusable candidates to extract after a second independent consumer are:

- typed parent-evidence identities;
- scientific-unit and denominator declarations;
- post-selection exposure status;
- claim-delta and reclassification guards;
- non-promotional gap vocabularies;
- source/evidence/read-trace bindings;
- closed deliverable inventories;
- no-overwrite publication;
- isolated replay receipts; and
- explicit separation between software maturity and scientific status.

Experiment-specific work-package IDs, the Cartesian gate counts, spectral
foundation status, and D7 requirement rows remain research artifacts. A future
generic API must not accept arbitrary mappings, self-attested booleans,
caller-byte-only promotion, or model-framework types.
