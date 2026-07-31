# SpiralLens Research-to-Library Roadmap

- **Status:** anchor document
- **Project maturity:** experimental, pre-1.0
- **License:** Apache-2.0
- **Canonical repository:** `RyoSpiralArchitect/SpiralLens`

This document is the single detailed roadmap for growing SpiralLens from a
research instrument into a reusable library. It defines what each phase must
deliver, what evidence is required to leave that phase, which interfaces may
stabilize, and which scientific claims remain out of scope.

The roadmap is capability-based rather than date-based. A milestone is complete
only when its exit criteria are satisfied; running a larger model or producing
an interesting visualization does not advance the milestone by itself.

The [Order-Parameter-First Fundamental Frame](FUNDAMENTAL_FRAME.md) is the
current ontology for scientific objects and claim labels. The
[Experiment Interpretation Ledger](EXPERIMENT_INTERPRETATION_LEDGER.md)
preserves the temporal relation between that frame and earlier experiments.
Neither document changes a frozen protocol or observed artifact.

## 1. North star

SpiralLens should become a model-agnostic, auditable toolkit that keeps six
things separate:

1. an explicitly bound observation substrate;
2. an optional model-derived order parameter or section;
3. a geometric or transport observable;
4. invariance under declared nuisance transformations;
5. a topology claim;
6. a semantic or causal interpretation.

The library should let a researcher bind a substrate, define a field or remain
explicitly on the geometry branch, construct matched loops, estimate local
transport, account for known architectural factors, persist every decision
with provenance, run matched nulls, and promote a result only as far as its
evidence allows.

The motivating optical-vortex and OAM analogy is useful intuition. It is not an
assumption that transformer activations are physical optical fields.

## 2. Non-negotiable scientific boundaries

These rules apply to every milestone and release:

- A large drift is not automatically a phase shift.
- High cosine similarity plus divergent updates creates a structural candidate,
  not a verified vortex or semantic distinction.
- A field-unbound scalar such as anisotropy, effective rank, eigengap,
  projected norm, density, or coherence is a `SupportDiagnostic`, not an order
  parameter or core. It becomes a `CoreScore` only through an exact same-field
  singularity/identifiability binding.
- Amplitude and phase-like direction must arise from the same declared,
  substrate-bound field.
- A core is an independently defined singular or unresolved set, not the center
  selected after maximizing winding.
- Continuous holonomy and sampled winding remain separate types and claims.
- Sampled winding is the winding of the declared discrete interpolation; it is
  not a certificate for an unknown continuous field.
- Continuous Procrustes rotation is not quantized charge.
- Deterministic construction under one graph protocol is reproducibility, not
  graph-construction-family invariance.
- A topology claim requires matched cycle or homology support across every
  preregistered admissible graph family; unsupported comparisons are
  `insufficient` and supported disagreement is `fail_graph_dependence`.
- A core-facing degeneracy scalar must be derived from the same declared field,
  frozen before loop readout, and persisted with its nested-radius radial
  profile. A nearby support diagnostic is not a substitute.
- An architecture-accounted sampled-winding estimate distribution, including
  its unrounded cycle total and proximity-to-integer residual, is a diagnostic
  of clustering versus continuous spread. It emits no resolved charge label;
  proximity to integers is not evidence of quantization or charge by itself.
- Projected curl, UMAP/PCA geometry, and other projection-dependent quantities
  may rank exploratory candidates but are not promoted to physical invariants.
- Whitening or PCA may condition a distance calculation, but cannot by itself
  establish a closed loop or topology.
- “OAM” remains motivation; the implemented decomposition is named by the
  mathematical operation, such as `angular_spectrum`.
- Discovery cannot use semantic labels, SAE labels, or held-out answers.
- Architecture-factor removal yields an accounted residual, not an
  automatically semantic residual.
- The scientific observation unit is at least
  `model × revision × token/context × position × layer`; token ID alone is not
  treated as meaning.
- A swept ID denotes a model input embedding row. Even when that row is
  tokenizer-addressable, a fixed-context model-input-row activation atlas is
  not described as a language-space or semantic atlas.
- Zero-candidate and null results are valid completed outcomes.
- A qualified zero-candidate result states the frozen end-to-end sensitivity
  region in which no candidate was observed; it is not an unrestricted absence
  claim.
- Pythia-70M is plumbing and integration validation. Pythia-160M remains the
  historically intended first claim-bearing model family, but the Fundamental
  Frame does not authorize a subject run.

The [branched claim taxonomy](claim_ladder.md) remains authoritative for result
labels, and an individual experiment protocol remains authoritative for that
run’s thresholds and claim ceiling.

## 3. Two independent maturity axes

SpiralLens tracks scientific evidence and software maturity separately.

- **Scientific evidence:** analogy → Level 1G geometry or Level 1D defect-field
  observable → Level 2G invariant geometry or Level 2T topological-defect
  candidate → Level 3 semantic and causal evidence.
- **Software maturity:** research preview → experimental API → alpha → beta →
  stable library.

A scientific hypothesis may be rejected while the software still matures into
a valuable 1.0 library that reliably reproduces positive, negative, and
inconclusive outcomes. Conversely, an interesting Level 2G, Level 2T, or
Level 3 result does not make the API stable. Release versions describe
software contracts, not the truth of the motivating hypothesis.

## 4. What “library” means

SpiralLens is not considered a library merely because it is installable.
A library milestone requires:

- a small documented public API with typed contracts;
- model-specific behavior behind adapters;
- optional heavy dependencies rather than mandatory framework lock-in;
- deterministic examples that run without private data;
- versioned, validated, and migratable persisted artifacts;
- clear stable, provisional, and experimental API labels;
- supported Python and compute-backend matrices;
- bounded resource behavior and explicit failure modes;
- semantic versioning and a deprecation policy;
- reproducible releases, changelogs, and source provenance;
- contribution and security expectations suitable for a public project.

Until those conditions are met, SpiralLens is accurately described as an
experimental research package.

## 5. Target package boundaries

The current namespace layout is already close to the intended library shape.
The target is:

