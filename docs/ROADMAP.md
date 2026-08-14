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

The two axes therefore use different canonical milestone namespaces:

| Lane | Canonical milestones | Current state | What advances the lane |
| --- | --- | --- | --- |
| Scientific | `SCI-S0` through `SCI-S4` | `SCI-S0` implemented and hardening; `SCI-S1` in progress | A frozen protocol reaches its declared scientific terminal condition. A `fail` or finite-budget `insufficient` is a completed outcome, although it may leave a later scientific milestone unauthorized. |
| Library | `LIB-L0` through `LIB-L3` | `LIB-L0` in progress | Software-contract, portability, compatibility, documentation, and release gates pass. No positive scientific result is required. |

Only the following cross-lane dependencies are normative:

- outputs from `SCI-S0` are candidates for `LIB-L0` extraction, but promotion
  requires a library-owned contract and two independent consumers;
- `SCI-S1` may use provisional internal APIs and does not wait for `LIB-L1`;
- `SCI-S1` must terminate under its frozen budget. A qualifying pass can
  authorize `SCI-S2`; `fail` or `insufficient` closes that attempt without
  authorizing `SCI-S2` and without blocking the library lane;
- `SCI-S2` and `SCI-S3` may supply protocols and artifacts for `SCI-S4`, while
  the absence of an eligible candidate is recorded rather than converted into
  a software blocker;
- library adapter conformance may reuse model families examined by `SCI-S4`,
  but it tests the adapter contract, not replication of a scientific effect;
- `LIB-L1` through `LIB-L3` never promote a claim level. They must preserve and
  expose negative, `insufficient`, and `not_run` outcomes without laundering
  them into evidence.

### 3.1 Canonical IDs and historical aliases

New documents, issues, PRs, and generated status surfaces use the canonical ID
before any prose description:

