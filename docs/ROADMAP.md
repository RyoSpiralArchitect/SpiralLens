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

## 1. North star

SpiralLens should become a model-agnostic, auditable toolkit for measuring
closed-loop transport structure in learned representations while keeping four
things separate:

1. a geometric or transport observable;
2. invariance under declared nuisance transformations;
3. a topology claim;
4. a semantic or causal interpretation.

The library should let a researcher construct a loop, estimate local transport,
account for known architectural factors, persist every decision with provenance,
run matched nulls, and promote a result only as far as its evidence allows.

The motivating optical-vortex and OAM analogy is useful intuition. It is not an
assumption that transformer activations are physical optical fields.

## 2. Non-negotiable scientific boundaries

These rules apply to every milestone and release:

- A large drift is not automatically a phase shift.
- High cosine similarity plus divergent updates creates a structural candidate,
  not a verified vortex or semantic distinction.
- Continuous holonomy and sampled winding remain separate types and claims.
- Sampled winding is the winding of the declared discrete interpolation; it is
  not a certificate for an unknown continuous field.
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
- Pythia-70M is plumbing and integration validation. Pythia-160M is the first
  intended claim-bearing model.

The [claim ladder](claim_ladder.md) remains authoritative for result labels,
and an individual experiment protocol remains authoritative for that run’s
thresholds and claim ceiling.

## 3. Two independent maturity axes

SpiralLens tracks scientific evidence and software maturity separately.

- **Scientific evidence:** analogy → Level 1 observable → Level 2 invariant
  candidate → Level 3 semantic and causal evidence.
- **Software maturity:** research preview → experimental API → alpha → beta →
  stable library.

A scientific hypothesis may be rejected while the software still matures into
a valuable 1.0 library that reliably reproduces positive, negative, and
inconclusive outcomes. Conversely, an interesting Level-2 or Level-3 result
does not make the API stable. Release versions describe software contracts, not
the truth of the motivating hypothesis.

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
| `contracts`, `loops`, `holonomy`, `topology` | Framework-neutral mathematical types and operations | NumPy/SciPy only |
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

Delivered:

- analytic rotation, winding, stretch, radial, shear, basis, reverse,
  off-core, nested-radius, and sampling-alias controls;
- separate continuous-holonomy and sampled-winding contracts;
- Hugging Face Pythia observation adapter;
- memory-mapped activation atlas with atomic manifests;
- immutable model revision and capture-runtime provenance;
- per-batch slice hashes, whole-file hashes, and fail-closed resume;
- structural candidate ledger with no semantic or SAE input;
- protocol ID, status, SHA-256, claim ceiling, and override provenance;
- exact blockwise pair search with an explicit size guard;
- CLI commands for calibration, atlas capture, and candidate extraction.

Exit criteria:

- all analytic controls pass;
- storage corruption and incompatible resume are rejected;
- a real Pythia-70M bounded smoke completes offline;
- a zero-candidate run completes normally;
- no current artifact is described above Claim Level 1.

What M0 does **not** prove:

- that a Pythia representation contains a closed semantic loop;
- that any candidate has non-zero relative holonomy;
- that sampled winding reflects continuous topology;
- that SAE reconstruction removes the hypothesized information.

### M1 — Candidate-to-loop integration

**Status:** immediate next milestone.

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
   rejects any mismatch.
5. Atlas manifests persist `language_space_atlas=false`,
   `semantic_unit=false`; decoded strings, when present downstream, are
   display-only sidecars rather than observation identity.
6. A neighbor-search protocol suitable for the full 50,304-row Pythia model
   input embedding table.
7. An exact reference backend for bounded datasets and an audited approximate
   backend for full-vocabulary discovery.
8. Recall and determinism evaluation of the approximate backend against exact
   subsets; the initial recall target is at least 0.99 at the preregistered
   candidate boundary.
9. Approximate search is used only for retrieval; every persisted candidate is
   reranked and gated with the exact metric.
10. A semantics-free candidate graph and deterministic cycle-construction
   procedure.
11. Local transport estimation using declared JVP, pullback metric, whitening,
   and/or Procrustes choices.
12. Relative holonomy rather than raw endpoint drift.
13. RoPE, LayerNorm, attention value, attention routing, MLP, basis,
    orientation, radius, and sampling-density controls wired into one run
    artifact.
14. Each required gate is persisted as `pass`, `fail`, `insufficient`, or
    `not_run`; incomplete gates cannot silently pass.
15. A versioned loop/candidate artifact linking every result back to atlas rows
    and protocol hashes.

Exit criteria:

- a full-vocabulary Pythia-70M atlas completes for every declared fixed
  context/position slice under a recorded resource budget;