| Boundary | Responsibility | Dependency policy |
| --- | --- | --- |
| `core` | Stable-candidate canonical codecs and future framework-neutral status/error primitives | Standard library only; promotion still requires two independent consumers |
| `access` | Provisional provenance, consumer authorization, value lineage, pre-observation descriptors, and attempt lifecycle | Standard library plus `core`; never reads model values |
| `contracts`, `loops`, `holonomy`, `topology` | Framework-neutral mathematical types and operations | NumPy/SciPy only |
| `referents` | Provisional F0-F4 pointwise objects, transformation laws, fit/evaluation partitions, and same-object relations | NumPy plus contract enums; no substrate field or model-side existence claim |
| `instrument_contracts` | Provisional manifests, closed-world integrity, selected metadata joins, and a separately authorized strict numeric consumer | Ordinary loading remains opaque; numeric access is lineage-gated and subject roles are forbidden |
| `synthetic` | Model-free construction-family identities, development generators, separated truth controls, numeric self-audit, and bounded bundle publication | Experimental core; no calibration selection or subject execution |
| `graphs` and future order-parameter boundaries | Provisional exact graph/domain fingerprints now; later field artifacts, core diagnostics, and qualification gates | NumPy-only in-memory foundation; persistence and scientific promotion remain future work |
| `qualification` | Experimental D0-D5 protocol, source/evidence roots, separate core and continuous sampled-loop kernels, crossed aggregation, one-attempt terminal chronology, scope-limited D6 admission, and internal D7 design/prediction/rebinding/replay-contract foundations | NumPy/PyYAML plus project contract foundations; C1 records the atomic Level-0 seed-free design, static-bounded declared diversity review, registry/aggregation application, review contract, and declared source set; committed C2 verifies that historical Git source set only; canonical unpersisted D7 replay-target and append-only attempt-envelope specifications define later contracts without creating official instances; deep-internal record, payload, and structural-join layers, a no-replace caller-supplied prefix evidence lane, and a non-authorizing authority-prerequisite input candidate partially complete step 18, while live verification, target authority, witness verification, official instances, freeze, admission, seeds, fused exclusive start, terminal publication, runner, replay, and D7/D8 authority remain absent; exact current execution-source/runtime closure is deferred until the operational surfaces are final |
| `calibration` | Analytic positive controls, negative controls, and instrument qualification | Core only |
| `metrics`, `gauge`, `nulls` | Structural observables, alignment, and matched controls | Core by default |
| `adapters` | Pythia, Hugging Face, and future model-family capture | Optional model extras |
| `atlas` | Streaming observation storage, integrity journals, and replay | Optional model extras for capture; reader should trend lighter |
| `jacobians`, `factors` | JVP and architecture-component accounting | Core analytic paths plus optional autodiff |
| `interventions` | Explicitly scoped activation interventions | Optional model extras |
| `semantics` | Post-discovery annotation and held-out evaluation | Never imported by discovery |
| `protocols` | Human-reviewable experiment declarations | Data, not hidden defaults |
| `benchmarks` | External comparison systems | Never imported by the core package |

TransformerLens or any other hook framework may become an adapter, but must not
define the core mathematical API or artifact schema.

## 6. Milestones

### M0 — Auditable instrument foundation

**Status:** implemented; hardening continues.

Delivered by C7, plus the explicitly marked post-C7 outcome addendum:

- analytic rotation, winding, stretch, radial, shear, basis, reverse,
  off-core, nested-radius, and sampling-alias controls;
- separate continuous-holonomy and sampled-winding contracts;
- Hugging Face Pythia observation adapter;
- memory-mapped activation atlas with atomic manifests;
- immutable model revision and capture-runtime provenance;
- per-batch slice hashes, whole-file hashes, and fail-closed resume;
- structural candidate ledger with no semantic or SAE input;
- protocol ID, status, SHA-256, claim ceiling, and override provenance;
- a state-only neighbor-backend contract, lexicographically deterministic exact
  reference, and shared float64 exact reranker;
- candidate-boundary recall/determinism audit artifacts with fail-closed
  `pass`, `fail`, and `insufficient` outcomes;
- a standalone frozen query-local, relative-density, cosine-boundary, and
  worst-case recall methodology, separate from any Pythia audit outcome;
- a pinned, selected-but-unpromoted Faiss HNSW range-search backend with
  full-index/subset-query audit receipts and strict ledger replay;
- a versioned one-query native range-call path, a tracked
  subject-independent production-shape two-cold-process qualification receipt,
  and a fresh-subprocess consumer-validation contract;
- post-C7 outcome addendum: one frozen consumer-safe Pythia-70M
  full-index/subset-query audit ended terminal `insufficient` with zero
  exact-reference support and issued no promotion receipt;
- CLI commands for calibration, atlas capture, neighbor-audit preparation and
  execution, native range preflight, and candidate extraction.

Historical exit criteria, preserved from the C7 roadmap:

- all analytic controls pass;
- storage corruption and incompatible resume are rejected;
- a real Pythia-70M bounded smoke completes offline;
- a zero-candidate run completes normally;
- no current artifact is described above Claim Level 1.

Post-C7 interpretation mapping, not a historical exit criterion:

- no M0 artifact exceeds the current Level 1G or Level 1D ceilings;
- no real-model defect field reaches Level 1D.

What M0 does **not** prove:

- that a Pythia representation contains a closed semantic loop;
- that any candidate has non-zero relative holonomy;
- that sampled winding reflects continuous topology;
- that a model-derived order parameter or core has been defined;
- that a scalar support diagnostic supplies phase or quantized charge;
- that one deterministic graph construction is topology-invariant;
- that SAE reconstruction removes the hypothesized information.

### M1 — Field qualification and candidate-to-loop integration

**Status:** in progress. Observation, ContextBank, retrieval, qualification,
and recall-gate machinery exist. The first frozen consumer-safe Pythia-70M
retrieval audit ended `insufficient` and did not promote the backend. The P0
registry, provisional artifact schemas, and closed-integrity bundle validator
are implemented. A first bounded P1 instrument-development generator now
emits paired representation-shaped positive/null substrates through F0/F1/F2,
with a model-free `SyntheticLatticeContextBinding`, no indexed ContextBank or
model/tokenizer binding, an exact
`instrument_dev_executed` mutual-kNN/Euclidean/\(k=6\) cell, durable
non-qualification and resource receipts, source-commit/blob binding,
current-environment byte-identical cold replay, and canonical closed-bundle
publication. The conservative resource preflight uses a versioned estimator,
safety factor four, and 256 MiB estimated peak/output caps; it guards
parameter-induced runaway allocation and is not an operating-system OOM
guarantee.

The P1 publisher validates a private staged tree and exposes the complete
directory through one Darwin-only atomic, exclusive, no-replace namespace
transition. Unsupported environments fail closed. This is namespace
atomicity, not crash durability. The slice is one generator family and does
not calibration-select or qualify an estimator or graph family, run D0-D8, or
satisfy graph-family qualification. Cycle construction is `not_run`; its empty
cycle-support payload means “not supplied,” not “observed cycleless.”

A separate experimental qualification slice now implements the closed
model-free D0-D5 **engine** without changing that P1 bundle's status. It adds a
Cartesian Fourier construction beside the representation construction,
separate charge-blind core and continuous sampled-loop kernels, the full
field-graph A by cycle-graph B by loop-role matrix, a field-sensitivity
effect-size sentinel, exact boundary/state-geometry-warp/structured-
observation-perturbation strata, complete source/evidence roots, and canonical
result persistence. The protocol records paired repeated-measures semantics
and gate-specific positive claim scopes; its 64 execution variants are not
declared independent replicates, and D2 collapses the two boundary repeats to
32 exact-agreement scientific input units. The engine emits only unrounded
integrated sampled-phase totals; integer output and topology claims remain
disabled.

Attempted D1 evidence is not accepted from its persisted hash tree alone.
Every result validation closes each metric to one comparator and one frozen
threshold field, re-executes the Cartesian and representation D1 families on
their fixed development seed under the current source-bound engine, and
requires exact canonical-byte equality with both persisted family receipts.
This rerun never consumes selection seeds. It is a local deterministic
cross-check, not cryptographic source proof or independent/native-runtime
attestation.