| Namespace | Scope | Example |
| --- | --- | --- |
| `SCI-Sn` | scientific milestone | `SCI-S1` field qualification |
| `LIB-Ln` | library milestone | `LIB-L1` alpha |
| `SCI-S1-Rnn` | numbered requirement in the `SCI-S1` deliverable list | [`SCI-S1-R22`](#sci-s1-r22) count and worst-case gates |
| `D7-OPS-nn` | numbered chronology in the D7 operations ledger in section 11 | [`D7-OPS-22`](#d7-ops-22) seed-supply transaction contract |

Bare `M1`, `item 22`, or similar references are not unique and are not used for
new normative references. Existing symbols, schema identifiers, artifact
bytes, Git history, and quotations retain their historical spellings. When a
historical alias is needed in new prose, it follows the canonical ID, for
example `D7-OPS-22 (historical item 22)`.

The former single-axis milestone labels remain historical navigation aliases:

| Historical alias | Canonical destination |
| --- | --- |
| `M0` | `SCI-S0` |
| `M1` | `SCI-S1` |
| `M2` | `SCI-S2` |
| `M3` | `SCI-S3` |
| `M4` | scientific replication and checkpoint dynamics → `SCI-S4`; internal model-observer boundary and framework-neutral core → `LIB-L0`; public adapter protocol → `LIB-L1`; second-adapter portability evidence → `LIB-L2` |
| `M5` | `LIB-L1` |
| `M6` | `LIB-L2` |
| `M7` | `LIB-L3` |

This mapping changes prospective interpretation and references only. It does
not rename or reinterpret a frozen artifact, protocol, outcome, or historical
commit.

### 3.2 V1–V9 navigation overlay

The canonical
[`VOY-V1`–`VOY-V9` route](../protocols/voy_v1_v9_strict_successor_route_v0_1.json)
is a navigation and fresh-coordinate declaration overlay on the existing
`D7-OPS`, `SCI-Sn`, and `LIB-Ln` namespaces. It neither reproduces their live
status nor renames, completes, or authorizes them, and it performs no
filesystem reservation or ownership claim. It grants no public-API,
repository-bound-export, console-script, runtime-dependency, maturity, or
schema promotion; the library lane is independent of VOY progress.

The separately frozen
[`d7-v1-pre-item23-materialization-v0-1`](../protocols/d7_v1_pre_item23_materialization_v0_1.json)
contract is a prospective `VOY-V3` input design, not a completed VOY stage. It
defines 11 primary structural schemas over nine future pre-item-23 files and a
later result, but remains `frozen_not_run`. An internal read-only kernel now
strictly rejoins a supplied staged tree and verifies the prospective
single-parent commit A and result-only commit B. It deliberately has no
caller-owned-stage publisher: that shape cannot close the validate-to-rename
race. A separate internal source-only primitive now owns a
private stage, performs exact-tree and joined validation, fsyncs members and
directories, and uses only a native no-replace directory rename. It remains
uninvoked and its observation is structural-only; reviewed source commit S,
C1/C2, external claims, artifact publication, result, and execution remain
absent. Fresh source now implements the bounded six-read post-D6 descriptive
derivation and the declared v1 preparation, runner, and official-callable
coordinates. The entrypoints stop before dispatch; a later private source
closes the external chronology but remains unwired because independent S
review and selection, runtime closure, invocation authority, and
execution-start authority are absent. A separate internal source-only stage-17
primitive now owns its result
bytes by rejoining exact commit A and source S and rerunning the six-input
derivation; it accepts no caller result, path, or stage and can publish only at
the fixed coordinate with fsync plus native no-replace rename. It remains
uninvoked. Future commit-B verification requires the same byte-exact
rederivation and rejects schema-valid substitute outputs. Before S selection,
the descriptive implementation was split from one 4,699-line module into a
287-line facade and eight bounded private work packages. Its canonical result
bytes are unchanged, and every helper is now joined independently to its import
origin, live source, source-S blob, and C1 member tuple. A private source-only
builder now derives an in-memory C1/C2 candidate from an asserted clean current
`HEAD` without accepting caller source paths, members, bytes, record IDs, or
callbacks. Its exact Git inventory contains every tracked ordinary
`src/spirallens` blob plus the project metadata, declared runtime lock, frozen
protocol and route, and required v1 scripts. It canonically reloads and rejoins
both records and repeats the clean-HEAD gate before return. This does not review
or select S. The entire frozen v1 repository root must be absent in that
asserted tree, but this current-tree fact does not prove artifact chronology.
Runtime-lock membership does not attest installed dependency or runtime
conformity. Source completion remains unmet, S remains unselected, and no
artifact or result has been generated. A later private source-only candidate
now rebuilds that C1/C2 candidate and rejoins only the deterministic contract
surface already available without choosing values: supplier role
`supplier-identity`, ordered slots `confirmation-seed-slot-00` and
`confirmation-seed-slot-01`, and the exact seven embedded full-design
field-to-role entries. It returns no supplier identity, binding bytes, seed,
claim, inventory, full design, or chronology. In particular, neither the
two-seed cardinality nor any of the six non-inventory bindings is authorized
for persistence; at that increment they remained unspecified pending a later
source-selected derivation and verifier. The supplier portion is now
source-fixed in a later private candidate: one exact zero-argument module-global
OS-CSPRNG callable, canonical supplier identity, and a combined registry of two
predecessor, two parent-selection, and four development exclusions. The
joined-loader path independently rederives that identity and requires a future
inventory to contain exactly two unique ascending values outside all eight
exclusions. This is still pre-chronology source work: the supplier is not
invoked and no seed or durable record is created. A subsequent private layer
now resolves the six non-inventory design bindings only as source-derived
virtual referents. From exactly five permitted pinned scientific parents it
performs typed reconstruction and cross-joins, invokes the approved seed-free
execution-design builder exactly once, and derives the family proposal and
non-issued admission, unfrozen protocol draft, Git-declared source-member
graph, exact 64/192/1,152/six-stratum aggregation, and the protocol's exact
19-stage, three-commit future chronology policy. The documents remain private,
in-memory, and nonpersisted. The joined materialization verifier independently
rederives and exact-compares all six bindings.
This closes a structural binding gap only. External-binding authentication,
runtime-environment authentication, runtime dependency-closure verification,
family admission, official embedded-full-design creation/freeze, aggregation
review/application, and lifecycle instantiation all remain false. There is no
store, official coordinate, claim, supplier invocation, seed, execution,
result, scientific evidence, persisted/supported schema, protocol, route,
record, public API, or dependency revision. S remains unreviewed and
unselected; claim delta is `none`, VOY-V3 remains `frozen_not_run`, and D7/D8
remain `not_run`.
Before S selection, the 2,108-line referent module was further split into a
721-line pure canonical-document kernel behind a 1,808-line provenance facade.
The new leaf performs no Git or filesystem I/O and is itself joined to its
repository import origin, live bytes, source-S blob, and C1 member. Referent
semantics and every provenance and authority boundary are unchanged.
One private, non-exported source operation now implements the previously
missing pre-item-23 chronology owner. It accepts only a repository and asserted
exact source commit; derives all records and fixed coordinates internally;
makes the external claim durable before entering the captured fixed supplier
exactly once; makes the attempt durable; promotes the exact two-file external
store without replacement; creates the chronology receipt last; rejoins all
bytes; and delegates only the exact nine-file repository publication to the
existing private publisher. A sealed publisher-owned descriptor capability
keeps both external files and their full directory ancestry reauthenticated
through all repository-publication gates. Composite failures preserve facts
for both namespaces. Every failure is non-cleanable, non-resumable, and
non-retryable. The operation is deliberately uninvoked and the preparation
entrypoint remains unwired. Its commit argument does not prove independent
source review or selection, installed-runtime closure, or invocation
authority. No materialization artifact, commit A/B, execution, result, or
scientific evidence is created; S remains unreviewed and unselected, claim
delta is `none`, VOY-V3 remains `frozen_not_run`, and D7/D8 remain `not_run`.
No `D7-OPS`, scientific, or library completion credit changes here.

### Current verified-B observation (2026-08-13)

The source-era paragraphs above remain historical statements. Exact source S
`a9b9da21954478e42982e27f9e6b02cbeba5a08d` now has a strict successor A
`be4462c3eee666aff620292b1494cc4209a0c6a6` containing only the nine
pre-item-23 files and a strict successor B
`9735ae8b231f5b6e967a4b7dbaed0fb2eca78061` containing only the descriptive
result. Existing protocol and route bytes are unchanged. The protocol's
`frozen_not_run` value records its issue-time state; it is not rewritten into a
live status claim.

Verified B matches the evidence shape named by the VOY-V3 purpose,
`prospective-receipt-and-conforming-descriptive-artifact`. Because the VOY
route is a navigation alias rather than a status or authority registry, this
is recorded only as **VOY-V3 purpose evidence observed**. It does not establish
VOY-V3 completion credit, `D7-OPS-22` or `D7-OPS-23` credit, or authorization
to enter VOY-V4. The V4 predecessor relation orders review; it is not a
dispatch trigger.

The descriptive status is `insufficient`, with 26 available outputs and one
blocked output caused by unpersisted historical main-D2 scalar values. Its
attempt remains `reserved_not_started`, `scientific_result_issued=false`, and
`d7_result_produced=false`; this is not a D7 terminal and is not the VOY-V9
branch status. No reconstruction, rerun, or same-identity rescue is authorized.
Progress therefore holds at the V3/V4 decision boundary. Continuing the strict
route requires a separate V4 readiness and authority decision. Bending the
route requires a new reviewed route version and a dated Ledger entry before
any affected input is consumed.

The library lane remains independent. Neither this documentation projection
nor the artifact chain counts as either independent library consumer; no
library-owned contract or maturity was promoted. The two-independent-consumer
rule and the preservation of `blocked`, `insufficient`, and `not_run` states
remain in force. No library milestone changes.

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
| `contracts` | Exact-seven root namespace has one provisional, namespace-scoped library-admission observation; no deep module or per-name admission | NumPy only; focused behavior/identity evidence, not promotion |
| `loops`, `holonomy`, `topology` | Framework-neutral mathematical operations; provisional and outside the `contracts` observation, with no admission decision following | NumPy/SciPy only |
| `referents` | Provisional F0-F4 pointwise objects, transformation laws, fit/evaluation partitions, and same-object relations | NumPy plus contract enums; no substrate field or model-side existence claim |
| `instrument_contracts` | Provisional manifests, closed-world integrity, selected metadata joins, and a separately authorized strict numeric consumer | Ordinary loading remains opaque; numeric access is lineage-gated and subject roles are forbidden |
| `synthetic` | Model-free construction-family identities, development generators, separated truth controls, numeric self-audit, and bounded bundle publication | Experimental core; no calibration selection or subject execution |
| `graphs` and future order-parameter boundaries | Provisional exact graph/domain fingerprints now; later field artifacts, core diagnostics, and qualification gates | NumPy-only in-memory foundation; persistence and scientific promotion remain future work |
| `qualification` | The installed boundary is the exact 19-module model-free D0-D6 protocol, source/evidence roots, separate core and continuous sampled-loop kernels, crossed aggregation, one-attempt terminal chronology, and scope-limited D6 admission. All 47 `confirmation_*` D7 design/prediction/rebinding/replay implementation modules remain under the same repository source namespace but are repository-only experiment internals, not wheel members or root exports. | The installed closure uses NumPy/PyYAML plus project contract foundations and retains all 115 ordered root exports. Repository-only C1 records the atomic Level-0 seed-free design, static-bounded declared diversity review, registry/aggregation application, review contract, and declared source set; committed C2 verifies that historical Git source set only; canonical D7 replay-target and append-only attempt-envelope specifications define separate contracts; deep-internal record, payload, structural-join, caller-prefix evidence lane, authority-prerequisite, atomic structural terminal, signed external-witness, typed post-start runner, and same-call fused-start mechanics complete `D7-OPS-19` and `D7-OPS-20` without an official run; the corrected `D7-OPS-21` receipt-only chain is complete; the reviewed exact-current re-anchor, Level-0 `D7-OPS-22` transaction/freeze receipt, operationally complete/scientifically insufficient but chronology-deviated item-23 result, later all-false nine-member descriptor/intent, and canonical non-retroactive disposition are persisted; strict observation now reports the post-descriptor presence state `launch-intent-present`, while v0.1 official entry is blocked; `freeze_verified=false`, every receipt binding retains `authoritative_source_loaded=false` and `identity_authenticated=false`, and official run, replay, and D7/D8 authority remain absent. |
| `calibration` | Analytic positive controls, negative controls, and instrument qualification | Core only |
| `metrics`, `gauge`, `nulls` | Structural observables, alignment, and matched controls | Core by default |
| `adapters` | Pythia, Hugging Face, and future model-family capture | Optional model extras |
| `atlas` | Streaming observation storage, integrity journals, and replay | NumPy/PyYAML reader closure and all exact 20 root/star bindings are importable without model frameworks; sweep and public-example execution remain model extras, and the whole namespace remains provisional/model extra |
| `jacobians`, `factors` | JVP and architecture-component accounting | Core analytic paths plus optional autodiff |
| `interventions` | Explicitly scoped activation interventions | Optional model extras |
| `semantics` | Post-discovery annotation and held-out evaluation | Never imported by discovery |
| `protocols` | Human-reviewable experiment declarations | Data, not hidden defaults |
| `benchmarks` | External comparison systems | Never imported by the core package |

TransformerLens or any other hook framework may become an adapter, but must not
define the core mathematical API or artifact schema.

## 6. Two-lane milestones

### Scientific lane

<a id="sci-s0"></a>
#### SCI-S0 — Auditable instrument foundation (historical `M0`)

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

- no `SCI-S0` artifact exceeds the current Level 1G or Level 1D ceilings;
- no real-model defect field reaches Level 1D.

What `SCI-S0` does **not** prove:

- that a Pythia representation contains a closed semantic loop;
- that any candidate has non-zero relative holonomy;
- that sampled winding reflects continuous topology;
- that a model-derived order parameter or core has been defined;
- that a scalar support diagnostic supplies phase or quantized charge;
- that one deterministic graph construction is topology-invariant;
- that SAE reconstruction removes the hypothesized information.

<a id="sci-s1"></a>
#### SCI-S1 — Field qualification and candidate-to-loop integration (historical `M1`)

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

Deliverables:

1. <a id="sci-s1-r01"></a>**SCI-S1-R01** — `ObservationKey` and `ContextBank` contracts that make model revision,
   context, token position, layer, and capture stage explicit.
2. <a id="sci-s1-r02"></a>**SCI-S1-R02** — A tracked public context bank containing 6–12 project-authored synthetic
   engineering fixtures. Every context has `role=example` and
   `claim_eligible=false`; the bank tests loading, validation, capture, and
   replay only.
3. <a id="sci-s1-r03"></a>**SCI-S1-R03** — Discovery and held-out roles are rejected from that public engineering
   bank. Scientific discovery and held-out banks begin in `SCI-S2` as separate frozen
   artifacts.
4. <a id="sci-s1-r04"></a>**SCI-S1-R04** — Atlas requests bind the bank's source and canonical digests, selected role,
   ordered context IDs, sweep/observation positions, and sweep domain. Resume
   rejects any mismatch before appending an attempt. The binding embeds
   canonical bank content so load/replay can recompute bank, selected-context,
   tokenizer, and request-identity digests independently.
5. <a id="sci-s1-r05"></a>**SCI-S1-R05** — Atlas manifests persist `language_space_atlas=false`,
   `semantic_unit=false`; decoded strings, when present downstream, are
   display-only sidecars rather than observation identity. Candidate references
   carry the bound bank/context/spec identities and tokenizer-addressability
   flag rather than aggregating by decoded text.
6. <a id="sci-s1-r06"></a>**SCI-S1-R06** — A neighbor-search protocol suitable for the full 50,304-row Pythia model
   input embedding table.
7. <a id="sci-s1-r07"></a>**SCI-S1-R07** — An exact reference backend for bounded datasets and an audited approximate
   backend for full-vocabulary discovery.
8. <a id="sci-s1-r08"></a>**SCI-S1-R08** — Recall and determinism evaluation of the approximate backend against exact
   subsets; the initial recall target is at least 0.99 at the preregistered
   candidate boundary.
   Promotion also requires the frozen query-local, relative-density,
   density-by-cosine-boundary, and worst-case coverage gates; aggregate recall
   alone is not sufficient. Freezing those measurement rules is not a Pythia
   audit result.
9. <a id="sci-s1-r09"></a>**SCI-S1-R09** — Approximate search is used only for retrieval; every persisted candidate is
   reranked and gated with the exact metric.
10. <a id="sci-s1-r10"></a>**SCI-S1-R10** — Experimental `SubstrateBinding`, `SupportDiagnostic`,
    `GeometricFieldEstimate`, `CoreScore`, `OrderParameterSpec`,
    `OrderParameterField`, `CoreCandidate`, and `GroundTruthAnchor` contracts
    qualified on synthetic representation-shaped phantoms before any new
    subject protocol.
11. <a id="sci-s1-r11"></a>**SCI-S1-R11** — Competing field hypotheses with explicit transformation laws, fit scopes,
    claim ceilings, and no outcome-selected winner.
12. <a id="sci-s1-r12"></a>**SCI-S1-R12** — Semantics-free, deterministic mutual-kNN, fixed-radius, and
    shared-neighbor candidate graph families with canonical construction
    receipts.
13. <a id="sci-s1-r13"></a>**SCI-S1-R13** — Deterministic cycle construction plus a matched support or homology rule
    that remains meaningful across genuinely different graph-construction
    families and compares the same enclosing support/class rather than
    construction-specific cycle indices.
14. <a id="sci-s1-r14"></a>**SCI-S1-R14** — A full crossed field-estimation-graph by cycle-construction-graph null,
    extended by a core-estimation-graph axis whenever the core estimator is
    neither graph-free nor bound to the field graph, with graph diversity,
    support, and worst-case gates.
15. <a id="sci-s1-r15"></a>**SCI-S1-R15** — Local transport estimation using declared JVP, pullback metric, whitening,
    projector, and/or Procrustes choices.
16. <a id="sci-s1-r16"></a>**SCI-S1-R16** — Relative holonomy rather than raw endpoint drift on the geometry branch.
17. <a id="sci-s1-r17"></a>**SCI-S1-R17** — Sampled winding only from an eligible, nonzero, orientable
    order-parameter section on the defect branch with a frozen
    trivialization/reference or gauge-invariant connection-corrected lift.
18. <a id="sci-s1-r18"></a>**SCI-S1-R18** — RoPE, LayerNorm, attention value, attention routing, MLP, basis,
    orientation, radius, sampling-density, graph-family, and matched-null
    controls wired into one run artifact.
19. <a id="sci-s1-r19"></a>**SCI-S1-R19** — Each required gate is persisted as `pass`, `fail`, `insufficient`, or
    `not_run`; incomplete gates cannot silently pass.
20. <a id="sci-s1-r20"></a>**SCI-S1-R20** — Versioned substrate, field, graph, discriminated geometry/defect loop, and
    result artifacts linking every result back to atlas rows, fit scopes, and
    protocol hashes.
21. <a id="sci-s1-r21"></a>**SCI-S1-R21** — A charge-blind `CoreScore`/`CoreCandidate` receipt bound to the same
    order-parameter field and frozen before loop readout, kept distinct from a
    supplied `GroundTruthAnchor`, with known-core, off-core, density, and
    sparse-support controls. Its D2-only falsifier matrix distinguishes a
    high-amplitude local-identifiability-loss decoy from a localized
    same-section low-amplitude candidate and requires independent measurement
    support at the candidate itself. The current engine binds the core input
    to the inherited field-estimation graph and keeps this Level-0 candidate
    below any vortex, topology, charge, or core-loop-join claim.
22. <a id="sci-s1-r22"></a>**SCI-S1-R22** — Attempted, evaluable, insufficient, and abstention counts plus worst-case
    coverage, recall, and specificity gates across required phantom strata.
23. <a id="sci-s1-r23"></a>**SCI-S1-R23** — A content-addressed `CalibrationSelectionDecision` sealed before hidden
    confirmation, followed by a non-selecting
    `CalibrationConfirmationResult`.
24. <a id="sci-s1-r24"></a>**SCI-S1-R24** — A future `SubjectProtocolManifest` and access boundary that reveal no
    subject-derived values before separate review, freeze, and execution
    authorization.
25. <a id="sci-s1-r25"></a>**SCI-S1-R25** — A protocol-declared same-field core-degeneracy scalar recorded at every
    candidate and as a nested-radius radial profile. Its threshold and matching
    rule are frozen before any loop value is read.
26. <a id="sci-s1-r26"></a>**SCI-S1-R26** — An architecture-accounted sampled-winding estimate distribution across the
    eligible loop ensemble, retaining every unrounded cycle total and
    proximity-to-integer residual and comparing them with continuous and
    integer-clustered calibration controls. This is a non-quantization
    diagnostic, emits no resolved charge label, and is never a charge
    certificate by itself.
27. <a id="sci-s1-r27"></a>**SCI-S1-R27** — An opposite-sign dipole phantom with a separation sweep, single-core loop
    signs, both-core-loop additivity/net-zero checks, and explicit two-core
    resolution. It also calibrates the measurement needed by any future
    checkpoint-series annihilation analysis.
28. <a id="sci-s1-r28"></a>**SCI-S1-R28** — An end-to-end detection-limit surface over injection amplitude, declared
    perturbation or noise level, and sampling density. Synthetic fields must
    enter through the atlas representation and traverse ANN retrieval, exact
    reranking, graph construction, cycle construction, and the final gates.
    Exact-recall audits are stratified by local-density and candidate-boundary
    cells because exact reranking cannot recover neighbors the ANN never
    retrieved.
29. <a id="sci-s1-r29"></a>**SCI-S1-R29** — A bounded qualification transition rule fixed before further tuning. Each
    protocol declares its maximum revision/resource budget and a terminal
    action. Complete, evaluable required-gate success is `pass` and may
    authorize `SCI-S2`. Any complete, evaluable required-gate failure is a
    terminal `fail`, cannot be retuned under the same protocol identity, and
    does not authorize `SCI-S2`. Missing evaluability, support, coverage, or
    sensitivity at budget exhaustion is terminal `insufficient`, supports no
    falsification or qualified-null claim, and does not authorize `SCI-S2`.

Exit criteria:

- a full-vocabulary Pythia-70M atlas completes for every declared fixed
  context/position slice under a recorded resource budget;
- the tracked public example bank validates with all roles equal to `example`
  and with claim eligibility disabled;
- approximate discovery meets its preregistered recall target on exact subsets;
- the end-to-end detection-limit surface is frozen and complete before `SCI-S2` or
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
- the terminal `SCI-S1` transition is persisted as exactly one of `pass`,
  `fail`, or `insufficient` under the frozen protocol and resource budget;
  adverse evaluable gates cannot be relabeled as missing evidence.

Pythia-70M may exercise this path before qualification only as a
claim-ineligible plumbing run. It cannot satisfy the detection-limit exit
criterion or authorize `SCI-S2`.

<a id="sci-s2"></a>
#### SCI-S2 — Frozen Pythia-160M scientific protocol (historical `M2`)

**Status:** blocked on `SCI-S1` by design.

A private, nonpersisted pre-observation declaration assessor may be developed
in parallel as source-only preparation. It treats revision, architecture,
files, dimensions, and counts as unverified declarations, performs static
integer resource arithmetic only, and remains
`blocked_external_prerequisites`. It does not observe a model, host resource,
context bank, manifest, or payload; it cannot satisfy or transition `SCI-S1`,
unblock `SCI-S2`, issue a `SubjectProtocolManifest`, authorize subject
prepare-only or execution, or earn any VOY or D0-D8 credit.

Before subject access, the protocol declares one primary endpoint and fixes an
exactly-one terminal mapping. Required validity, control, or invariance failure
takes precedence as `fail`; if none fails but required evaluability is missing,
`insufficient` takes precedence. Only a valid, fully evaluable run can resolve
the primary endpoint as `positive`, `qualified_zero`, or `qualified_null`:

- `positive`: at least one candidate earns its branch-specific label within
  the frozen claim ceiling; an eligible structural target may proceed to
  `SCI-S3`, and the exact quantity may proceed to `SCI-S4` replication;
- `qualified_zero`: a fully evaluable candidate-count primary endpoint yields
  zero eligible candidates inside the `SCI-S1`-qualified detection region;
- `qualified_null`: a fully evaluable preregistered effect/comparison primary
  endpoint yields no qualifying effect inside its frozen sensitivity region.
  It is not a synonym for zero candidates;
- either qualified outcome authorizes no `SCI-S3` semantic target, but its
  bounded endpoint may proceed to `SCI-S4` replication;
- `fail`: an evaluable required validity, control, or invariance gate fails.
  No candidate is promoted, no threshold is retuned under the same protocol
  identity, and neither `SCI-S3` nor positive-effect replication is authorized;
- `insufficient`: sensitivity, support, coverage, witness, or evaluability is
  incomplete. It is neither a qualified zero/null nor a falsification and
  authorizes neither `SCI-S3` nor `SCI-S4` scientific replication.

Infrastructure-invalid attempts remain separately typed and follow the frozen
attempt/budget policy; they do not silently become a scientific terminal.

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
  equally; a zero-candidate report names the `SCI-S1`-qualified detectable region
  rather than claiming unrestricted absence.

Exit criteria:

- one clean protocol run without post-hoc discovery-threshold changes;
- the signed tag and independent snapshot resolve to the exact protocol and
  source digests before claim-bearing subject access. If the independent
  witness is unavailable, a plumbing-only attempt may record that absence, but
  the `SCI-S2` claim-bearing run remains blocked;
- every reported candidate links to all required null results;
- an independent rerun reproduces the persisted structural quantities within
  declared numerical tolerances;
- any Level 2G or Level 2T label is earned per candidate, not inherited from
  the run.

Completing `SCI-S2` does not establish semantics or SAE loss.

<a id="sci-s3"></a>
#### SCI-S3 — SAE gap and causal semantic validation (historical `M3`)

**Status:** future and conditional on an eligible positive structural target
from `SCI-S2`. If `SCI-S2` ends `qualified_zero`, `qualified_null`, `fail`, or
`insufficient`, `SCI-S3` is `not_run` or not applicable for that study; this is
not a software failure.

Each `SCI-S3` protocol freezes a finite resource budget and one exactly-one
terminal before held-out semantics or intervention endpoints are opened:
`positive` requires every preregistered predictive, causal, and control gate;
`qualified_null` requires a valid, adequately sensitive evaluation with no
predicted semantic/causal effect; `fail` records an evaluable adverse required
gate or falsifying direction; and `insufficient` records missing sensitivity,
support, coverage, or evaluability. No terminal is converted by extending the
same protocol after its budget.

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

<a id="sci-s4"></a>
#### SCI-S4 — Scientific replication and checkpoint dynamics

**Status:** future and conditional on a replayable positive quantity or a
`qualified_zero`/`qualified_null` from `SCI-S2`, or an eligible Level 3
quantity or `qualified_null` from `SCI-S3`. `SCI-S2`/`SCI-S3` `insufficient`
is not a bounded null.

Each `SCI-S4` replication protocol likewise freezes its source quantity,
tolerances, primary endpoint, and finite budget. It terminates exactly once as
`positive_replication`, `replicated_qualified_zero`,
`replicated_qualified_null`, `fail_replication`, or `insufficient`; supported
disagreement is `fail_replication`, missing evaluability is `insufficient`, and
neither may be relabeled by adding checkpoints or models after the frozen
budget.

Deliverables:

- checkpoint, seed, or scale replication where public models permit it;
- a preregistered public-checkpoint series that treats training step as a
  prospective control variable for candidate density and opposite-sign pair
  trajectories. Layer depth remains a within-model spatial/profile coordinate,
  not a temperature proxy; no Kosterlitz-Thouless or annihilation claim follows
  without the calibrated dipole resolution and branch-specific gates;
- explicit separation of adapter-induced observable differences from a
  scientific replication effect;
- a preregistered replication interpretation for positive, negative, and
  inconclusive outcomes.

Exit criteria:

- every replication binds the original protocol quantity, admissible
  tolerances, and all model/checkpoint-specific deviations;
- checkpoint-series conclusions remain within the calibrated dipole-resolution
  and detection-limit region;
- a negative or inconclusive replication remains a first-class artifact.

### Library lane

<a id="lib-l0"></a>
#### LIB-L0 — Research-package consolidation

**Status:** in progress. The package is installable and much of its mathematics
is framework-neutral, but repository-bound official experiments and broad
provisional surfaces are not yet separated from reusable library contracts.

**Historical planning alias:** the software/model-abstraction portion of `M4`.

Deliverables:

- small authority-free evidence primitives for bounded canonical JSON bytes and
  digest-before-parse. A shared primitive owns observation order only; typed
  reconstruction joins and all claim, authority, chronology, publication, and
  repository meanings remain with each domain contract;
- explicit policy-equivalence matrices before any consolidation of claim
  ceilings, authority facts, typestate transitions, atomic/no-replace
  publication, or historical pin verification. Those contracts remain
  version-owned and domain-local until two consumers prove that both the
  accepted inputs and failure semantics are identical;
- item-specific evidence contracts expressed as declarative schemas and data
  wherever doing so preserves their scientific distinctions;
- explicit `Workspace` or `RepositoryContext` injection for operations that
  require Git history or repository files; no reusable reader infers a Git
  root from `__file__`;
- an explicit boundary between framework-neutral `spirallens` APIs and
  repository-bound official experiments;
- an explicit model-observer boundary that keeps framework types out of core
  contracts; its public adapter protocol is promoted only in `LIB-L1`;
- core mathematical imports that remain free of Torch, Transformers, and
  Faiss;
- read-only generated status/schema/digest views whose authoritative inputs
  are the human-owned Fundamental Frame, Interpretation Ledger, and this
  roadmap for policy, plus canonical machine artifacts for observed bytes.
  Every view binds its generator version and input digests, is regenerated by
  a declared check rather than hand-edited, and has no authority of its own;
  policy conflicts resolve to the human-owned source, byte/status conflicts to
  the canonical artifact, and a stale projection fails validation;
- a public-surface budget and promotion rule that prevents experiment-specific
  helpers from becoming provisional exports by default.

The first bounded mechanism renders `docs/generated/lib_l0_status_v0_1.json`,
schema `spirallens.lib-l0-status-view.v0.1`, from the Frame, Ledger, Roadmap,
validator, three classification manifests, and generator bytes. Default output
is canonical JSON on stdout; `--check` observes committed/rendered byte equality
for bounded reads during that invocation and writes nothing. The view is
non-authoritative, and owner documents record no view hash. Freshness establishes no validation pass,
API/support, compatibility/portability, library maturity, `LIB-L0` completion,
release, science, authority, or D7 readiness/re-anchor.

The first namespace-scoped provisional library-admission observation is the
exact-seven `spirallens.contracts` root surface already owned by the ordered-export
manifest. SHA-256
`864092553149e4226ca5cc25675085c1e3bb9a724d23ed6d884419cb367bb4f0`
fixes `tests/test_contracts_library_admission.py`. The exact three CPython
3.11.16 / 3.12.14 / 3.13.15, Ubuntu 24.04 x86_64, locked-dependency jobs run
all 42 source nodes and exact 41 neutral direct-wheel nodes; only the
source-owned manifest/consumer join is absent from the wheel selectors. The
test binds the root/defining identities, enumerated behavior and failures, and
exact source/installed origins for `spirallens`, `spirallens.contracts`, and
its `calibration` and `math` defining modules.
One provisional source line makes default-generated `SampledLoop.parameter_values`
read-only like explicit inputs without a numeric value, signature, export, or
dependency delta. PR108 changes no production source, export, dependency,
manifest, validator, or report schema. This is a bounded source/direct-wheel
observation, not full library-test ownership, coverage of the other 552 exports
or the sdist-derived behavior route, installed deep-module or per-name
two-consumer admission, public API, or promotion. Historical source/D7 receipts
remain unchanged and unre-anchored; current readiness remains false.
`closed_library_allowlist_established=false` and
`closed_public_api_contract_established=false`; all distribution grants remain
false; support, stability, compatibility, portability, typing, and release remain
unestablished; `LIB-L0` remains in progress; no science, authority, or D7 state
changes.

Exit criteria:

- every promoted common primitive has two independent consumers and materially
  reduces duplicated evidence plumbing without merging holonomy, winding,
  authority vocabularies, publication outcomes, or other scientifically and
  operationally distinct types;
- wheel-installed library operations declare whether they are portable or
  require an explicit repository context;
- the reference adapter passes an internal conformance suite, with
  adapter-induced differences reported without being called replication;
- library tests run against the intended installed/source tree with origin
  verification and without hidden adjacent-worktree imports;
- synthetic/conformance fixtures for `pass`, `fail`, `insufficient`, and
  `not_run` can be loaded, rendered, and round-tripped without promotion or
  loss. No completed `SCI-S1` attempt is required for entry into `LIB-L1`.

The first attempted internal foothold was an authority-free canonical-JSON
source binding shared by the instrument-artifact and qualification loaders.
A scoped migration inventory found no third semantically compatible consumer:
every candidate either increased production lines, changed domain-specific
errors, or crossed a frozen chronology boundary. The abstraction was therefore
retired instead of being spread into unrelated evidence paths. The portable
instrument loader again owns its direct domain implementation; qualification
retains the observed digest-before-parse correction in one consumer-local
helper. Serialized bytes, public exports, artifact schemas, typed
reconstruction, and top-level domain exception classes, messages, and
validation order are unchanged; the retired private cause chain is removed.

The completed pay-down gate is recorded as `LIB-L0-CSB-001`:

- baseline commit:
  `41e1893f878a00c5e73ac101296aefe7f1ca5ae1`;
- production scope and final physical-line balance:
  - the absent/private kernel: `0 → 0`;
  - `src/spirallens/instrument_contracts/artifact_loader.py`: `128 → 128`;
  - `src/spirallens/qualification/persistence.py`: `440 → 438`;
  - total: `568 → 566`, therefore `-2` cumulative extraction debt;
- counter: physical lines computed with Python `str.splitlines()` over those
  files, treating the absent baseline kernel as zero;
- closure rule: the original `<= 0` requirement is satisfied by abstraction
  reversal, not by weakening the counter, deleting validation, or enrolling a
  semantically incompatible consumer.

Tests and documentation are excluded from this counter but remain required for
the reversal. The gate's successful rejection is not completion of `LIB-L0`:
any future common primitive must independently have two genuine consumers and
materially remove duplicated production plumbing. Retiring this internal
module changes current source-tree identity only; frozen artifacts and
historical pins remain unchanged, and any exact-current readiness re-anchor
must be a new versioned observation rather than a rewrite.

The first repository-context foothold is likewise internal and
non-authorizing. `build_current_qualification_engine_binding()` and
`run_public_example_plumbing()` retain their existing provisional public names
but now require a caller-supplied `repository_root`; the public-example CLI
requires the corresponding flag. A private `RepositoryContext` marker carries
only the normalized absolute path; construction performs no I/O or Git
discovery. Its narrow same-file comparison rebinds each migrated consumer's
actually imported source to the declared checkout, preventing execution from
one worktree from being attributed to another. It is not serialized and proves
no Git-root identity, cleanliness, ancestry, claim, chronology, or authority
fact. The D7 fixed zero-argument official producer is excluded from this
migration because its signature and imported-source identity are versioned
chronology inputs; changing it requires a separate protocol decision.
Advancement, runner, Faiss, and phantom context migrations remain open, so this
foothold does not satisfy the `LIB-L0` repository-boundary exit.

Against baseline commit `aee47f9cefb1c5fd445ad586471edd4712cb5178`, this
foothold adds `+109` physical production lines and `+0` public exports. Later
repository-context migrations must reuse this single private marker and report
the running production balance; they must not introduce a parallel context or
import-origin plumbing family.

The current extraction baseline and decision gates are recorded in the
[LIB-L0 extraction inventory](LIBRARY_EXTRACTION_INVENTORY.md), audited at
commit `a7e24f912ffeaa15a6b79bf200c39dccf9cd5746`. At that historical audit
coordinate the repository-only set was the exact 20 D7 v1
`confirmation_v1_*` modules plus two private Pythia-160M kernels: 22 modules
and 19,190 physical lines. The current fail-closed versioned manifest retains
those files and additionally classifies the 27 formerly shipped
`qualification/confirmation_*.py` modules as repository-only. It now
partitions all 182 `src/**/*.py` module paths into 133 wheel-present modules
(24 package initializers, two console-entrypoint runtime modules, and 107 other
shipped runtime modules) and 49 repository-only modules. The v0.10 diagnostic
proves the exact 133-member set through the
source tree, sdist, both wheel routes, and both fresh non-editable
installations and records
`closed_wheel_python_module_inventory_established=true`.

A second versioned manifest,
`distribution/spirallens_ordered_exports_v0_1.json`, schema
`spirallens.ordered-package-exports.v0.1`, closes only the static literal
ordered `__all__` declarations for all 24 classified package initializers: 559
namespace-scoped entries. The v0.10 diagnostic proves the same initializer
bytes and ordered declarations in the source tree, sdist, both wheel routes,
and both fresh installs, parsing installed initializer bytes without importing
`spirallens`. It records
`closed_ordered_package_export_inventory_established=true`.

A third versioned manifest,
`distribution/spirallens_installed_imports_v0_1.json`, schema
`spirallens.installed-import-conformance.v0.1`, closes the expected installed
import outcomes for those exact 133 modules under one bounded host-projected
environment contract. The v0.10 diagnostic applies that contract separately to
the direct-source and sdist-derived non-editable wheels. This is a
single-current-host observation, not a portability matrix. It uses one fresh
`-I -S -B`, 30-second process per module, a neutral working directory, and no
`PYTHONPATH`. Site initialization is disabled and `.pth` startup is not
executed; the fresh-wheel root and the exact host-distribution roots for the
three declared base dependencies are added explicitly. The six optional
prefixes are blocked, and a separate generic blocker rejects distributions
outside those declared bases. The repository-only validator parent uses
`packaging` supplied by the already-declared dev `build` toolchain; the
isolated children do not import it. The base runtime dependencies are
unchanged, and installed metadata has the exact 13 normalized `Requires-Dist`
records: three base and ten optional-extra requirements. The two routes have
equal normalized startup receipts. Each route observes 131 base-import
successes and two exact blocked-Torch model-extra outcomes:
`spirallens.adapters` and `spirallens.adapters.pythia`. The sole
blocked undeclared attempt is `charset_normalizer`, which remains unloaded;
the aggregate loaded third-party distributions remain the exact declared base
three. Runtime
list-valued `__all__` equals the static declaration for the 23 successfully
imported initializers and 554 entries; `spirallens.adapters` and its five
entries remain unavailable at the blocked Torch boundary. The historical
pre-boundary 159-member routes had outcome-manifest SHA-256
`8f885faab04cd796285d6263381172a4697fc310dafd96c504de44b4214187c7`.
Their adopted pre-projection live validation receipt has SHA-256
`2ce75371e7a8f39db66c136cf64c039f6f76fcbdf84b6f6b76b6bdf5f0b502b4`.
The separately retained preA/preB/post invariants bind that receipt to
validator SHA-256
`a08ddf98f8d7da985f0ed5029b999c0ab40d6b37a250e450a8df51a38a89575c`,
setup SHA-256
`da83e2ad642bef085948571a26bef52030abadc91f0cb5d8d3a2450160b0079f`,
manifest SHA-256
`d9a90a30514a64d561e3caaa5ab6309b5c205efa12a91bb93ec07cebe83c6795`,
and unchanged `src` inputs before this receipt-projection documentation was
added. Because the documentation
changed afterward, and `README.md` is embedded in distribution metadata, its
artifact hashes do not attest artifacts rebuilt from the later documentation
state.
The report records
`closed_installed_module_import_outcome_inventory_established=true` and the
strictly scoped
`runtime_successful_package_export_values_established=true`.

`spirallens.atlas.id_sweep` and `spirallens.atlas.engineering_run` are the two
later Atlas base-import successes. A source probe and both fresh-wheel workers
resolve all exact 20 defining/root/star identities with model prefixes blocked.
Neutral sweep hints and the public runner's exact model-free hints resolve; its
root identity, structural signature, and raw annotations remain fixed. On call,
the runner imports Torch and then the adapter before argument/root access;
`run_id_sweep` still imports Torch before adapter/config access. Default
resolved run-sweep hints, private-helper hints, and former private globals are
outside the claim. This is a bounded framework import boundary, not operation
portability, public API/protocol, support, release, D7 authority, or `LIB-L0` completion.

The private `spirallens._model_observer.BatchObservationProtocol` seam
separates the declared observation capability from the Atlas store's NumPy
import. An internal offline conformance check carries a reference
`PythiaAdapter` observation into `spirallens.atlas._capture_store`; those two
modules account for the two new base-import successes. The Tensor-backed
`BatchObservation`, public exports, artifact schema, and residual-hooks v2
capture contract remain unchanged. Protocol satisfaction is structural, not a
runtime `isinstance` gate. This establishes no NumPy-owned or value-neutral
observation record, public adapter protocol, portability result, or completion
of `LIB-L0`.

The v0.10 diagnostic runs one model-free probe against staged source and both
fresh-install routes. It requires six root/core/qualification origins under the
intended tree and equal canonical render, parse, `GateResult.from_dict()`, and
rerender for `pass`, `fail`, `insufficient`, and `not_run`, preserving state and
claim scope without negative-to-`pass` promotion. A passing report observes only
the four-state fixture exit subgate and one origin-verified source/installed
slice. It is not the full library-test exit, a runtime-artifact
schema or API change, support, full compatibility, portability, science,
authority, D7 readiness/re-anchor, release, or completion of `LIB-L0`.

These are physical-placement, static-declaration, and installed-import
closures, not a closed library allowlist or public API contract. The audit hook
begins only after isolated interpreter and standard-library probe bootstrap
and reports zero denied events inside a bounded
write/process/network/filesystem policy. It deliberately does not deny
`ctypes.dlopen`, `os.putenv`, or `os.unsetenv` and cannot establish side-effect
freedom. Module-process isolation does not prove combined import-order or
concurrent behavior. The probe does not resolve the 554 named exports or invoke
any operation. Its explicit dependency roots share host directories, so base
dependencies are neither freshly installed nor an isolated closure.
`runtime_export_values_established`,
`all_package_runtime_export_values_established`,
`export_symbol_importability_established`,
`side_effect_free_imports_established`,
`closed_public_api_contract_established`, and
`closed_library_allowlist_established` remain `false`; optional dependency
extras, portability, authority, and scientific meaning remain orthogonal. In
particular, the wheel now retains exactly 19 model-free D0-D6 qualification
modules and all 115 ordered `spirallens.qualification` exports, while all 47
`qualification/confirmation_*.py` D7 implementation modules remain in source
as repository-only members. This closes that physical D7 distribution
boundary without changing D7 source or history. Legacy repository-inferred
operations and other open allowlist, compatibility, portability, and release
gates keep the wheel from being library-grade. The report's authority,
`lib_l0`, library, portability, public-API, and
scientific grants all remain `false`, so `LIB-L0` remains in progress and
VOY-V4 remains unauthorized. A current repository test-file count is
intentionally not frozen here. The former sdist's 106-file test surface was an
implicit partial subset: some carried tests depended on
omitted helpers or deliberately repository-only experiment modules. It was not
a self-contained replay, installed-wheel conformance suite, or maturity
receipt. The v0.10 diagnostic now requires the sdist's top-level `tests` path to
be absent and records `sdist_test_surface` as exact `absent / 0 / []`. This is a
distribution-role boundary, not a full sdist inventory, replay result,
compatibility or portability grant, API promotion, library milestone,
scientific claim, or authority record.
Future package data, extension modules, namespace/generated modules, or
bytecode-only distribution support requires a reviewed versioned
classification/schema successor.

The current diagnostic remains a proportionate fail-closed ratchet. Its
anti-bloat successor trigger is now satisfied by the private,
repository/build-only `distribution/_installed_import_policy.py` seam. The
seam is standard-library-only and performs no I/O or parsing; it owns only
immutable installed-import metadata and the deterministic canonical JSON
projection passed from the validator parent to isolated workers. Workers do
not import it and independently reject projection shape, type, empty-value,
and expected-outcome drift. Setup and validator retain independent manifest
and `pyproject.toml` parsers, validation, error boundaries, and adversaries.
The validator also uses one generic exact-file reader for the reviewed sdist
members. The sdist must contain exactly one regular byte-identical policy file,
while wheels must contain none.

Against baseline `ef84d7e2107fb4ff9d931e34523f3e942e9244ad`, physical
production lines across `setup.py`, `scripts/validate_distribution.py`, the
policy file, and `MANIFEST.in` change from 6,130 to 6,098 (`-32`). The four
exact duplicated policy-literal blocks change from 66 physical occurrences,
including 33 redundant lines, to zero setup/validator duplicate excess
(`33 -> 0`, 100 percent). This is maintenance of a private build boundary, not
a library milestone: no installed-import schema or outcome, diagnostic report
semantics, `src/spirallens` runtime, export, dependency, API, portability,
library or `LIB-L0` status, scientific claim, or authority record changes.

The next bounded consolidation, measured against baseline commit
`be274333e77d7518cb21ddb6afda3d62222e4b6c`, shares one standard-library-only
held-file byte primitive between exactly two production domains:
`access.descriptor` and `referents.loader`. With physical lines counted by
Python `str.splitlines()`, `_held_file.py`, `access/descriptor.py`, and
`referents/loader.py` change from `0/517/179` to `85/457/105`; the total changes
from `696` to `647`, a net `-49` and 25.8 percent of the audited 190-line
duplicated block, with no added export or dependency. The frozen equivalence
surface preserves each wrapper's path/digest preprocessing order, returned
bytes, domain exception type and message, direct OS cause/context, policy
no-cause/context, and descriptor cleanup order. The primitive remains private
and POSIX `dir_fd`-oriented: `O_NOFOLLOW` is conditional on host support, a
FIFO can block at open before the regular-file check, and the held-descriptor
plus before/after metadata checks are not a proof against every hostile race or
TOCTOU condition. Parsing, digest validation, read traces, claim and authority
meaning remain domain-local. This pay-down changes no public API, schema,
artifact, protocol, scientific or VOY authority, does not authorize VOY-V4,
and does not complete or advance `LIB-L0`.

A later incremental audit at baseline `da10e358e6a6fc009992c5bec3dc7bf0e9d6bca8`
reuses that existing private module's directory-chain traversal for three independent
roles: bounded readers, the access descriptor writer, and the neighbor-audit reservation
publisher. `_held_file.py` / `access/descriptor.py` / `audit_output.py` change from
`85/457/292` to `85/437/273` physical lines, total `834 → 795` (`-39`); the three
opener definitions change `65 → 21` (`-44`, 67.7 percent). Domain wrappers retain their
exact relative-path errors, and leaf operations, identity, fsync, no-replace, recovery,
publication, and authority remain local. This adds no module, export, external dependency, API,
support, security, portability, D7, science, authority, or VOY state and does not complete
or promote `LIB-L0`.

A subsequent narrow audit at baseline `c9167ae76757c287d7d75223fd2a33be23e5c777`
reuses the byte-identical private lowercase SHA-256 syntax validator already owned by
`neighbors.contracts` in execution-freeze, neighbor-audit, and the downstream audit
receipt. Execution-freeze and neighbor-audit are the two independent consumers; the
receipt is not counted again. The four-file scope changes from `8259` to `8232` physical
lines (`-27`), while validator implementations plus imports change `32 → 11` (`-21`,
65.6 percent). Calls retain exact input order, returned string identity, and raw
`ValueError` message/cause/context; private helper identity, module, and traceback frame
are not compatibility claims. No module, export, external dependency, schema, D7
re-anchor, API, support, security, science, authority, VOY, or `LIB-L0` state changes.

The next private consolidation at baseline `7782b24c350e1ee5f6aeb8e942e82e7063734bb0`
keeps `access.contracts` as the existing owner of mapping, exact-key, digest, and enum
schema validators and reuses them in terminal lifecycle records and value-access lineage.
The three production files change from `919/566/229` to `919/526/221` physical lines,
total `1714 → 1666` (`-48`); validator definitions plus import bindings change `74 → 40`
(`-34`, 45.9 percent). Exact production inputs, validation order, return identity, domain
error type/message/cause/context, and label interpolation remain fixed. Identifier, fact,
typestate, derivation, and authority logic stay local. This adds no module, export, external
dependency, schema, API, support, security, D7 re-anchor, science, authority, VOY, or
`LIB-L0` state change; historical source receipts remain immutable and unre-anchored.

The following bounded split, measured against baseline commit
`a1d6c615da9e39247afa0332658e9aee7b24bb5a`, moves mutable Atlas capture
storage into private `_capture_store.py` while keeping manifest readers in
`store.py`. The two independent reader consumers are `metrics.candidate_pairs`
and `atlas.engineering_receipt`. A fresh non-editable wheel verifies that the
reader import closure may load NumPy and PyYAML but loads none of `torch`,
`transformers`, `huggingface_hub`, `safetensors`, `spirallens.adapters`,
`spirallens.atlas.id_sweep`, `spirallens.atlas.engineering_run`, or
`spirallens.atlas._capture_store`. The four-file production scope
`store.py` / `_capture_store.py` / `id_sweep.py` / `__init__.py` changes from
`1226/0/589/57` to `760/492/590/78` physical lines, or `1872 → 1920`
(`+48`); the reader store itself loses 466 lines. This boundary split satisfies
the extraction gate by emptying its forbidden import set, not by reducing total
production LOC. Lazy capture exports preserve the ordered 20-name
Atlas `__all__`, symbol identities, reader signatures, defining modules, and
exception identities. It does not make all of Atlas framework-neutral and
changes no public API, dependency, persistence schema, artifact, protocol,
scientific or VOY authority; it neither authorizes VOY-V4 nor completes or
advances `LIB-L0`.

The next bounded pay-down, measured against baseline commit
`366d195f112bc3b95f36504e8a711029c71e6161`, replaces four duplicated strict
PyYAML mapping-loader definitions with one private `core._strict_yaml` factory.
The independent production consumers remain `contexts.loader`,
`instrument_contracts.registry_loader`, `synthetic.protocol`, and
`atlas.engineering_protocol`. Across those four files plus the new helper,
physical production lines change from `3081` to `2987`, a net `-94`; the
audited extraction surface changes from `158` to `64` lines, a 59.5 percent
reduction, with no added export or dependency. The shared policy is limited
to SafeLoader alias, merge-key, string-key, and duplicate-key handling. Each
wrapper retains its own size, source-digest, UTF-8, domain-schema,
canonical-digest, exception-prefix, and observation order. Exact wrapper tests
preserve standard safe-tag behavior,
anchor-only acceptance, downstream nonfinite handling, wrapped PyYAML causes,
and raw recursion failure. The semantically different CLI, neighbor-receipt,
and ordinary `safe_load` families remain outside this primitive. This
deduplication changes no public API, persistence schema, artifact, protocol,
scientific or VOY authority; it neither authorizes VOY-V4 nor completes or
advances `LIB-L0`.

The subsequent array-fingerprint review at baseline commit
`6273b3601a7f38947146677cccbb3ebf0ac876ed` is a bounded rejection, not an
extraction. The graph, qualification, and representation-estimator helpers
produce identical `dtype.str` / shape / NUL / C-order-byte fingerprints for
stable ndarray metadata across 21 audited case families. Their unrestricted
callable contracts are not exact, however: graph and qualification construct
the digest from the first metadata observation and return a later metadata
observation, while the representation estimator returns the first observation
and hashes a later one; their digest-only callables also observe metadata a
different number of times.

More importantly, `src/spirallens/qualification/common.py` remains the exact
10,613-byte D7 v1 trust-root member with SHA-256
`a884545702c374def8df6fd9eb1fe0c3944b93f77cea3d50e9c6c3b5b0e648cf`
at reviewed source S, commit A, commit B, and this review baseline. The current
direct executing-source gate still joins those live bytes to reviewed S.
Changing the file or making it depend on a new unbound helper would introduce
a new, earlier deterministic trust-root failure; it must not be justified by
weakening the historical verifier. This statement does not claim that the
entire commit-B verifier is currently refreshable from the later descendant:
it already reports a separate post-S Python path-set drift after the direct
source gate. Excluding the trust root leaves only 33 local function lines in
the graph/representation pair, and no reviewed design demonstrated the
inventory's 20-line net-reduction threshold. Therefore no production, export,
dependency, wheel, schema, or test helper was added. The rejection preserves
historical evidence and does not complete `LIB-L0`, authorize VOY-V4, or alter
any scientific or authority state.

The following namespace-export repository-context review at clean baseline
`a2b7a01f97dc8bbc1e83a9d30142bcff009bbaf0` is also a bounded rejection. The
exact 24-initializer, 559-entry ordered namespace surface has 175 eager
operations, 264 eager classes, 109 eager values, four `TypeAlias` declarations,
and seven lazy Atlas exports. Static lazy-binding resolution closes the entry
kinds as 178 operation entries / 175 unique functions, 271 types, and 110
values, with zero unresolved entry kinds. These are namespace coordinates and
source roles, not a public API or maturity inventory.

Repository-context policy is defensible for only 14 operation entries. Eight
require explicit context:
`spirallens.atlas:run_public_example_plumbing` and
`spirallens.qualification:{build_current_qualification_engine_binding,prepare_closed_d0_d5_selection_protocol,prepare_selection_launch,publish_closed_d0_d5_preseed_readiness_artifact,verify_closed_d0_d5_preseed_source_readiness,verify_protocol_source_binding,verify_protocol_source_binding_successor}`.
Three accept optional context with a repository fallback:
`spirallens.qualification:{advancement_source_binding_sha256,build_current_advancement_source_binding,validate_advancement_decision_source}`.
`spirallens.qualification:run_and_publish_calibration_selection` directly
infers a repository, while
`spirallens.neighbors:run_faiss_hnsw_qualification` and
`spirallens.synthetic:emit_representation_phantom_bundle` do so transitively.

At that review the remaining 164 operation entries / 161 unique functions
stayed `not_established`. No-observed repository dependency is not portability
evidence, and `__all__` membership grants no support, API, compatibility, or
maturity status. A normative 559-row manifest would duplicate the existing
ordered-export inventory, while a compact default would launder those unknowns
into repository independence. A new parser and diagnostic projection would add
validation surface without satisfying the repository-context exit criterion
above. Therefore no manifest, parser, report field, schema, or production code
was added.

The first bounded follow-up at clean baseline
`e55a05e812e6fefda8e5924e0ba483b35fc6840e` classifies only
`spirallens.core:{canonical_json_bytes,canonical_json_sha256,parse_canonical_json,sha256_bytes}`
as `implementation_repository_context_not_required`. Their defining
`spirallens.core.canonical` functions are bound through the unchanged core
initializer and canonical source SHA-256 values
`3a1af1d86ac24e9796d5f0961180352c669e5dd37ed46e8fa2c0cea9dc31df1d`
and
`0a39f0b896e0ae1c2af8d1910dd37afae31ad563c20df785973a91ff4cadac5e`.
The focused 6,101-byte AST source-policy test, SHA-256
`f2e2580eb3c017a21508887b9d350f00bfb4e7fafb146a2b871a20bcdc7dc5d0`,
passed once and fails closed over exact imports, top-level calls, defining
targets, local call closure, call syntax, and forbidden repository, file,
environment, process, network, and dynamic-import names.

This is an implementation-owned repository-context declaration only. Receiver
protocol methods, including custom `Mapping` methods, may execute caller code,
so the audit does not establish purity, callback freedom, side-effect freedom,
safety, or portability. It also grants no support, public API, compatibility,
stability, or maturity. The audit now covers 18 namespace coordinates / 18 function
identities. The 160 unknown coordinates are 157 never-audited identities plus
the `spirallens.instrument_contracts` aliases `canonical_json_bytes`,
`canonical_json_sha256`, and `parse_canonical_json`: those three reach the same
audited targets, but their namespace import closure remains unaudited and they
inherit no declaration. No runtime, export, dependency, schema, report, public
API, `LIB-L0`, science, authority, or VOY state changes; VOY-V4 remains
unauthorized.

The bounded core-promotion preflight at clean baseline
`973f617add33817de279286baee39a608ea5fe54` freezes the 171-line,
7,420-byte `tests/test_core_canonical_compatibility.py`, SHA-256
`30d5088bfaf76639208c56b0201589b99a28c7656f382d431ddfb9c8f307ec1f`.
Its focused gate collected and passed six tests, fixing the exact ordered
seven-name `spirallens.core` surface, defining and legacy-module identities,
four callable signatures and annotations, type aliases, representative success
values, selected exact failures, and validation order. Existing policy evidence
establishes independent shared-codec use at defining or legacy leaf paths; the
four functions have 7 / 7 / 5 / 2 wheel-present top-level namespace families,
while exact `spirallens.core` root-coordinate production consumers remain zero.
A coherent eventual promotion covers all seven names, not only the four functions.
At clean baseline `da231477f91dc3d34e8f775f878d3a9992d355f3`, the deterministic
current-source README is 116,777 bytes at SHA-256
`fb868d4186a8811a4d136ae8d58d8c09cfa8fc952836b1843ae747f098e1d2f3`; its
dedicated 90-line, 3,943-byte test has SHA-256
`36d86cf8f3bdd3567cd92fe430d6a39eca3c24974da49810773f20f46dc4d457`.
The focused pair collected and passed seven tests without model, network, or
private data. The example and adopted policy grant no promotion. The intended
clean-wheel matrix has since passed for the exact recorded tuples; the separate
review below retains HOLD under the remaining promotion and release gates.

This test-and-documentation preflight changes no production source, API, export,
dependency, schema, artifact, receipt, D7 re-anchor, `LIB-L0`, scientific,
authority, or VOY state. It proves no cross-version or cross-host portability,
installed-distribution behavior, resource boundedness, safety, purity,
exhaustive failure surface, or custom-`Mapping` callback behavior.

The clean-wheel follow-up merged at main
`2ae687a13f9c0cefe5a07d3cbd1e7e3f6c26853d`; GitHub Actions push run
`31708106596` passed direct non-editable wheel jobs at these exact coordinates:

- CPython 3.11.16, `ubuntu24/20260720.247.2`, kernel `6.17.0-1020-azure`, wheel SHA-256 `5e35b54379d4c2fef7cbdaf769ea1da4eefc0d3c0096f9be96e1c97522832c72`;
- CPython 3.12.14, `ubuntu24/20260810.271.1`, kernel `6.17.0-1022-azure`, wheel SHA-256 `ee8d71c4076e9dc341868128d96fd68cabe0c75706cd0daaf6d2451335a57303`;
- CPython 3.13.15, `ubuntu24/20260810.271.1`, kernel `6.17.0-1022-azure`, wheel SHA-256 `9b2b40768fdd64bc9d66935464e6d337bdc5442c628ca658148e7ad34c78021d`.

All ran on Ubuntu 24.04.4 x86_64 with glibc 2.39 and the exact locked 13-package tuple
`build==1.5.0`, `iniconfig==2.3.0`, `numpy==2.4.6`, `packaging==26.3`,
`pip==26.2.1`, `pluggy==1.6.0`, `pygments==2.20.0`,
`pyproject-hooks==1.2.0`, `pytest==9.1.1`, `pyyaml==6.0.3`,
`scipy==1.17.1`, `setuptools==84.0.0`, and `wheel==0.48.0`. Before the
frozen compatibility file was imported, the separate probe established the
exact three installed module origins, ordered exact-seven identities, absence
of its eight listed forbidden modules from `sys.modules`, and no workspace
entry in `sys.path` or literal workspace path in `.pth` files; the frozen test at SHA-256
`30d5088bfaf76639208c56b0201589b99a28c7656f382d431ddfb9c8f307ec1f`
then passed 6 / 6 in every job. The workflow is 139 lines / 5,921 bytes at
SHA-256 `3239f43eefa6f391ae8360027b54a519ca1a516e255418157c60287dd192c0b2`;
the probe is 141 / 5,257 at `1802abb986897723a35fab6564086740f9f086f7eec448893658f9a6ae87c68c`;
the lock is 36 / 1,997 at `e95cd686c67e2d5dbb37aa95bac5ea3245a28cffd479957fc26931a9523f42d7`.

This clears the clean-wheel prerequisite only for those observed tuples. The
review qualifies 5 / 7 exact names, but `JsonScalar` and `JsonValue` each have
zero independent production consumers. Coherent exact-seven promotion therefore
stays rejected and on HOLD, not designated or active. The selected six tests are
not full compatibility evidence, and there is no PEP 561 typing claim.
Hosted logs are non-durable observations, not artifacts or support, stability,
or promotion receipts. They establish no other OS, architecture, Python patch,
runner image, dependency tuple, sdist parity, reproducible wheel-byte identity,
typing, exhaustive behavior, resource, safety, purity, whole-package
portability, `LIB-L0`, science, authority, or VOY change. These later
documentation bytes were not in the tested checkout and are not attested by
the run or its wheel metadata.

Repository `0.2.0` source/build metadata is an unreleased candidate and
activates no protection; merge, build, or tag is not a publication receipt, and
historical `0.1.0` compatibility is unattested. An actual policy-bearing `0.2`
release would activate only the prospectively designated `spirallens.__version__`
boundary. Core exact-seven remains on HOLD; if `0.2` ships on HOLD, its activation
is earliest `0.3.0`. The historical D7 `spirallens==0.1.0` lock and receipts stay
immutable. Their re-anchor was exact-current at issuance; this candidate changes
fixed v0.1 execution-source members, so current live readiness is false and no
successor re-anchor is created. Release still requires equal owners, a new
final-byte matrix, and a published-install receipt. This review changes no
release or claim state.

At clean main `58ce3e19521934fc3b0c20b1fb35fefca28afcf6`, equal owners and
main run `31719129800` closed the selected direct-wheel matrix; validator v0.9
separately passed the sdist, direct wheel, sdist-derived wheel, and both fresh
install routes. These nondurable candidate observations are not a release or
support grant: build isolation was not hash-locked and no public-index install
was tested. Publication stays HOLD pending an explicit human release decision,
a reviewed protected/pinned publish mechanism, an exact-final-commit rerun
after any distributed-input change, immutable tag/artifact provenance, and a
neutral published-index install receipt. No tag, upload, release, support
activation, core promotion, D7 successor, science, authority, or VOY state is
created; these later docs are outside the observed checkout.

The last declaration-only candidate, at clean baseline
`65a567659200ac41c5a15329af1074239b525ac5`, covered exactly
`spirallens.gauge:{orthonormal_frame,principal_angles,procrustes_connection,track_subspaces}`
and `src/spirallens/gauge/{__init__.py,procrustes_connection.py,subspace_tracking.py}`.
The owned closure was semantically eligible with no observed repository, file,
environment, process, or network dependency, but its honest formatted
non-import AST ratchet was 230 lines, above the hard 220-line gate. It was
withdrawn rather than obscured by opaque digests or a shared analyzer; no test
or declaration was adopted. Counts therefore stay 18 coordinates / 18 audited
identities, with 160 unknown = 157 never-audited identities + three unaudited
`spirallens.instrument_contracts` aliases. Mechanical declaration-only rollout
ends here. At clean baseline
`20409385eda0e0922772f08137f02ed8fc54d012`, the exact optional-fallback group
`spirallens.qualification:{advancement_source_binding_sha256,build_current_advancement_source_binding,validate_advancement_decision_source}`
was rejected for migration. `advancement_source_binding_sha256` requires the
keyword but accepts `None`; the other two also default it to `None`, so removal
is an accepted-input and public-signature break. Exact source SHA-256 values are
`7001959db17fb2d6c44fcdca024cc6ffc22b4df74a0a20333e94e113e470cc0a`
for `advancement.py`, `ce82f280348cbe4a5a21881c6dfea6d7a66d5a3e502e0ef00e27060350326f50`
for `_repository_context.py`, and
`e000cddd999a78af5911ca00325f0c6cb9da9e1a776311e66a629c8042d3b879`
for `qualification/__init__.py`. Advancement remains an exact D7
critical-runtime source/chronology member; no frozen binding is rewritten or
re-anchored. A `samefile` gate changes repository acceptance, validation/error
order, and TOCTOU behavior, while a new wrapper preserves the old fallback and
expands the surface. Both are rejected. Removing the 11-line resolver from the
217-line cluster yields at most `-5.1%` and fewer than 20 lines, below the
materiality gate. Counts stay 18 / 18 and 160 unknown.

At clean baseline `9eeec4234790babae22989f36f4ad94c5eef94df`, the Faiss transitive-context audit rejected every migration shape. The exact exported signature is
`(output_path: str | Path, *, worker_runtime_contract: Mapping[str, str] | None = None) -> FaissHNSWQualificationReceipt`; it has no repository argument. Its sole production
caller, the CLI preflight, also independently infers its root from `__file__`. The runner
captures source twice, each through 10 Git subprocesses including `ls-remote`; its
reporter-first happy path launches 25 subprocesses overall and accepts mixed physical
origins with parent A and worker B.
The 119-line source capture plus 200-line exported runner total 319 lines; replacing one
inferred-root line is about 0.3% and meets neither the 20-line nor 20% materiality gate,
with only one production consumer. Required context changes accepted inputs and
failure/observation order; optional context retains the fallback; a wrapper retains the
legacy coordinate while expanding exports. Reviewed SHA-256 values are
`ed29de5a89284d57b2a3628debc3cd8a8fe1586522fab5e02c2506778358ba92` for the runner,
`ce82f280348cbe4a5a21881c6dfea6d7a66d5a3e502e0ef00e27060350326f50` for the context,
and `934695307a3b116805a7115a95b75dd411d61089697e31e3c3d0c94919bef4f2` for the CLI.
The runner is a historical D7 C1/C2 source member, not a direct `_CRITICAL_RUNTIME_MODULES`
trust root; historical receipt `3c8c136c1e0dbbd84033b3c7144708b496e79bedc21dd9d5768494d37ba46b76` remains frozen and unre-anchored. Faiss stays transitively inferred; counts stay 18 / 18
with 160 unknown. At clean baseline `8cc2a594ceb25697f276d8c56bc0c718131dbcff`,
the phantom audit also rejects every migration shape. The exact exported signature is
`(protocol_path: Path, output_dir: Path) -> EmittedRepresentationPhantomBundle`; its
sole production consumer is the CLI adapter. The reviewed 301-line cluster
is the 21-line Git helper, 27-line revision verifier, two-line root helper,
23-line registry resolver, and 228-line exported emitter. Replacing its one
inferred-root expression is `1 / 301`, about `0.33%`, below both materiality
gates. Required context breaks accepted Python/CLI inputs and inserts a new
root/origin observation into the existing protocol load, generator-source/Git
verification, registry resolution/digest, and staged/published-output validation
order. Optional context retains inference; a wrapper retains the legacy
coordinate and expands exports. The emitter is a historical D7 v0
C1/item21/item22 and v1 C1/C2 source member, but not a direct
`_CRITICAL_RUNTIME_MODULES` trust root. It is distinct from the frozen P1
protocol and `representation_phantom.py` generator; neither frozen byte set nor
historical receipt is rewritten or re-anchored. Phantom remains transitively
inferred; counts stay 18 / 18 with 160 unknown. Repeated context-rejection
reviews stopped here; the completed core promotion audit retains HOLD. No production source,
test, schema, artifact, report, receipt, re-anchor, runtime, export, dependency, public API,
portability, maturity, network-free, `LIB-L0`, science, authority, or VOY state changes.

<a id="lib-l1"></a>
#### LIB-L1 — Library alpha (historical `M5`)

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

<a id="lib-l2"></a>
#### LIB-L2 — Library beta (historical `M6`)

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

<a id="lib-l3"></a>
#### LIB-L3 — Stable library 1.0 (historical `M7`)

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
- supported pre-1.0 surfaces are distinct from stable 1.0 contracts;
- this policy starts with its first release; adoption is not a release, and historical `0.1.0` compatibility is not attested;
- patches preserve callable coordinates/signatures and keep documented successes and documented failure boundaries backward-compatible;
- patches preserve the `spirallens.__version__` coordinate, `str` type/value format, and release-reporting semantics; its value tracks the release;
- their breaking changes or removal are minor-release-only, after a
  deprecation announcement in at least one prior minor and a migration note;
- pre-1.0 support promotion is minor-release-only and reviewed; stable status is a 1.0 transition;
- after any pre-1.0 core promotion, the exact seven legacy
  `instrument_contracts.canonical` identities and exact four
  `instrument_contracts` root aliases remain identity-preserving through
  `0.x`; they are not currently deprecated, and the whole namespace remains
  provisional;
- Python support covers only an exact Python patch, OS, architecture, and dependency-version tuple whose clean-wheel jobs pass;
- `requires-python` metadata and classifiers are not support receipts;
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

- public `SCI-S1` fixtures remain `role=example` and `claim_eligible=false`;
- discovery and held-out contexts live in separate frozen `SCI-S2` artifacts;
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
| Instrument refinement indefinitely postpones a claim-bearing run | Freeze a finite `SCI-S1` revision/resource budget and transition rule; advance when all gates pass, stop `insufficient` when qualification does not, and treat an `SCI-S2` zero-candidate run as a qualified null only inside the calibrated sensitivity region |
| A caller record or serialized token masquerades as launch authority | Treat canonical bytes as inputs only; derive the same-call transition inside one fused verify-and-exclusive-start operation, emit no reusable capability, and reobserve the declared source/runtime surface, physical identity, and absence at the transition |

## 11. D7 operations ledger and immediate next plan

The ordered entries below have the fixed canonical IDs `D7-OPS-01` through
`D7-OPS-29`. Their numeric positions are historical navigation aids, not a
second identity system. Completed entries are never renumbered; a future
insertion is appended or introduced in a versioned successor ledger.

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

1. <a id="d7-ops-01"></a>**D7-OPS-01** — adopt and review the Fundamental Frame, branched claim taxonomy, and
   historical interpretation ledger;
2. <a id="d7-ops-02"></a>**D7-OPS-02** — register competing field hypotheses F0–F4 with transformation laws, fit
   scopes, and claim ceilings — implemented as the strict, outcome-excluded P0
   registry;
3. <a id="d7-ops-03"></a>**D7-OPS-03** — define canonical substrate, graph, support, geometry-field,
   order-parameter, connection, discriminated loop, and calibration artifacts
   — implemented as metadata-only experimental v0.1 schemas;
4. <a id="d7-ops-04"></a>**D7-OPS-04** — define a canonical closed-world bundle manifest, resolve exact artifact and
   payload closure, and validate selected cross-manifest metadata joins —
   implemented as a closed-integrity validator that streams opaque payload
   bytes only for length and SHA-256 verification;
5. <a id="d7-ops-05"></a>**D7-OPS-05** — add a separately constructed Cartesian Fourier family with the exact
   nonzero-with-core, null-with-core, null-without-core, and
   prerequisite-failure controls — implemented in the D0-D5 engine;
6. <a id="d7-ops-06"></a>**D7-OPS-06** — consume deterministic mutual-kNN, fixed-radius, and shared-neighbor
   constructors through distinct field/cycle axes on the exact discrete
   domain — implemented for the closed selection engine;
7. <a id="d7-ops-07"></a>**D7-OPS-07** — implement separate core-only and loop-only evidence paths, execute the full
   field-graph by cycle-graph by loop-role matrix, and require a substantive
   field-output effect-size sentinel — implemented without integer or topology
   authority;
8. <a id="d7-ops-08"></a>**D7-OPS-08** — freeze nonnumeric failure semantics, exact required stress strata,
   all-primary pass, coverage/abstention/recall/specificity, source/evidence
   roots, and one-attempt terminal chronology — implemented at the engine and
   schema level;
9. <a id="d7-ops-09"></a>**D7-OPS-09** — commit that engine; commit exact canonical readiness/protocol/freeze
   artifacts as F; persist a launch intent before one exclusive claim; commit
   the store freeze, intent, claim, and descriptor as G; derive and revalidate
   exact G authorization; then perform the live source verification and atomic
   execution-start transition, the one-shot D0-D5 selection, and atomic
   publication of either its fully validated result or typed failure —
   completed with all six Cartesian-surrogate-scoped gates passing;
10. <a id="d7-ops-10"></a>**D7-OPS-10** — seal the exact surrogate profile and a construction-diverse confirmation
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
11. <a id="d7-ops-11"></a>**D7-OPS-11** — freeze post-selection descriptive analysis separately from the value-blind
    D7 structural gap matrix — recorded as two canonical, non-authorizing
    research artifacts; the descriptive lane cannot tune D7, and the gap lane
    cannot read the terminal values, name a candidate, or compute progress;
12. <a id="d7-ops-12"></a>**D7-OPS-12** — land the spectral-moment draft foundation: for ordinary or novel
    construction, exact four-case development generation plus a closed typed
    draft reconstructed only from the authoritative committed-D6 loader receipt.
    Its current internal `v0.2` identity, now preserved as a canonical
    historical body inside C1, excludes
    validation-time current-loader HEAD/digest fields while retaining typed
    receipt validation, so unchanged inputs are commit-stable. The draft
    remains unpersisted as a standalone/public artifact. This is not a D7
    full-design freeze: it does not
    complete same-schema construction-diversity review, selects no
    confirmation seed or execution inventory, persists no receipt, admits no
    family, exposes no runner/result, and leaves D7/D8 `not_run`;
13. <a id="d7-ops-13"></a>**D7-OPS-13** — close the seed-free D7 execution topology before choosing official seeds:
    reconstruct the full authoritative parent protocol; translate all three
    stresses explicitly; generate the exact 64-primary, 192-core, and
    1,152-loop seed-slot inventory; and exercise the exact crossed
    graph/field/blind-core/continuous-loop path on permanently excluded
    development seeds without producing a gate, result, or terminal —
    implemented. This step also records the newly discovered D6 v0.1
    incompatibility: required cells and stress-strata bodies contain selection
    seeds and seed-bearing IDs, so structural projection equality is true
    while exact parent-manifest satisfaction and admission remain false;
14. <a id="d7-ops-14"></a>**D7-OPS-14** — encode a proposed successor-only fulfillment rule without rewriting D6:
    graph-axis and threshold bodies remain exact, while cells/stress receive
    distinct successor identities whose structural projections match —
    implemented as an internal `v0.1` factory and strict reader. The historical
    proposal remains unreviewed and ineffective for admission; C1 preserves it
    unchanged and separately encodes the successor review contract without a
    repository-review attestation. Historical D6 v0.1 exact admission remains
    false;
15. <a id="d7-ops-15"></a>**D7-OPS-15** — create **C1**, the atomic and strictly reloadable stable seed-free
    candidate — completed at
    `experiments/qualification/d7_spectral_moment_confirmation_v0_1/c1-seed-free-source-set.json`.
    It binds the design, declared static-bounded construction-diversity review,
    D7 implementation registry, aggregation application, successor review
    contract, and complete declared `src/spirallens/**/*.py` plus
    `pyproject.toml` source set. It deliberately embeds no future commit,
    repository-review attestation, C2 receipt, official seed, admission, or
    execution authority; declared source set is not declared Git source-set
    closure;
16. <a id="d7-ops-16"></a>**D7-OPS-16** — create **C2** as the unique receipt-only child of the exact clean
    post-merge C1 commit — completed. C2 binds
    `e58a8169b41be688628ab7dda583e68088d3affc`; its unique
    receipt-introduction commit is
    `2f4e715a951211af8ca0ca4f6b2f7473134bf92b`. The committed loader verifies
    ancestry and every declared C1 source blob. C2 does not execute historical
    code or attest Python/native runtime, transitive dependencies, in-process
    identity, hostile-local-mutation resistance, or current compatibility;
17. <a id="d7-ops-17"></a>**D7-OPS-17** — only after C2, first define the immutable replay target independently from
    the launch/claim/start/outcome attempt envelope — implemented at the
    contract-specification level by the canonical, unpersisted
    `D7ReplayTargetContractSpec` and `D7AttemptEnvelopeContractSpec`. Neither is
    a replay-target or attempt instance. The latter fixes an append-only
    declaration → authorization → exclusive claim → start →
    scientific-result-or-failed-attempt → manifest → consumption model,
    rather than one mutable nullable object. The future target is exactly
    Level 0 with an all-false local authority vector. Do not create a
    placeholder result to stand in for any of these objects;
18. <a id="d7-ops-18"></a>**D7-OPS-18** — expose the concrete inputs needed by the later operational boundary
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
    cannot be used to reclassify a scientific outcome. The contract reserves
    an external execution identity for later start authority, but neither the
    evidence-only prefix nor the item-20 structural-start bytes establish
    `started_unresolved`. A visible structural start without a terminal blocks
    retry; only future official reauthentication of its exact authority
    evidence and durable start could establish that named lifecycle state.
    The caller-supplied start record plus terminal absence is only
    `caller_supplied_start_record_present_terminal_absent`; every terminal
    entry is `terminal_path_present_unverified`. It establishes neither
    execution nor `started_unresolved`, and isolated replay is rejected before
    persistence. Authoritative target/attempt instances and replay comparison
    remain deferred. The separately
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
19. <a id="d7-ops-19"></a>**D7-OPS-19** — implement the atomic result/failed-attempt terminal transaction,
    authenticated external-witness verification/finalization path, and
    eventual runner mechanics in a separately reviewed sequence —
    **implemented as deep-internal mechanics without an official run**. The
    structural writer publishes one closed inventory by descriptor-relative
    native no-replace directory rename, then strictly reloads it; race,
    staging-orphan, symlink, hardlink, FIFO, unknown-member, file-identity, and
    descriptor-drift checks fail closed. The primary-only typed runner rejoins
    the target projection and accepts only one zero-argument scientific
    producer callback. The external path persists a two-signature Ed25519
    observer/verifier envelope in the failed-terminal inventory, atomically
    consumes callback entry plus prepared-terminal publication, and performs
    verify → fixed live revalidation → record derivation → no-replace publish
    → strict reload. Authentication is relative only to explicitly supplied
    runtime pins: trust-root provenance, official authority, wall-clock
    freshness, ownership issuance, execution observation, scientific
    eligibility, retry/replay, D7, and D8 are not established. The official
    supplier was not invoked, no seed was issued, and no official execution was
    introduced. PR26 later fixes the separately auditable deep-internal
    zero-argument producer and exact full-inventory, aggregation, and
    full-design builders without turning item 19 into an official run;
20. <a id="d7-ops-20"></a>**D7-OPS-20** — implement one fused verify-and-exclusive-start operation —
    **implemented as deep-internal mechanics without an official invocation**.
    The only operation accepts a raw current-HEAD descriptor path and one
    zero-argument producer. It derives the Git root and current HEAD, reopens a
    closed nine-member inventory, rejoins its separately persisted records to
    the launch bundle, requires a clean canonical `origin/main`, verifies
    strict source → freeze → authorization → HEAD ancestry, matches the closed
    declared source tree and declared runtime/callable/process observation
    surfaces,
    reobserves a physical store whose bidirectional tree disjointness from the
    repository is proved by descriptor-relative device/inode ancestry, plus
    output/terminal absence,
    and atomically publishes a dedicated, structurally named
    authoritative-start transaction before entering the producer. Its strict
    structural loader alone grants no authority and does not establish
    `started_unresolved`. The fused call then repeats the descriptor, remote,
    runtime, physical, absence, and start-directory checks; any drift leaves
    the visible start consumed without callback entry. The private ownership
    handoff is one-shot and consumed before callback invocation; every exit
    after its construction invalidates both callback entry and terminal
    publication, including failure before runner dispatch. The operation
    accepts and returns no authorization token, ownership object, seed,
    supplier, expected digest, preverified record, or caller-selected trust
    root. This is an honest-local-process protocol rooted in live Git transport
    equality; it is not resistance to a hostile local operator, trust-root
    signature proof, an official start instance, or a scientific result. The
    declared surface covers tracked `src/spirallens/**`, `pyproject.toml`, the
    required runtime lock, exact equality of the complete installed
    distribution name/version inventory, interpreter executable bytes,
    producer source/code identity, and selected process fields; it does not
    close installed package files, loaded native libraries,
    mutable module globals, callable defaults or closures, unrecorded
    environment state, model state, or data state.
21. <a id="d7-ops-21"></a>**D7-OPS-21** — close the code-side execution ingredients before positive authority —
    **partially complete**. PR26 tracks the exact
    `requirements-d7-runtime-lock.txt`, fixes the deep-internal zero-argument
    official producer and exact full-inventory, aggregation, and full-design
    builders, and enforces exact equality of the complete installed
    distribution name/version inventory. Its design load is one private,
    recorded-C1-only archival reconstruction route: pinned C1/C2 verification,
    exact parent
    protocol loading, and whole-document equality with the design recorded in
    C1 are mandatory. It is not a general alternate construction path or a
    historical reinterpretation of D6 or C1, and it accepts no caller-authored
    design.
    The corrected item-21 source anchor defines but does not issue the remaining three
    positive item-21 artifacts. Their fixed order is (a) exact source/runtime
    receipt, (b) seed-free readiness, and (c) scoped reviewed successor-family
    admission. All item-21 source code and documentation are final in that source
    commit. The receipt is the only addition in its direct child; readiness is
    the only addition in the next direct child; and admission is the only
    addition in the next direct child. A merge, intervening change, combined
    artifact or documentation commit, or embedded future-child identity does
    not satisfy this strict receipt-only chronology. Item 21 is partial at the
    source commit and complete at the final corrected tip only after all three
    artifacts are tracked in that chain, strictly reloaded, and pass their
    exact source/runtime and chronology rejoin checks. C2 cannot satisfy these
    obligations, and the existing caller-constructible authority records
    retain false verification fields and are not promoted. No item-22 seed is
    supplied here. Full HEAD-reachable artifact history must retain one exact
    direct-child introduction and identical descendant blobs; merged-away
    mutation, delete/re-add, and parallel introduction fail. Historical
    reconstruction enforces issuer-equivalent source caps; the anchor, HEAD,
    and every bounded source-path event on their descendant ancestry must
    retain the exact anchored tree;
22. <a id="d7-ops-22"></a>**D7-OPS-22** — record one historical item-22 transaction and its later freeze receipt — **`full-design-frozen`; Level 0**.
    The repository-root-only operation accepts no caller supplier, seed, claim key, layout, or authority object; it reloads the historical chain and reviewed exact-current re-anchor, durably claims before one fixed supplier-function invocation, excludes both frozen seed registries, and atomically publishes the closed target without replacement. Import and tests create no tracked artifact. Exactly one tracked transaction exists; its artifact claims one honest-local invocation, while claim, invocation, inventory-output, and transition verification fields remain false. It is not independent proof of an exactly-once supplier call, unseen values, or global independence. The fixed
    `item22-seed-supply/` root has
    `exclusive-seed-supply-claim.json`, `seed-supply-abort.json`, atomic
    `published-target/` members `official-seed-inventory.json`,
    `full-inventory.json`, `full-design.json`, `replay-target.json`,
    `single-supplier-invocation.json`, and `transaction-manifest.json`, then the
    later `full-design-freeze.json` leaf. The re-anchor remains outside that
    root at `item22-current-source-runtime-reanchor.json`; the closed launch
    descriptor is the external `launch.json`, while its distinct launch-intent
    member is `launch-members/launch-intent.json`. All six atomic members are canonical regular
    unaliased files; the manifest binds the other five, and unknown members,
    partial visibility, replacement, and publication retry are forbidden.
    Exact digest edges must rejoin full inventory to seed inventory, full
    design to both inventories, replay target to those same member bytes,
    invocation receipt to the same inventory, and chronology subjects to their
    published members. The
    closed states are `preclaim`,
    `claim-present-publication-absent-nonretryable`,
    `seed-supply-aborted-established`, `publication-complete-unfrozen`,
    `full-design-frozen`, and `launch-intent-present`. The live pre-call claim
    interval is immediately non-retryable and permits no restarted supplier
    entry. It becomes a semantic abort only when that operation ends without
    publication. The distinct durable
    `seed-supply-aborted-established` state requires an evidence receipt at
    `seed-supply-abort.json`; target absence alone does not establish it. This
    later item-22 specification explicitly refines the historical replay-target
    field
    `seed_supply_chronology_contract.claim_without_target_is_seed_supply_aborted`
    without mutating historical bytes. That older blanket flag grants no future
    behavior; operational code must use the active/ended-origin and
    semantic/durable-evidence split above.
    The fixed supplier identity is
    `d7-item22-honest-local-os-csprng-v0-1`; it declares
    `secrets.randbits(63)` and no cryptographic unseen-value proof. The
    `spirallens.d7-item22-exclusive-seed-supply-claim-key.v0.1` scheme uses
    SHA-256 over canonical JSON with domain separator
    `spirallens:d7:item22:exclusive-seed-supply-claim:v0.1`; its ordered inputs
    form one exact-key top-level object binding the fixed claim path, historical
    item-21 triple, reviewed re-anchor, supplier identity, and development and
    parent exclusions. Dynamic bindings use an exact five-field identity
    projection; alternate encodings, extra fields, and caller values are
    rejected. Its closed state machine requires the fixed supplier identity, a
    derived key, internally live-verified
    re-anchor, and durable claim before supplier entry. Only that originating
    operation may proceed from claim to complete publication or evidence-backed
    abort; a restart entrant cannot
    invoke the supplier. Abort-established is terminal, failure to persist its
    evidence remains claim-present/non-retryable, and post-publication failure
    remains `publication-complete-unfrozen`, not abort, with no supplier retry.
    The exclusivity requirement is repository-local and cross-process on
    the same filesystem; it proves no cross-host, distributed-filesystem, or
    supplier-global idempotency. The durable claim-before-call interval is
    required but not restart-resumable. The operation must fsync the owning
    experiment directory after creating the initially absent transaction
    namespace, then fsync claim, staged member/directory, publication-parent,
    and abort-evidence boundaries. Restart recovery uses one mutually exclusive
    presence table in `(claim, target, abort, freeze, launch)` order: `00000`
    is preclaim, `10000` claim-present/nonretryable, `10100`
    abort-established, `11000` publication-complete/unfrozen, `11010`
    full-design-frozen, and `11011` launch-intent-present. Present artifacts
    must pass canonical strict reload. Any other combination—including target
    plus abort, downstream evidence without claim, or invalid/partial
    evidence—fails closed with no precedence or retry. These requirements prove
    neither power-loss survival nor filesystem semantics. Historical
    item-21 reload remains valid. Before operation, this later source surface
    failed exact-current live readiness. After all pre-claim execution source
    became final, the repository first published and reviewed a versioned exact-current
    source/runtime re-anchor bound to the historical item-21 chain at the fixed
    pre-claim path. The source implementation is not that re-anchor. The
    item-22 operation performs the applicable live check internally
    immediately before its no-replace claim and accepts no cached readiness
    snapshot. Only then could it acquire the exclusive seed-supply claim and
    atomically publish the exact seed-bearing full design and replay target.
    The Git history proves that the reviewed re-anchor precedes the single
    same-commit seven-file transaction introduction. The reviewed source
    contract orders live recheck → durable claim → supplier entry → publication,
    and the persisted artifacts claim that chronology, but their verification
    fields remain false and do not independently prove the historical
    invocation or transition timing. That transaction was introduced by
    `f2c1e032f153d369eed99c1bbd467da518b5b9fb` at
    `publication-complete-unfrozen`. The later receipt records that commit as
    `freeze_commit`, records the PR #39 merge
    `6ea0ad761ebcf9e9aedb21319747b6489db66c52` as its designated
    repository-local chronology checkpoint, and was uniquely introduced by
    `f07962db96c4e59020c32e1b27ae8598e69ef6d1`. Git therefore establishes the
    strict ancestry
    `f2c1e032f153d369eed99c1bbd467da518b5b9fb` <
    `6ea0ad761ebcf9e9aedb21319747b6489db66c52` <
    `f07962db96c4e59020c32e1b27ae8598e69ef6d1`, the receipt's unique
    introduction, and the unchanged frozen-member blobs. Platform commit
    signature evidence is separate: the receipt does not establish
    human-signed authorization or review content, an independent witness,
    actor identity, or wall-clock ordering. The receipt itself records
    `freeze_verified=false`; its three bindings record
    `authoritative_source_loaded=false` and `identity_authenticated=false`.
    At this item-22 freeze checkpoint the strict state was
    `full-design-frozen`, but the
    claim ceiling remains Level 0, all item-22 target authority flags remain
    false, and the receipt grants no launch, execution, semantic, causal,
    topological, or scientific authority. Abort evidence, launch intent,
    attempt envelope, result, and D7/D8 advancement were absent. The next
    artifact at that checkpoint was the separate item-23 descriptive result,
    not launch intent. A
    claim without target publication remains non-retryable; target absence
    never proves that the supplier was not invoked;
23. <a id="d7-ops-23"></a>**D7-OPS-23** — separate descriptive result persisted — **operationally complete; scientifically `insufficient`; chronology `deviated`; completion credit false; Level 0**.
    Commit `83ed5f419ff27af0935aa84c363df64f04926cac` records the
    `5,293,662`-byte schema-v0.1 result
    `post-d6-descriptive-a654fa3d9117d2ec9f9275dd`, with canonical SHA-256
    `d0d498b4fb62b38b31de063010516eb17323a4f5b96f44b3ba1f8e7d5680cf4a`.
    It records a seven-file analysis-input read trace and contains exactly 26
    available outputs and one blocked output,
    `amplitude-identifiability-support-separation`, because the historical
    main D2 amplitude, identifiability, and support scalars were not persisted.
    Partial descriptor and confounder evidence does not meet the full-scope
    denominator, and no rerun reconstruction was performed. The result records
    `operational_status=complete`, `claim_delta=none`, D7/D8 `not_run`, and
    zero true authority facts. The item-22 state at this historical checkpoint
    is `full-design-frozen`. The narrower machine path treated launch intent,
    the exclusive official D7 execution-attempt envelope, and receipt-bound
    output-namespace absence as later. The unchanged 2026-07-29 Fundamental
    Frame required those chronology bindings before item 23, so commit
    `897dd7c60411f5fd36c6c50fb5064802a25a471b` records the non-retroactive
    disposition: item 23 supplies no `D7-OPS-23` completion credit. The later
    descriptor/intent commit `09b0cc5c08c11e1dfea019ec13fd7a50bcc50bb4`
    does not cure that ordering;
24. <a id="d7-ops-24"></a>**D7-OPS-24** — **descriptor committed; official v0.1 invocation blocked by protocol deviation; D7/D8 `not_run`; Level 0**.
    The intended v0.1 sequence was to create and commit the closed
    nine-member descriptor and pass strict verification-evidence replay/rejoin,
    recognizing that structural replay preserves but does not recompute or
    independently reauthenticate its live-observation digests and that terminal
    lineage binds the evidence bytes only; pass temporary Git/runtime end-to-end
    validation and authoritative-start-compatible external-abort integration.
    The plan then called for the fused
    verify-and-exclusive-start operation, run the admitted family without
    overrides or post-selection exclusions, require one exact terminal outcome,
    and require complete isolated byte-identical replay before setting any
    scope-specific D7/D8 status. Same-family new seeds remain replication and
    cannot satisfy this item. The experiment-only source-parent preparer and
    fixed dispatcher are non-authorizing plumbing: they accept no scientific
    override and never call the producer during preparation. `launch.json` is
    the descriptor, while `launch-members/launch-intent.json` is its distinct
    launch-intent member. Descriptor publication is last and is bounded by
    exact live rejoin of all nine member projections plus an anchored promoted
    store and empty authoritative-start lane. A preparation partial is retained
    and fail-closed; v0.1 is neither resumed nor cleaned up automatically, and
    recovery requires a reviewed versioned successor. The launcher path/cwd/argv
    and execution HEAD are bound, but launcher bytes remain outside the
    pre-item-22 frozen source closure under the explicit honest-local boundary.
    The source parent is commit
    `0508b339655221acffb81523388becf968108b66`; the exact eight-file
    artifact-only child is
    `09b0cc5c08c11e1dfea019ec13fd7a50bcc50bb4`. Its descriptor SHA-256 is
    `0335d80cfef3e54a9dc14045b6d76d3cf0f939dfeb373203a4cce2b1df7704ac`,
    its bundle SHA-256 is
    `b796ef191840af4ada4172f157be1e7b3e98f1380c7df47d80f4950c0388ee94`,
    and the strict observer reports `launch-intent-present`. At descriptor
    commit `09b0cc5c08c11e1dfea019ec13fd7a50bcc50bb4`, before the disposition
    source changes, exact-runtime/live-identity checks, wrong-envelope
    rejection, temporary Git/runtime end-to-end, hard-exit no-retry, and signed
    external-abort integration passed without producer entry. Those are
    historical plumbing validations, not current v0.1 live-source eligibility.
    Every authority, execution, result, scientific,
    retry, replay, D7, and D8 fact remains false. Canonical-main merge/rejoin
    cannot make this v0.1 identity eligible. The canonical disposition blocks
    its fixed runner, canonical fused entry, and direct producer before start
    or generator access, and the source change intentionally breaks equality
    with the old v0.1 execution-source closure. Do not invoke or reuse these
    coordinates. Any future execution requires a separately reviewed
    versioned successor with new coordinates;
25. <a id="d7-ops-25"></a>**D7-OPS-25** — after an eligible separately versioned qualification successor, begin the separate representation-native F0-F4 selection lane;
    independently confirm and replay its selected instrument without
    transferring Cartesian D2-D5 evidence;
26. <a id="d7-ops-26"></a>**D7-OPS-26** — establish the same-substrate field/core/loop join, persist the frozen
    same-field core-degeneracy scalar and nested-radius profile, and retain the
    architecture-accounted sampled-winding estimate distribution with its
    unrounded cycle totals and residuals; only when the convention permits it
    may calibration-side integer/topology eligibility be assessed;
27. <a id="d7-ops-27"></a>**D7-OPS-27** — qualify the opposite-sign dipole controls and the atlas-to-ANN-to-cycle
    detection-limit surface over injection amplitude, declared
    perturbation/noise, and sampling density, including density-stratified
    exact-recall and graph-family matched-class gates;
28. <a id="d7-ops-28"></a>**D7-OPS-28** — apply the preregistered `SCI-S1` transition/stop rule. Pythia-70M remains
    plumbing-only; complete evaluable adverse gates end `fail`, while an
    exhausted budget without adequate evaluability ends `insufficient`, rather
    than extending instrumentation or relabeling one as the other; and
29. <a id="d7-ops-29"></a>**D7-OPS-29** — only after those separately reviewed `SCI-S1` gates prepare and externally
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
  seed supplier, or granting authority. Because C2 is historical-only, item
  21 cannot derive positive exact-current authority from it; and
- the final corrected item-21 receipt-only chain, whose source commit freezes all code and
  docs and whose three direct children separately add and strictly reload the
  exact source/runtime receipt, seed-free readiness, and scoped reviewed
  successor-family admission. This completes item 21 after the lifecycle,
  result, terminal, runner, and fused mechanics without invoking item 22; and
- the deep-internal item-22 repository-local one-shot operation, which
  implements claim-before-supplier, exclusion-clean OS-CSPRNG supply, and atomic
  target publication. The reviewed re-anchor and one tracked Level-0 target
  were historically introduced at `publication-complete-unfrozen`; a strictly
  later receipt advances that historical checkpoint to `full-design-frozen`
  without setting `freeze_verified` or any authority fact true. The still-later
  descriptor/intent commit now makes the presence observer
  `launch-intent-present`; historical item-21 reload remains valid, and launch
  authorization, execution, and scientific authority remain absent.

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
The exact Pythia-70M identity and runtime layout are now centralized in one
private model-profile seam. That seam remains closed to Pythia-160M and grants
no model-access, subject-preparation, execution, or scientific authority;
`SCI-S2` remains blocked on the terminal `SCI-S1` transition.
The separate private Pythia-160M pre-observation assessor does not register a
160M engineering profile or reuse the 70M lane. It ships no declaration
instance, reads no subject or model value, and can report only a statically
computed, externally blocked assessment with Level-0/no-delta boundaries.
One later source-only increment defined a private provider-metadata and
`config.json` identity-acquisition contract without making a provider request.
From exact merged source commit
`fb640788d3c036cb86127ed9d32d28d27c1e2aa9`, a separately reviewed follow-up
then invoked that operation exactly once and persisted the closed four-file
`pythia160-v0.1` candidate. Its canonical `review_pending` receipt resolves
revision `50f5173d932e8e61f858120bcb800b97af589f46`, rejoins the default and exact
provider responses, and joins the retrieved config bytes to the provider's
non-LFS Git blob. It neither read weights, tokenizer bytes, cache entries,
model values, or activations nor registered Pythia-160M, satisfied the
pre-observation assessor, advanced `SCI-S1`, unblocked `SCI-S2`, or granted
preparation, execution, capture, or scientific authority.
The operation reserved its durable private stage before the first provider
request and completed without retry; the stage is absent after publication.
Publication was an honest, quiescent-local guarantee and did not claim security
against a hostile same-user process racing the final native directory rename.
A subsequent source-only correction records that the exact isolated Python
3.13 runtime exposed an unexpectedly empty default certificate store. The
private script now constructs and validates one explicit TLS client context
from the fixed honest-local macOS CA bundle before durable stage reservation,
then supplies that same context to every bounded HTTPS request. The bundle is
read through no-symlink anchors as a bounded root-owned regular file with no
group or world write bit; certificate verification, hostname checking, TLS
1.2 or newer, and a nonempty CA store are mandatory. Ambient OpenSSL
configuration, provider-module, and engine environment is rejected before TLS
initialization. That correction itself did not run the live main or persist
evidence. The later acquisition used this explicit context, but did not add
the operational CA-bundle digest to the v0.1 receipt, so the candidate does not
attest exact transport-trust bytes. External-witness, identity-review, model,
subject, execution, capture, `SCI-S1`, `SCI-S2`, VOY-credit, and scientific
authority remain false.
A separate deterministic offline fake-NeoX check now hardens selected-position
snapshot ownership and exact per-module train/eval-flag restoration in the
current `PythiaAdapter`. It verifies zero-intervention and hook mechanics only
on that fake structural surface; it does not verify hook parity, zero
intervention, resource fit, or compatibility on any real Pythia model,
including Pythia-160M, and it changes none of the assessor's blocked or
`not_run` facts. The current capture identifier advances from residual-hooks
v1 to v2; partial v1 atlases cannot resume under v2 and receive no migration.
Completed v1 artifacts and the byte-frozen Pythia-70M v0.1 receipt remain
historical and readable, but the protocol binds its earlier adapter source.
Any future model access therefore requires a separately reviewed successor
protocol rather than reusing that cell.

The successor-only fulfillment rule for the D6 v0.1 identity-bearing
cells/stress manifests remains an unchanged historical proposal. C1 is now
recorded as a source-only Level-0 candidate: it declares and hashes the
complete `src/spirallens/**/*.py` plus `pyproject.toml` set, but deliberately
cannot attest its future commit or declared Git source-set closure. The
choice-free C2 receipt is now recorded as the unique receipt-only child of the
exact clean post-merge C1 commit. It does not attest runtime or transitive
dependencies. The separate canonical replay-target and attempt-envelope
contract specifications remain distinct. One Level-0 replay-target instance
was originally introduced inside the item-22 target at
`publication-complete-unfrozen` and is now bound by the separate
full-design-freeze receipt; no attempt-envelope instance is persisted. Step 18
is now partially complete: two deep-internal modules
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
the declared local path coordinates; that reobservation establishes no
source/runtime authority. PR #23 now adds an eighth deep-internal module whose
strict loader returns only a non-authorizing structural candidate. Dedicated
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
observation, and emits no reusable capability. Roadmap item 19 now adds
deep-internal terminal/witness/runner mechanics: a closed atomic structural
terminal with descriptor-relative no-replace publication and strict reload; a
primary-only typed post-start handoff with target-projection validation; and a
persisted two-signature Ed25519 observer/verifier witness whose integrated
external-abort path atomically consumes callback/publication entry, verifies,
live-revalidates fixed coordinates, derives the terminal chain, publishes
once, and strictly reloads. Signature
authentication is only relative to explicit runtime pins. Roadmap item 20 now
adds a separate deep-internal same-call path: a raw current-HEAD descriptor is
reopened as a closed inventory, bound to live canonical `origin/main`, declared
source/runtime and callable/process observation surfaces, a tree-disjoint physical
store, two absence passes, a durable no-replace structurally named
authoritative-start transaction, and one-use callback ownership. The declared
surface covers tracked source and lock bytes, exact equality of the complete
installed distribution name/version inventory, interpreter executable bytes,
producer source/code identity, and selected process fields; package files,
loaded native libraries, mutable module globals, callable defaults/closures,
unrecorded environment, model
state, and data state remain unclosed. Success or an ordinary handled failure
causes at most one terminal-publication attempt; publication failure, hard exit
or `BaseException`, unproved start-parent fsync, or post-start drift can leave
the start visible with no terminal. The start bytes and their strict structural loader
alone grant no authority and do not establish `started_unresolved`; only a
future official same-call invocation plus its verified transition could
justify that lifecycle interpretation. The path emits no reusable
authorization capability and a post-start mismatch enters no callback. This
gives the private ownership type an issuer only inside that
exact call; structural loaders still grant no authority. PR26 now provides the
exact runtime lock, fixed deep-internal zero-argument official producer, exact
full-inventory, aggregation, and full-design builders, and installed-inventory
equality check as code-side item-21 ingredients only. At the PR26 tip there is
no positive exact-current source/runtime receipt or reviewed
admission/readiness. There is also no official descriptor,
target/freeze/intent instance, replay comparator, official seed,
execution-observation receipt, scientific eligibility, invocation/run, or
official record instance. The item-19 evidence-only finalizer cannot accept
the item-20 structural-start type. The positive-authority remainder of item
21 was the next staged closure. The corrected item-21 source anchor freezes the fixed tracked
chain—exact source/runtime receipt, seed-free readiness, then scoped reviewed
successor-family admission—but issues none of those artifacts. Three
successive receipt-only direct children then add exactly one artifact each in
that order, strictly reload/rejoin all three, and complete item 21 at the final
corrected tip. C2 and the existing caller-constructible false-authority records
cannot supply or replace them. Those later actions were absent at the final
corrected `D7-OPS-21` tip. The current tip now tracks the reviewed exact-current
re-anchor; one item-22 exclusive claim; a receipt claiming one honest-local
invocation; the official seed inventory and atomic six-member target; and the
later full-design-freeze receipt. The target transaction was historically
introduced at `publication-complete-unfrozen`; strict reload now reports
`full-design-frozen`. The freeze receipt records `freeze_verified=false`, and
its bindings authenticate no source or identity. The target remains Level 0
and every authority flag is false. The item-23 descriptive result is now
committed with `operational_status=complete`, scientific
`status=insufficient`, 26 available outputs, one blocked output, and no claim
delta. Its separate chronology conformance is `deviated`, it receives no
`D7-OPS-23` completion credit, and this does not reclassify the scientific
status as `fail`. The later launch intent and nine-member descriptor are committed at
Level 0 and strict reload now reports `launch-intent-present`.
No official fused invocation,
start, terminal/result, D7 result, or D8 replay exists; D7 and D8 remain
`not_run`. At descriptor commit `09b0cc5c...`, before the disposition source
changes, strict verification-evidence replay/rejoin, temporary Git/runtime
end-to-end validation, and authoritative-start-compatible external-abort
integration passed without producer entry. Those historical plumbing
validations do not satisfy current v0.1 live-source equality. The canonical disposition introduced
by `897dd7c60411f5fd36c6c50fb5064802a25a471b` is non-retroactive: the later
descriptor does not cure item 23, v0.1 official entry is blocked before start
or generator access, and the old source closure is intentionally superseded.
Any future official execution requires a separately reviewed versioned
successor and new coordinates.
Lifecycle and
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