- the tracked public example bank validates with all roles equal to `example`
  and with claim eligibility disabled;
- approximate discovery meets its preregistered recall target on exact subsets;
- loop construction is deterministic from the frozen protocol and run ID;
- injected-rotation positives survive while pure-gauge/stretch/shear negatives
  are rejected;
- each shortlisted real-model loop has matched reverse, radius, sampling, and
  architecture-accounted controls;
- rerunning from persisted atlas data requires no model download or inference;
- results remain Claim Level 1 unless every Level-2 control is complete.

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
- complete offline replay artifacts;
- a concise result report that treats positive, zero, and null outcomes equally.

Exit criteria:

- one clean protocol run without post-hoc discovery-threshold changes;
- every reported candidate links to all required null results;
- an independent rerun reproduces the persisted structural quantities within
  declared numerical tolerances;
- any Level-2 label is earned per candidate, not inherited from the run.

Passing M2 does not establish semantics or SAE loss.

### M3 — SAE gap and causal semantic validation

**Status:** future research milestone.

**Target release family:** `0.4.x`.

Deliverables:

- frozen SAE choice, reconstruction definition, and comparison layer;
- raw-residual versus SAE-reconstruction transport measurements at matched
  points;
- held-out semantic minimal pairs added only after structural discovery;
- norm-preserving cyclic-mode interventions and matched sham interventions;
- selective downstream behavioral endpoints;
- checkpoint and seed replication where models and SAEs permit it.

Exit criteria:

- a preregistered structural quantity predicts held-out contrasts;
- the result is not explained by norm, token frequency, position, RoPE,
  routing, or reconstruction-error magnitude alone;
- intervention direction and dose predict selective downstream changes;
- sham, random-subspace, and reverse interventions fail as expected;
- the effect replicates across declared contexts and at least one independent
  model checkpoint or seed.

Only this milestone can support a Claim Level 3 result.

### M4 — Replication and model abstraction

**Target release family:** `0.5.x`.

Deliverables:

- a model-observer adapter protocol independent of Hugging Face class names;
- a second model family in addition to Pythia/GPT-NeoX;
- checkpoint, seed, or scale replication where public models permit it;
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
record reviewed in public. Until that structure lands, this roadmap, the claim
ladder, and tracked protocols are the decision anchors.

Contributions submitted to the project are accepted under Apache-2.0 unless
explicitly stated otherwise.

## 10. Known risks

| Risk | Required response |
| --- | --- |
| Optical language outruns the observable | Persist mathematically named quantities and explicit non-claims |
| Projection artifacts look like vortices | Require ambient-space or gauge-accounted controls |
| Full-vocabulary search becomes intractable | Keep exact reference subsets and audit approximate recall |
| Backend differences create false candidates | Bind backend/runtime and test repeatability before promotion |
| Resume blesses corrupted partial data | Verify committed batch hashes before writing a new attempt |
| Semantic labels leak into discovery | Separate modules, artifacts, and dataset splits |
| Interesting Pythia-70M result drives confirmatory-bank tuning | Keep 70M as plumbing; freeze 160M contexts, splits, thresholds, and preprocessing independently of its outcomes |
| Research API ossifies too early | Stabilize only independently reused, documented contracts |
| Library engineering dilutes scientific falsifiability | Require the same claim ladder through every release |

## 11. Immediate next plan

The next implementation sequence after the initial public repository push is:

1. define `ObservationKey`, `ContextSpec`, and `ContextBank` contracts;
2. validate a public 6–12-context synthetic engineering bank with only
   `role=example` and `claim_eligible=false`;
3. bind the bank's exact role, entry order, positions, sweep domain, and both
   digests into atlas capture and resume;
4. define a neighbor-backend interface and retain exact blockwise search as the
   reference implementation;
5. implement an audited full-vocabulary candidate index with recall measurement;
6. construct a deterministic semantics-free candidate graph and closed cycles;
7. connect cycles to local transport, relative holonomy, and the full null suite;
8. run the integrated Pythia-70M pilot;
9. create separate frozen M2 discovery and held-out banks without using 70M
   outcomes to tune the 160M confirmatory bank, then freeze the Pythia-160M
   protocol.

The immediate deliverable is not “find a semantic vortex.” It is a replayable
candidate-to-loop artifact whose promotion gates are explicit before the
Pythia-160M result is visible.

## 12. Roadmap change rule

Changes to milestone order or scientific promotion gates should update this
document in the same pull request as the implementing change. Completed
milestones should retain their original exit criteria, with amendments recorded
explicitly rather than silently rewriting history.