The lane is not a P0-wide competition. Cartesian D2-D5 evidence does not
qualify or select the representation estimator merely because that estimator
passes fixed-seed D1/D3 checks. PR #9 protocol/result bytes keep P0 winner
selection, representation D2-D5 transfer, and a localized core-loop join
explicitly false. A later D6 transition must first supply
representation-native D2-D5 evidence or a reviewed construct-equivalence
bridge.

The frozen official selection outcome now exists. It was not opened by engine
tests or documentation: its claim-bearing attempt followed, in order,
the committed engine; the exact canonical readiness, protocol, and unopened
freeze committed as F; a canonical launch intent persisted before one
exclusive attempt claim; the store freeze, intent, claim, and descriptor
committed as G; fresh descriptor-derived authorization of all four clean
tracked G artifacts; live revalidation at the official runner entrance; one
atomic execution-start transition binding the authorization digest and G HEAD
before generation; and one atomic terminal publication containing either the
result or a typed failure whose authorization digest matches the start, with
its consumption receipt and manifest. Terminal publication/reload also require
the typed authorization, exact unchanged G blobs, absence of start/terminal at
G, and `engine -> G -> current` ancestry. Negative-access facts are external
attestations, and the current local uniqueness history trusts store deletion
rights. D6-D8 remain unadvanced and every D0-D5 result keeps
`synthetic_qualified=false`. The pre-run freeze is not the later D6
scope-limited advancement decision.

The ordinary successor-aware terminal validator preserves the execution
receipt across the later artifact commit required by this roadmap. It accepts
only an exact descendant history, verifies bound blobs at the stored execution
HEAD and current HEAD, reconstructs the historical receipt, and requires its
unchanged canonical digest. The separate D6 archival loader verifies clean
tracked G/H history and serialized companion joins without current D1
recomputation; it explicitly grants neither current-engine compatibility nor
historical reexecution. Neither route collapses execution HEAD and artifact
HEAD or grants runtime/hostile-mutation attestation.

**Target release family:** `0.2.x`.

Deliverables:

1. `ObservationKey` and `ContextBank` contracts that make model revision,
   context, token position, layer, and capture stage explicit.
2. A tracked public context bank containing 6–12 project-authored synthetic
   engineering fixtures. Every context has `role=example` and
   `claim_eligible=false`; the bank tests loading, validation, capture, and
   replay only.
3. Discovery and held-out roles are rejected from that public engineering
   bank. Scientific discovery and held-out banks begin in M2 as separate frozen
   artifacts.
4. Atlas requests bind the bank's source and canonical digests, selected role,
   ordered context IDs, sweep/observation positions, and sweep domain. Resume
   rejects any mismatch before appending an attempt. The binding embeds
   canonical bank content so load/replay can recompute bank, selected-context,
   tokenizer, and request-identity digests independently.
5. Atlas manifests persist `language_space_atlas=false`,
   `semantic_unit=false`; decoded strings, when present downstream, are
   display-only sidecars rather than observation identity. Candidate references
   carry the bound bank/context/spec identities and tokenizer-addressability
   flag rather than aggregating by decoded text.
6. A neighbor-search protocol suitable for the full 50,304-row Pythia model
   input embedding table.
7. An exact reference backend for bounded datasets and an audited approximate
   backend for full-vocabulary discovery.
8. Recall and determinism evaluation of the approximate backend against exact
   subsets; the initial recall target is at least 0.99 at the preregistered
   candidate boundary.
   Promotion also requires the frozen query-local, relative-density,
   density-by-cosine-boundary, and worst-case coverage gates; aggregate recall
   alone is not sufficient. Freezing those measurement rules is not a Pythia
   audit result.
9. Approximate search is used only for retrieval; every persisted candidate is
   reranked and gated with the exact metric.
10. Experimental `SubstrateBinding`, `SupportDiagnostic`,
    `GeometricFieldEstimate`, `CoreScore`, `OrderParameterSpec`,
    `OrderParameterField`, `CoreCandidate`, and `GroundTruthAnchor` contracts
    qualified on synthetic representation-shaped phantoms before any new
    subject protocol.
11. Competing field hypotheses with explicit transformation laws, fit scopes,
    claim ceilings, and no outcome-selected winner.
12. Semantics-free, deterministic mutual-kNN, fixed-radius, and
    shared-neighbor candidate graph families with canonical construction
    receipts.
13. Deterministic cycle construction plus a matched support or homology rule
    that remains meaningful across genuinely different graph-construction
    families and compares the same enclosing support/class rather than
    construction-specific cycle indices.
14. A full crossed field-estimation-graph by cycle-construction-graph null,
    extended by a core-estimation-graph axis whenever the core estimator is
    neither graph-free nor bound to the field graph, with graph diversity,
    support, and worst-case gates.
15. Local transport estimation using declared JVP, pullback metric, whitening,
    projector, and/or Procrustes choices.
16. Relative holonomy rather than raw endpoint drift on the geometry branch.
17. Sampled winding only from an eligible, nonzero, orientable
    order-parameter section on the defect branch with a frozen
    trivialization/reference or gauge-invariant connection-corrected lift.
18. RoPE, LayerNorm, attention value, attention routing, MLP, basis,
    orientation, radius, sampling-density, graph-family, and matched-null
    controls wired into one run artifact.
19. Each required gate is persisted as `pass`, `fail`, `insufficient`, or
    `not_run`; incomplete gates cannot silently pass.
20. Versioned substrate, field, graph, discriminated geometry/defect loop, and
    result artifacts linking every result back to atlas rows, fit scopes, and
    protocol hashes.
21. A charge-blind `CoreScore`/`CoreCandidate` receipt bound to the same
    order-parameter field and frozen before loop readout, kept distinct from a
    supplied `GroundTruthAnchor`, with known-core, off-core, density, and
    sparse-support controls. Its D2-only falsifier matrix distinguishes a
    high-amplitude local-identifiability-loss decoy from a localized
    same-section low-amplitude candidate and requires independent measurement
    support at the candidate itself. The current engine binds the core input
    to the inherited field-estimation graph and keeps this Level-0 candidate
    below any vortex, topology, charge, or core-loop-join claim.
22. Attempted, evaluable, insufficient, and abstention counts plus worst-case
    coverage, recall, and specificity gates across required phantom strata.
23. A content-addressed `CalibrationSelectionDecision` sealed before hidden
    confirmation, followed by a non-selecting
    `CalibrationConfirmationResult`.
24. A future `SubjectProtocolManifest` and access boundary that reveal no
    subject-derived values before separate review, freeze, and execution
    authorization.
25. A protocol-declared same-field core-degeneracy scalar recorded at every
    candidate and as a nested-radius radial profile. Its threshold and matching
    rule are frozen before any loop value is read.
26. An architecture-accounted sampled-winding estimate distribution across the
    eligible loop ensemble, retaining every unrounded cycle total and
    proximity-to-integer residual and comparing them with continuous and
    integer-clustered calibration controls. This is a non-quantization
    diagnostic, emits no resolved charge label, and is never a charge
    certificate by itself.
27. An opposite-sign dipole phantom with a separation sweep, single-core loop
    signs, both-core-loop additivity/net-zero checks, and explicit two-core
    resolution. It also calibrates the measurement needed by any future
    checkpoint-series annihilation analysis.
28. An end-to-end detection-limit surface over injection amplitude, declared
    perturbation or noise level, and sampling density. Synthetic fields must
    enter through the atlas representation and traverse ANN retrieval, exact
    reranking, graph construction, cycle construction, and the final gates.
    Exact-recall audits are stratified by local-density and candidate-boundary
    cells because exact reranking cannot recover neighbors the ANN never
    retrieved.
29. A bounded qualification transition rule fixed before further tuning. Each
    protocol declares its maximum revision/resource budget and a terminal
    action: advance to M2 when the finite gates pass, or stop with a persisted
    `insufficient` qualification record when the budget is exhausted.

Exit criteria:

- a full-vocabulary Pythia-70M atlas completes for every declared fixed
  context/position slice under a recorded resource budget;
- the tracked public example bank validates with all roles equal to `example`
  and with claim eligibility disabled;
- approximate discovery meets its preregistered recall target on exact subsets;
- the end-to-end detection-limit surface is frozen and complete before M2 or
  any Pythia-160M run; it reports detection probability and uncertainty over
  injection amplitude, declared perturbation/noise, and sampling density, with
  density-stratified exact-recall and worst-case gates;
- a locked independent synthetic calibration qualifies the selected
  instrument bundle before subject `prepare-only`;
- the calibration-selection artifact freezes advanced hypotheses, required
  cells, thresholds, coverage, abstention, and aggregation before hidden
  confirmation;
- every required stratum meets its worst-case coverage and specificity gates
  without converting adverse cases into selective `insufficient` outcomes;
- all required graph families are deterministic, genuinely distinct, and
  supported;
- the crossed graph-family matrix passes on known positives and rejects
  pure-gauge, shuffled, and rewired negatives, including the core-graph axis
  when present;
- loop construction is deterministic from the frozen protocol and run ID, and
  topology comparisons bind a matched class rather than a cycle-basis index;
- injected-rotation positives survive while pure-gauge/stretch/shear negatives
  are rejected;
- the opposite-sign dipole sweep resolves both cores in its declared regime,
  recovers their individual signs, and satisfies the frozen outer-loop
  additivity/net-zero control;
- each shortlisted real-model loop has matched reverse, radius, sampling, and
  architecture-accounted controls;
- every Level 1D result binds a replayable order-parameter field and an
  explicit singular-set/core status; every localized-defect result binds an
  independently inferred `CoreCandidate` to that same field, its persisted
  core-degeneracy scalar, and its nested-radius radial profile;
- any sampled-winding population summary preserves its unrounded cycle totals,
  proximity-to-integer residuals, architecture accounting, and calibration
  comparison, emits no resolved charge label, and remains explicitly
  non-evidence for quantized charge;
- supplied phantom anchors qualify conditional loop mathematics only and do
  not satisfy core-localization criteria;
- every local-frame integer binds its field, connection, interpolation, and
  trivialization/reference convention;
- subject `prepare-only` reveals no activation, graph, support, eigenspectrum,
  core, or candidate value;
- rerunning from persisted atlas data requires no model download or inference;
- Level 2G and Level 2T are promoted independently and only after every
  branch-specific control is complete.

Pythia-70M may exercise this path before qualification only as a
claim-ineligible plumbing run. It cannot satisfy the detection-limit exit
criterion or authorize M2.

### M2 — Frozen Pythia-160M scientific protocol

**Status:** blocked on M1 by design.

**Target release family:** `0.3.x`.

Deliverables:

- separate frozen discovery and held-out context-bank artifacts; a loader or
  run cannot silently mix their roles;
- split assignment grouped by `family_id`, `source_id`, and `template_id`, so
  exact or near-copy templates cannot cross discovery and held-out boundaries;
- any learned preprocessing is fit on analytic calibration and discovery data
  only, then frozen before held-out observation;
- immutable Pythia-160M model revision and capture contract;
- thresholds fixed from analytic controls, not tuned on Pythia-160M outcomes;
- Pythia-70M outcomes may qualify plumbing but cannot select or tune
  Pythia-160M confirmatory contexts, split membership, thresholds, exclusions,
  or learned preprocessing;
- a preregistered resource budget, null family, stopping rule, and claim ceiling;
- a signed annotated freeze tag plus an independently timestamped,
  content-addressed snapshot of the exact protocol and instrument source
  (a DOI-bearing archive such as Zenodo, or an equivalent immutable timestamp
  service), with both references bound into the run manifest;
- complete offline replay artifacts;
- a concise result report that treats positive, zero, and null outcomes
  equally; a zero-candidate report names the M1-qualified detectable region
  rather than claiming unrestricted absence.

Exit criteria:

- one clean protocol run without post-hoc discovery-threshold changes;
- the signed tag and independent snapshot resolve to the exact protocol and
  source digests before claim-bearing subject access. If the independent
  witness is unavailable, a plumbing-only attempt may record that absence, but
  the M2 claim-bearing run remains blocked;
- every reported candidate links to all required null results;
- an independent rerun reproduces the persisted structural quantities within
  declared numerical tolerances;
- any Level 2G or Level 2T label is earned per candidate, not inherited from
  the run.

Passing M2 does not establish semantics or SAE loss.

### M3 — SAE gap and causal semantic validation

**Status:** future research milestone.

**Target release family:** `0.4.x`.

Deliverables:

- frozen SAE choice, reconstruction definition, and comparison layer;
- raw-residual versus SAE-reconstruction transport measurements at matched
  points;
- a PCA-\(k\) compression comparator chosen to match SAE reconstruction MSE,
  with its fit partition and \(k\)-selection rule frozen before held-out
  evaluation;
- held-out semantic minimal pairs added only after structural discovery;
- norm-preserving cyclic-mode interventions and matched sham interventions;
- selective downstream behavioral endpoints;
- checkpoint and seed replication where models and SAEs permit it.

Exit criteria:

- a preregistered structural quantity predicts held-out contrasts;
- the result is not explained by norm, token frequency, position, RoPE,
  routing, or reconstruction-error magnitude alone; survival under matched-MSE
  PCA-\(k\) but loss under SAE is reported as basis-specific evidence, while
  loss under both remains generic compression sensitivity;
- intervention direction and dose predict selective downstream changes;
- sham, random-subspace, and reverse interventions fail as expected;
- the effect replicates across declared contexts and at least one independent
  model checkpoint or seed.

Only this milestone can support a Level 3 result.

### M4 — Replication and model abstraction

**Target release family:** `0.5.x`.

Deliverables:

- a model-observer adapter protocol independent of Hugging Face class names;
- a second model family in addition to Pythia/GPT-NeoX;
- checkpoint, seed, or scale replication where public models permit it;
- a preregistered public-checkpoint series that treats training step as a
  prospective control variable for candidate density and opposite-sign pair
  trajectories. Layer depth remains a within-model spatial/profile coordinate,
  not a temperature proxy; no Kosterlitz-Thouless or annihilation claim follows
  without the calibrated dipole resolution and branch-specific gates;
- core mathematical imports that remain free of Torch/Transformers;
- adapter conformance tests using the same phantom and artifact contracts;
- explicit measurement of adapter-induced observable differences.

Exit criteria:

- at least two independent adapter implementations pass the same conformance
  suite;
- the core package installs and imports without a model framework;
- model-specific hook names do not enter stable mathematical contracts;
- a negative or inconclusive replication remains a first-class artifact.

### M5 — Library alpha

**Target release family:** `0.8.x`.

Deliverables:

- an explicitly enumerated public API;
- provisional APIs moved under an experimental namespace or marked clearly;
- adapter protocols independent of Hugging Face class names;
- reader APIs that do not require model frameworks when technically feasible;
- schema migration tools for supported artifact versions;
- deterministic tutorial datasets and end-to-end examples;
- built-in protocol resources included in wheels and loaded without relying on
  a repository-relative path;
- benchmark fixtures for speed, memory, and numerical stability;
- API reference and architecture documentation;
- Python 3.11–3.13 CI on the supported core platforms.

Exit criteria:

- a new user can install the core and complete calibration without PyTorch;
- a model user can install one documented extra and reproduce an atlas example;
- artifact readers reject unsupported schemas with a migration path;
- public functions have types, examples, failure semantics, and tests;
- package imports do not trigger model downloads, network access, or telemetry.

### M6 — Library beta

**Target release family:** `0.9.x`.

Deliverables:

- a documented plugin/adapter registration mechanism;
- audited full-vocabulary search backends with explicit accuracy/resource
  tradeoffs;
- CPU, MPS, and CUDA compatibility matrix;
- documentation site, tutorials, and troubleshooting guides;
- a contributor guide, issue templates, changelog, and release checklist;
- supply-chain checks, dependency review, and generated software bill of
  materials for releases;
- performance regression budgets;
- at least one adapter beyond Pythia/GPT-NeoX without core API changes.

Exit criteria:

- external users can implement an adapter from documentation alone;
- two consecutive minor releases avoid unplanned public-API breaks;
- persisted artifacts survive documented upgrades;
- full examples are reproducible in clean environments;
- known numerical/backend differences are documented and tested.

### M7 — Stable library 1.0

Deliverables and release gates:

- semantic-versioning commitment for the public API;
- documented minimum deprecation window;
- stable artifact schema policy and supported migrations;
- signed, reproducible PyPI and GitHub releases;
- complete license and third-party attribution review;
- stable CLI exit codes and machine-readable output contracts;
- supported Python/backend matrix with CI;
- security policy and private vulnerability-reporting path;
- governance for maintainers, reviews, RFCs, and experimental promotion;
- published scientific limitations and non-claims.

`1.0.0` is justified only when downstream code can depend on SpiralLens without
depending on repository internals or a particular research experiment.

## 7. API maturity policy

Before 1.0:

- artifact schemas are always versioned and fail closed;
- public symbols may change between minor versions, with migration notes;
- functions used only by one experiment remain internal or experimental;
- a symbol is promoted only after two independent consumers, full tests, and
  user-facing documentation;
- scientific claim labels are data in artifacts, not inferred from function
  names.

At 1.0:

- patch releases are backward compatible;
- minor releases add compatible behavior;
- breaking API or artifact changes require a major release;
- deprecated interfaces remain for a documented transition window.

## 8. Artifact and reproducibility policy

Every claim-bearing artifact should bind:

- package and schema versions;
- source revision or release;
- model ID and immutable model revision;
- effective compute backend, dtype, and framework versions;
- protocol bytes and SHA-256;
- context-bank and token-selection digests;
- thresholds and all exploratory overrides;
- progress journal and integrity hashes;
- claim level and unmet promotion gates.

Generated model weights, credentials, private prompts, and large activation
arrays are not committed to Git. Small synthetic fixtures may be committed when
their provenance and license are clear.

Context banks have an additional leakage boundary:

- public M1 fixtures remain `role=example` and `claim_eligible=false`;
- discovery and held-out contexts live in separate frozen M2 artifacts;
- split assignment groups related items by family, source, and template rather
  than assigning individual rows independently;
- learned transforms are fit only on calibration/discovery data and are frozen
  before held-out evaluation;
- results observed on Pythia-70M cannot be used to tune the Pythia-160M
  confirmatory bank.

## 9. Contribution and decision model

During the research phase, decisions that alter persisted meaning should be
recorded before implementation. High-impact examples include:

- changing the scientific observation unit;
- changing a schema’s interpretation;
- promoting an approximate search backend;
- changing a claim-level gate;
- allowing semantic information into discovery;
- changing stable API or deprecation policy.

The intended long-term mechanism is a lightweight RFC or architecture-decision
record reviewed in public. Until that structure lands, the Fundamental Frame
controls current ontology, the Interpretation Ledger records temporal
decisions, this roadmap controls sequencing, the claim taxonomy controls
labels, and tracked protocols control individual executions. None can rewrite
an earlier artifact.

Contributions submitted to the project are accepted under Apache-2.0 unless
explicitly stated otherwise.

## 10. Known risks

| Risk | Required response |
| --- | --- |
| Optical language outruns the observable | Persist mathematically named quantities and explicit non-claims |
| Geometry is promoted without a substrate referent | Keep geometry on Level 1G/2G unless a separate field/defect contract exists |
| A scalar diagnostic is laundered into an order parameter | Persist it as `SupportDiagnostic`; permit `CoreScore` only with an exact same-field singularity rule |
| A core is selected from the observed winding | Localize singular support independently and freeze the matching rule before charge evaluation |
| One deterministic graph is mistaken for topology | Require genuinely distinct graph families and the full crossed construction null |
| Integer rounding is mistaken for quantization | Bind target topology, amplitude/identifiability, branch margin, matched class, and deformation stability |
| Projection artifacts look like vortices | Require ambient-space or gauge-accounted controls |
| Full-vocabulary search becomes intractable | Keep exact reference subsets and audit approximate recall |
| Backend differences create false candidates | Bind backend/runtime/index bytes, require verified receipts, and test repeatability before promotion |
| Aggregate ANN recall hides a local collapse | Bind the frozen query-local, density-by-boundary, and worst-case methodology into each atlas-specific execution before enabling promotion |
| Exact reranking hides ANN false negatives | Qualify the complete atlas-to-cycle path with a density-stratified detection-limit surface; never infer sensitivity from persisted-candidate precision alone |
| Resume blesses corrupted partial data | Verify committed batch hashes before writing a new attempt |
| Semantic labels leak into discovery | Separate modules, artifacts, and dataset splits |
| Interesting Pythia-70M result drives confirmatory-bank tuning | Keep 70M as plumbing; freeze 160M contexts, splits, thresholds, and preprocessing independently of its outcomes |
| Research API ossifies too early | Stabilize only independently reused, documented contracts |
| Library engineering dilutes scientific falsifiability | Require the same claim ladder through every release |
| Instrument refinement indefinitely postpones a claim-bearing run | Freeze a finite M1 revision/resource budget and transition rule; advance when all gates pass, stop `insufficient` when qualification does not, and treat an M2 zero-candidate run as a qualified null only inside the calibrated sensitivity region |
| A caller record or serialized token masquerades as launch authority | Treat canonical bytes as inputs only; derive authority inside one fused verify-and-exclusive-start operation, emit no reusable capability, and reobserve exact runtime, physical identity, and absence at the transition |

## 11. Immediate next plan

The original sequence completed the ContextBank, atlas, neighbor-backend,
recall-gate, producer-qualification, and consumer-safe execution machinery. Its
first frozen v0.4 Pythia-70M full-index/subset-query audit ended terminal
`insufficient`: all 1,000 selected queries had zero exact-reference support, so
recall was not estimable and no promotion receipt was issued. The exact
historical reading is preserved in the
[Interpretation Ledger](EXPERIMENT_INTERPRETATION_LEDGER.md).

That outcome remains a terminal retrieval-only result. Separately, a
post-outcome conceptual review established prospective gates for a new
Level-0 order-parameter question. No inference from the audit status or empty
support selected the field hypotheses, graph families, or calibration rules
below:

1. adopt and review the Fundamental Frame, branched claim taxonomy, and
   historical interpretation ledger;
2. register competing field hypotheses F0–F4 with transformation laws, fit
   scopes, and claim ceilings — implemented as the strict, outcome-excluded P0
   registry;
3. define canonical substrate, graph, support, geometry-field,
   order-parameter, connection, discriminated loop, and calibration artifacts
   — implemented as metadata-only experimental v0.1 schemas;
4. define a canonical closed-world bundle manifest, resolve exact artifact and
   payload closure, and validate selected cross-manifest metadata joins —
   implemented as a closed-integrity validator that streams opaque payload
   bytes only for length and SHA-256 verification;
5. add a separately constructed Cartesian Fourier family with the exact
   nonzero-with-core, null-with-core, null-without-core, and
   prerequisite-failure controls — implemented in the D0-D5 engine;
6. consume deterministic mutual-kNN, fixed-radius, and shared-neighbor
   constructors through distinct field/cycle axes on the exact discrete
   domain — implemented for the closed selection engine;
7. implement separate core-only and loop-only evidence paths, execute the full
   field-graph by cycle-graph by loop-role matrix, and require a substantive
   field-output effect-size sentinel — implemented without integer or topology
   authority;
8. freeze nonnumeric failure semantics, exact required stress strata,
   all-primary pass, coverage/abstention/recall/specificity, source/evidence
   roots, and one-attempt terminal chronology — implemented at the engine and
   schema level;
9. commit that engine; commit exact canonical readiness/protocol/freeze
   artifacts as F; persist a launch intent before one exclusive claim; commit
   the store freeze, intent, claim, and descriptor as G; derive and revalidate
   exact G authorization; then perform the live source verification and atomic
   execution-start transition, the one-shot D0-D5 selection, and atomic
   publication of either its fully validated result or typed failure —
   completed with all six Cartesian-surrogate-scoped gates passing;
10. seal the exact surrogate profile and a construction-diverse confirmation
    admission contract before any confirmation access — implemented as the
    scope-limited D6 decision with canonical SHA-256
    `c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07`;
    its clean tracked reload passed and now binds the clean current loader
    source surface to one stable HEAD without claiming historical-source
    compatibility, but it does not select the representation instrument or
    advance global D6-D8; preserve its source-commit ancestry with a merge
    commit because squash/rebase integration invalidates the authoritative
    lineage, and treat its absolute-path end-to-end reload as local archival
    evidence rather than a cross-worktree test;
11. freeze post-selection descriptive analysis separately from the value-blind
    D7 structural gap matrix — recorded as two canonical, non-authorizing
    research artifacts; the descriptive lane cannot tune D7, and the gap lane
    cannot read the terminal values, name a candidate, or compute progress;
12. land the spectral-moment draft foundation: exact four-case development
    generation plus a closed typed draft reconstructed only from the
    authoritative committed-D6 loader receipt. Its current internal `v0.2`
    identity, now preserved as a canonical historical body inside C1, excludes
    validation-time current-loader HEAD/digest fields while retaining typed
    receipt validation, so unchanged inputs are commit-stable. The draft
    remains unpersisted as a standalone/public artifact. This is not a D7
    full-design freeze: it does not
    complete same-schema construction-diversity review, selects no
    confirmation seed or execution inventory, persists no receipt, admits no
    family, exposes no runner/result, and leaves D7/D8 `not_run`;
13. close the seed-free D7 execution topology before choosing official seeds:
    reconstruct the full authoritative parent protocol; translate all three
    stresses explicitly; generate the exact 64-primary, 192-core, and
    1,152-loop seed-slot inventory; and exercise the exact crossed
    graph/field/blind-core/continuous-loop path on permanently excluded
    development seeds without producing a gate, result, or terminal —
    implemented. This step also records the newly discovered D6 v0.1
    incompatibility: required cells and stress-strata bodies contain selection
    seeds and seed-bearing IDs, so structural projection equality is true
    while exact parent-manifest satisfaction and admission remain false;
14. encode a proposed successor-only fulfillment rule without rewriting D6:
    graph-axis and threshold bodies remain exact, while cells/stress receive
    distinct successor identities whose structural projections match —
    implemented as an internal `v0.1` factory and strict reader. The historical
    proposal remains unreviewed and ineffective for admission; C1 preserves it
    unchanged and separately encodes the successor review contract without a
    repository-review attestation. Historical D6 v0.1 exact admission remains
    false;
15. create **C1**, the atomic and strictly reloadable stable seed-free
    candidate — completed at
    `experiments/qualification/d7_spectral_moment_confirmation_v0_1/c1-seed-free-source-set.json`.
    It binds the design, declared static-bounded construction-diversity review,
    D7 implementation registry, aggregation application, successor review
    contract, and complete declared `src/spirallens/**/*.py` plus
    `pyproject.toml` source set. It deliberately embeds no future commit,
    repository-review attestation, C2 receipt, official seed, admission, or
    execution authority; declared source set is not declared Git source-set
    closure;
16. create **C2** as the unique receipt-only child of the exact clean
    post-merge C1 commit — completed. C2 binds
    `e58a8169b41be688628ab7dda583e68088d3affc`; its unique
    receipt-introduction commit is
    `2f4e715a951211af8ca0ca4f6b2f7473134bf92b`. The committed loader verifies
    ancestry and every declared C1 source blob. C2 does not execute historical
    code or attest Python/native runtime, transitive dependencies, in-process
    identity, hostile-local-mutation resistance, or current compatibility;
17. only after C2, first define the immutable replay target independently from
    the launch/claim/start/outcome attempt envelope — implemented at the
    contract-specification level by the canonical, unpersisted
    `D7ReplayTargetContractSpec` and `D7AttemptEnvelopeContractSpec`. Neither is
    a replay-target or attempt instance. The latter fixes an append-only
    declaration → authorization → exclusive claim → start →
    scientific-result-or-failed-attempt → manifest → consumption model,
    rather than one mutable nullable object. The future target is exactly
    Level 0 with an all-false local authority vector. Do not create a
    placeholder result to stand in for any of these objects;
18. expose the concrete inputs needed by the later operational boundary
    without constructing authority — **partially complete through the
    deep-internal append-only prefix evidence store and PR #23
    non-authorizing structural candidate**.
    Closed canonical declaration, authorization, claim, start, outcome,
    manifest, and consumption schemas plus pure structural joins are
    implemented without creating an official instance. A separate
    persistence-only module now atomically publishes and strictly reloads a
    caller-supplied primary declaration, authorization record, claim record,
    and start record beneath an immutable false-authority store scope and four
    chained envelopes in a dedicated evidence-only namespace. Raw lifecycle
    records are not top-level files and in-place promotion is prohibited.
    Authorization and start evidence reobserve their declared parent
    device/inode and absent output/terminal leaves; the four receipts are
    content-addressed. Native exclusive rename is required and unsupported
    platforms fail closed.
    The hash dependency is acyclic: the manifest binds the typed outcome, and
    consumption binds the manifest. Scientific `pass`, `fail`, and
    `insufficient` remain results; infrastructure failure is separate and
    cannot be used to reclassify a scientific outcome. The future
    authoritative start binds an external execution identity, and an
    authoritative start without terminal remains `started_unresolved` unless a
    later verifier establishes a witness for that exact start and identity.
    The current caller-supplied start record plus terminal absence is only
    `caller_supplied_start_record_present_terminal_absent`; every terminal
    entry is `terminal_path_present_unverified`. It establishes neither
    execution nor `started_unresolved`, and isolated replay is rejected before
    persistence. Authoritative target/attempt instances,
    terminal publication, witness verification, finalization, execution
    capability, runner, and replay comparison remain deferred. The separately
    reviewed canonical payload slice is now
    implemented: D7-specific wrappers reuse the core/loop and reviewed stratum
    row validators inside new enclosing schemas, while event-lane, joined
    primary-unit, and four-state gate rows remain D7-specific. Pure validators
    close all six component bytes through 1,344 event lanes, 64 cell-derived
    primaries, six strata, gate summary, and outer result bindings. Canonical
    authorization/pre-start path-absence receipts, failure payloads, and
    external-abort receipts are also structurally joined to the attempt
    records. This does not load the target or gate manifest, observe a
    target or gate authority, authenticate a witness, reserve a destination,
    authorize a finalizer, or prove hostile-process
    TOCTOU/post-publication inode safety. The local prefix writer's path
    reobservation grants no scientific or execution authority. Those
    operational producers and authorities must be added before any
    structurally valid caller bytes are treated as verified evidence.
    PR #23 additionally gives canonical structure to a concrete subset of
    later prerequisites. Its replay-target record uses dedicated
    caller-claimed admission, exact-full-design, and exact-source/runtime
    candidate leaves, all with `identity_authenticated=false`. A typed
    exclusive-supply claim causally joins the supplier, development and parent
    registries, readiness, and caller-alleged admission and source/runtime
    receipts; a typed single invocation rejoins that claim and supplier to the
    official inventory and atomic inventory/full-design/target publication.
    Claim, invocation, chronology, inventory-output, and publication
    verification remain false. The physical input carries the exact attempt
    key derived from the target and fixed primary role, normalized paths,
    positive store/lane/parent device/inode identities, a distinct store/lane
    identity requirement, and lexical plus known-physical-alias
    persistence-reserved path exclusions. The artifact binding has no raw
    `from_bytes` factory. The strict loader applies the byte-size cap, checks
    the expected digest before parsing, translates canonical parse errors, and
    checks structural joins only. It authenticates no source, seed registry,
    runtime, filesystem observation, admission, freeze, invocation, or
    execution, and emits no reusable capability. A caller-created record,
    digest, serialized “capability,” or token remains data rather than
    authority;
19. implement the atomic result/failed-attempt terminal transaction,
    authenticated external-witness verification/finalization path, and
    eventual runner mechanics in a separately reviewed sequence. Do not invoke
    the official supplier, issue a seed, or perform an official execution in
    this item;
20. implement one fused verify-and-exclusive-start operation. It must reopen
    and authenticate the exact target, launch intent, source/runtime closure,
    admission, execution identity, and physical store/lane; live-reobserve
    identity and output/terminal absence; and transition directly into the
    exclusive start. It must not serialize, return, cache, or accept a reusable
    authorization capability or caller token;
21. only after those execution surfaces are final, issue an exact current
    execution-source/runtime receipt, complete reviewed family admission, and
    establish seed-free readiness. C2 cannot satisfy this item, and no seed is
    supplied here;
22. acquire the exclusive seed-supply claim, invoke the supplier once,
    atomically publish the exact seed-bearing full design and replay target,
    then commit their freeze receipt before launch intent. A claim without
    target publication is `seed_supply_aborted` and non-retryable; target
    absence never proves that the supplier was not invoked;
23. after that committed D7 design-freeze receipt exists, execute the separate
    descriptive result without changing any D7 design byte; any change requires
    a new version and review;
24. invoke the fused verify-and-exclusive-start operation, run the admitted
    family without overrides or post-selection exclusions, publish exactly one
    terminal outcome, and require complete isolated byte-identical replay
    before setting any scope-specific D7/D8 status. Same-family new seeds
    remain replication and cannot satisfy this item;
25. only then begin the separate representation-native F0-F4 selection lane;
    independently confirm and replay its selected instrument without
    transferring Cartesian D2-D5 evidence;
26. establish the same-substrate field/core/loop join, persist the frozen
    same-field core-degeneracy scalar and nested-radius profile, and retain the
    architecture-accounted sampled-winding estimate distribution with its
    unrounded cycle totals and residuals; only when the convention permits it
    may calibration-side integer/topology eligibility be assessed;
27. qualify the opposite-sign dipole controls and the atlas-to-ANN-to-cycle
    detection-limit surface over injection amplitude, declared
    perturbation/noise, and sampling density, including density-stratified
    exact-recall and graph-family matched-class gates;
28. apply the preregistered M1 transition/stop rule. Pythia-70M remains
    plumbing-only; an exhausted qualification budget ends `insufficient`
    rather than extending instrumentation indefinitely; and
29. only after those separately reviewed M1 gates prepare and externally
    witness a new Pythia-160M subject manifest with new IDs under the
    no-subject-value boundary, while keeping Pythia-70M outcomes unable to
    select any Pythia-160M choice.

The generic access/lifecycle boundary and hermetic wheel-install validation are
already library capabilities. The D0-D5 chronology now additionally persists
one launch intent before its freeze-keyed exclusive attempt claim, requires
four exact clean tracked G artifacts before authorization, creates a distinct
immutable execution-start transition that binds the authorization digest and G
HEAD before generation, and publishes one immutable terminal transaction with
the same digest afterward. Generic standalone result persistence rejects the
official protocol ID; official authority exists only through this validated
typed-authorization, engine-to-G-to-current, start-to-terminal join. Those
files enforce local
no-overwrite history, but their access facts remain external attestations and
deletion rights remain trusted until a durable append-only store exists.

The current work has advanced from documentation and metadata-only contracts
into one bounded, model-free P1 development producer. That producer executes
the bound representation phantom, exact mutual-kNN development graph, and
F0/F1/F2 estimators, then semantically self-audits the generated arrays before
handing them to the generic closed-world validator. The generic validator
itself still treats payload values as opaque: it resolves exact artifact
identities, verifies payload bytes, and checks selected metadata joins without
recomputing estimator values.

This library slice adds, without changing that generic behavior:

- a registry-bound canonical F0-F4 pointwise-referent set;
- executable F2/F3 same-vector and F4 same-tensor relations;
- content-derived fit/evaluation partition receipts;
- out-of-band-parent-bound value-access lineage;
- a descriptor-retaining strict NPY consumer with row and L2 checks; and
- a second spectral-moment construction-family foundation whose exact four
  development cases keep estimator inputs and oracle truth separated; and
- a closed D7 draft-contract type reconstructed from the authoritative D6
  loader receipt, now superseded by an internal `v0.2` whose exact canonical
  historical body is preserved inside C1 while remaining unpersisted as a
  standalone/public artifact; its identity is stable across validation-only
  descendant HEAD changes, while deliberately admitting no family and issuing
  no full-design receipt;
- a strict full-parent design-body reconstruction and seed-slot execution
  inventory with exact 64/192/1,152 repeated-measures counts; and
- a development-only path through all crossed graph/core/loop cells that
  supplies no oracle-truth record to the blind kernels and cannot aggregate
  or publish a D7 result; and
- an internal `v0.1` D6-to-D7 successor-rule proposal that carries graph and threshold
  bodies exactly, rebinds cells/stress only through a matched structural
  projection, strictly reconstructs canonical bytes, and leaves both artifact
  publication and D6/D7 admission false; and
- one atomic six-component C1 candidate that preserves that proposal,
  records the successor review contract, static-bounded declared diversity
  review, seed-free design, registry/aggregation application, and declared
  Python source set; plus the choice-free C2 verifier and committed receipt.
  C1 remains a Level-0 source declaration that cannot attest its future
  commit; C2 verifies only that declared historical Git source set, not runtime
  or transitive dependencies, admission, or current compatibility; and
- canonical in-memory `spirallens.d7-replay-target-contract-spec.v0.1` and
  `spirallens.d7-attempt-envelope-contract-spec.v0.1` specifications,
  reconstructed only after the pinned C2 history is reverified. They define a
  future content-addressed, attempt-independent target and a separate
  append-only attempt lineage without persisting either instance, exposing a
  seed supplier, or granting authority. Because C2 is historical-only, a later
  exact current execution-source/runtime closure must follow the completed
  lifecycle, result, terminal, and runner code.

These capabilities make the pointwise same-object and value-validation
obligations testable. The `spirallens.graphs` foundation constructs three
deterministic exhaustive canonical-coordinate-order Euclidean float64
adjacency families, measures structural diversity, verifies an oriented finite
chain complex, and binds graph cycles to one exact induced support boundary.
The D0-D5 engine now consumes those foundations in a crossed model-free
selection design. That integration still establishes no homology or topology
certificate: it records only unrounded integrated sampled-phase totals and
graph-family stability.

Engine tests and development executions do not qualify D0-D8. The official
frozen D0-D5 Cartesian-surrogate result is recorded and passed its six scoped
gates, but no independent calibration confirmation is performed and no subject
is prepared, executed, or observed. Every current result remains Level 0 with
`d6_d8_advanced=false` and `synthetic_qualified=false`.
The detailed preparation gates are in
[Next Experiment Preparation](NEXT_EXPERIMENT_PREPARATION.md).

In parallel, a deliberately non-scientific
`public_example_engineering` lane may exercise the existing Pythia-70M
observation apparatus before D8. It is frozen to an `example`,
claim-ineligible ContextBank, exact offline model bytes, bounded rows,
CPU/float32 capture, and an atlas-integrity-only allowlist. Its receipt records
real model access and persisted activations, while candidate, neighbor,
instrument, graph, field, core, loop, semantic, SAE, integer, and D0-D8 stages
remain `not_run`. This lane cannot select any choice in steps 5-29 above and
cannot be cited as subject preparation or evidence.

The successor-only fulfillment rule for the D6 v0.1 identity-bearing
cells/stress manifests remains an unchanged historical proposal. C1 is now
recorded as a source-only Level-0 candidate: it declares and hashes the
complete `src/spirallens/**/*.py` plus `pyproject.toml` set, but deliberately
cannot attest its future commit or declared Git source-set closure. The
choice-free C2 receipt is now recorded as the unique receipt-only child of the
exact clean post-merge C1 commit. It does not attest runtime or transitive
dependencies. The separate canonical replay-target and attempt-envelope
contract specifications are implemented in memory, but no concrete instance
is persisted. Step 18 is now partially complete: two deep-internal modules
define the concrete canonical record schemas and pure structural joins for
declaration through consumption, and four further deep-internal modules now
close the canonical result-component, absence-receipt, failure-payload, and
external-receipt byte shapes. A seventh module now persists and strictly
reloads the caller-supplied primary declaration-through-start record prefix as
no-replace, false-authority scope/envelope evidence. It reports exact
start-record plus terminal absence only as
`caller_supplied_start_record_present_terminal_absent`, never as execution or
`started_unresolved`. Their acyclic outcome → manifest → consumption
graph keeps scientific `pass`/`fail`/`insufficient` distinct from
infrastructure failure. The result bundle mechanically rejoins cells,
primaries, strata, four-state gates, and the outer payload, but target exact
sets and gate evidence still require an authoritative target loader. The start
schema binds an external execution identity. The prefix writer reobserves only
the declared local path coordinates; no source/runtime authority or witness
verifier exists. PR #23 now adds an eighth deep-internal module whose strict
loader returns only a non-authorizing structural candidate. Dedicated
caller-claimed target admission, exact-full-design, and exact-source/runtime
leaves record `identity_authenticated=false`. Typed exclusive-claim and
single-invocation inputs causally join supplier, registries, readiness,
caller-alleged receipt bindings, official inventory, and atomic publication.
The physical input binds the target-and-primary-role-derived attempt key,
positive distinct store/lane identities, and lexical plus
known-physical-alias persistence-reserved path exclusions. The artifact
binding has no raw
`from_bytes` factory; the loader applies its size cap, verifies the digest
before parsing, and translates canonical parse errors. It authenticates no
caller, receipt, registry, claim, invocation, or publication, performs no live
observation, and emits no reusable capability. No terminal
publisher, authoritative target/store loader,
execution capability, runner, finalizer, replay comparator, official seed, or
official record instance is introduced. After those
operational surfaces, a fused verify-and-exclusive-start operation, and the
runner are final, a new exact current execution-source/runtime closure and
reviewed admission are required; C2 cannot supply them. Only afterward may
the supplier be invoked once, target/full design be published and frozen,
launch intent be persisted, and the fused start be invoked. Lifecycle and
terminal work keep the replay target separate from the attempt envelope and
create no placeholder result. The current
four-case generator, C1 design, rebinding record, contract specifications,
record schemas, and development prediction inventory are not a D7 full-design
freeze, admission, or run. Historical D6 bytes remain unchanged and exact D6
v0.1 admission remains false. Only a later locked D7 pass and isolated
byte-identical D8 replay could support a scope-specific synthetic-qualified,
replayable bundle.
That still would not mean “find a semantic vortex” or authorize a subject run.

## 12. Roadmap change rule

Changes to milestone order or scientific promotion gates should update this
document and the Fundamental Frame in the same reviewed change. Every
interpretive change also receives an Interpretation Ledger entry. Completed
milestones, frozen protocols, and persisted outcomes retain their original
criteria and bytes; amendments are recorded explicitly rather than silently
rewriting history.
