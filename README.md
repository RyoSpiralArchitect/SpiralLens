# SpiralLens

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)

SpiralLens is an auditable instrument for asking whether transformer
representations contain geometric transport structure or a substrate-bound
field/defect structure that is missed by static, one-direction-at-a-time
feature descriptions.

> **Project status:** experimental research software. The repository is being
> designed toward a reusable library, but the public API and artifact schemas
> remain pre-1.0 and may change.

The project now separates two deliberately narrow questions:

> Can we detect reproducible loop or relative-holonomy structure after
> separating norm changes and accounting for known architectural factors?
>
> Separately, can we define a model-derived order parameter whose amplitude,
> direction, singular set, and sampled charge survive the controls required for
> a topological-defect candidate?

SpiralLens does **not** assume that a model contains literal optical vortices.
It does not call a large drift “phase,” does not treat projected curl as a
physical quantity, and does not label a structural candidate as semantic until
held-out prediction and causal intervention succeed.

No real-model order parameter, verified core, sampled model winding, or
topological-defect candidate currently exists. Local anisotropy, effective
rank, projected norm, and spectral gaps remain possible diagnostics, not
order parameters by themselves.

## Scientific interpretation anchors

The project adopted an order-parameter-first fundamental interpretation after
the frozen Pythia-70M retrieval audit. This is explicitly a post-outcome change
to the future research question, not a rewrite or explanation of that audit.
Frozen protocols and outcomes retain their original meaning.

Read these documents before adding a field, graph, loop, or claim:

- [Order-Parameter-First Fundamental Frame](docs/FUNDAMENTAL_FRAME.md)
- [Experiment Interpretation Ledger](docs/EXPERIMENT_INTERPRETATION_LEDGER.md)
- [Branched Claim Taxonomy](docs/claim_ladder.md)
- [Next Experiment Preparation](docs/NEXT_EXPERIMENT_PREPARATION.md)
- [P0 Hypothesis and Artifact Contracts](docs/P0_HYPOTHESIS_AND_ARTIFACT_CONTRACTS.md)
- [Research-to-Library Roadmap](docs/ROADMAP.md)
- [Access, Provenance, and Lifecycle Boundary](docs/ACCESS_BOUNDARY.md)
- [Pointwise Referents and Numeric Payload Boundary](docs/REFERENT_AND_NUMERIC_BOUNDARY.md)
- [API Maturity and Compatibility Status](docs/API_STATUS.md)
- [Schema and Compatibility Change Record](docs/SCHEMA_CHANGELOG.md)

## Research pipeline

1. Validate the instrument on analytic rotation, winding, stretch, radial, and
   shear phantoms.
2. Stream a fixed-context Pythia model-input-row activation atlas to
   memory-mapped arrays.
3. Emit a schema-validated, provenance-bound structural candidate ledger
   without semantic labels.
4. Bind an explicit substrate and choose one of two typed paths:
   geometry/transport, or a preregistered order-parameter field.
5. Construct semantics-free graph families and matched cycles.
6. Run protocol-declared gauge, architecture, graph-family, radius,
   orientation, sampling, and matched nulls.
7. Add semantic and causal evaluation only after structural promotion.

Pythia-70M is a plumbing smoke. Pythia-160M remains the historically intended
first scientific model family, but this frame does not authorize that run.
SAE annotation, training-checkpoint trajectories, transfer operators, and
natural-language interpretation are intentionally deferred.

The subject-data executable path currently reaches step 3 through a state-only
neighbor backend contract, a deterministic exact reference, and shared exact
reranking. Separately, the P0 contract layer now validates the F0-F4
hypothesis registry and individual canonical instrument-artifact manifests.
The first P1 development generator now emits one paired
representation-shaped positive/null substrate through F0, F1, and F2 into a
canonical closed bundle. It uses a model-free
`SyntheticLatticeContextBinding` embedded in each
`SyntheticLatticeSubstrateBinding` and the instrument-development-only
`synthetic_lattice` axis. Its bundle indexes no ContextBank
(`context_banks=()`), creates no `ModelBinding` or tokenizer binding, and does
not load Pythia or reuse a model ContextBank.
Its closed-integrity bundle validator additionally resolves exact
content-addressed artifact references, rejects missing, extra, unreachable, or
cyclic members, verifies opaque payload byte lengths and SHA-256 digests, and
checks selected cross-manifest metadata joins. It does not decode payload
values, recompute row identities from array contents, run an estimator or graph
constructor, load a model, or access subject data.
The separate, explicitly authorized numeric consumer now retains only requested
payload descriptors from the same secure bundle-validation transaction,
re-hashes those exact descriptors, strictly decodes bounded numeric NPY v1/v2
snapshots, derives row identity from content, and can verify a frozen L2
amplitude relation. Calling the ordinary bundle loader still retains no
payload descriptor and returns no payload bytes or decoded array. Bundle
member paths remain visible as manifest metadata and are not an access-control
boundary.

The provisional `spirallens.referents` namespace now fixes the F0-F4
pointwise-referent contract. F0 support diagnostics and the F1 projector are
explicitly not order parameters. F2 and F3 derive amplitude and direction from
the same pointwise vector, while F4 derives both from the same pointwise
traceless spin-two tensor. No substrate field or interpolation is bound, so
these formulas are not yet order parameters.
The tracked P0 registry produces referent-contract digest
`4108ccda4f2a76920091bf2bf422b97297fe4d91ee54f14e2b03362e53e358f2`.
This is a software and construct-definition identity, not evidence that any
model contains the referent.

A typed generator-family identity now distinguishes a mathematical
construction from a seed, source digest, or implementation label. The new
spectral-moment quadrature family declares a separate mathematical
construction from the existing representation phantom and supplies separated
F2/F4 positive/null/prerequisite-failure development controls. Distinct family
metadata is necessary but does not prove epistemic or implementation
independence. It is not yet wired into a qualification bundle and does not
advance D0-D8.
The mathematical loop/holonomy tools and architecture-factor/null primitives
exist, and the sampled-winding primitive accepts caller-supplied complex
values, but no Pythia candidate is wired to a model-derived order parameter,
matched graph-cycle family, Level 2G result, or Level 2T result.
The exact pairwise reference fails loudly above 10,000 all-pair rows. No
approximate backend has been promoted yet. A pinned Faiss HNSW range-search
implementation and its receipt-gated audit path now exist. The first
consumer-safe, frozen Pythia-70M full-index/subset-query execution terminated
`insufficient`: all 1,000 preregistered queries had zero exact-reference
support at the frozen boundary. Deterministic empty output passed, recall was
not estimable, and no persistence receipt was issued. This is retrieval
plumbing evidence only.

## Development install

```bash
python -m pip install -e '.[ann,models,dev]'
```

The analytic calibration requires only the core dependencies:

```bash
python -m pip install -e .
spirallens calibrate
```

The full test suite includes the offline Pythia adapter and Faiss backend:

```bash
python -m pip install -e '.[ann,models,dev]'
pytest
```

## First end-to-end run

Calibrate the model-free instrument:

```bash
spirallens calibrate \
  --samples 512 \
  --output runs/calibration/analytic-v0.1.json
```

Validate the tracked public context-bank example before capture:

```bash
spirallens context-bank validate \
  --path protocols/context_bank_example_v0_1.yaml \
  --allow-role example
```

Validate the post-outcome, outcome-excluded P0 hypothesis registry:

```bash
spirallens hypothesis-registry validate \
  --path protocols/order_parameter_hypothesis_registry_v0_1.yaml
```

This command is read-only. It verifies that all F0-F4 families remain
Level-0, no winner or integer output is authorized, and no prior subject
outcome, subject identity, semantic label, or numeric threshold can enter the
registry.

Generate the first tracked P1 instrument-development bundle:

```bash
spirallens synthetic-bundle generate \
  --protocol protocols/p1_representation_phantom_v0_1.yaml \
  --output-dir runs/p1-representation-dev-v0.1
```

The tracked protocol binds the exact generator commit and module SHA-256, the
P0 registry source and canonical digests, the two fixed cases, and an execution
boundary in which all model, subject, calibration-selection, and integer
authorities are false. The emitter executes the bound source bytes, validates
the generated numeric relations, round-trips every NPY payload, validates the
staged closed bundle, and revalidates the published tree. The manifest is
written last inside a private staging directory. Publication then makes the
complete validated directory visible in one atomic, exclusive, no-replace
namespace transition using Darwin `renameatx_np(RENAME_EXCL)`; an existing
destination is never replaced. The publisher retains the exact published
directory descriptor and passes its `(device, inode)` identity into the secure
bundle loader, so post-publication validation cannot silently follow a
replacement display path. This current implementation requires Darwin
`O_NOFOLLOW_ANY`, directory-relative operations, and a filesystem supporting
the exclusive rename. Unsupported environments fail closed. This is namespace
atomicity, not a claim of crash durability: the publisher does not yet fsync
the complete tree and parent directory. If post-publication validation fails,
the published tree is retained for forensic inspection rather than
destructively rolled back. Pre-publication failures likewise retain their
private, random staging directory; the emitter never performs a recursive
stat-then-delete cleanup that could race with a replacement directory.

The durable substrate preprocessing receipt records both
`identity-no-preprocessing` and the complete non-qualification boundary:
`qualification_status=not_evaluated`, `synthetic_qualified=false`, and D0-D8
all `not_run`. The same receipt records
`context_kind=synthetic_lattice`,
`synthetic_context_claim_eligible=false`,
`cycle_construction_status=not_run`, and a versioned conservative resource
guard. The guard uses estimator
`representation-phantom-conservative-static-estimate-v0.1`, safety factor
`4`, and 256 MiB estimated peak/output caps. It protects against
parameter-induced runaway allocation; it is explicitly not an operating-system
OOM guarantee.

The executed development graph is recorded with
`resolution=instrument_dev_executed` and exact
`mutual-knn`/`euclidean`/`k-6` choices. That receipt states what this visible
development cell ran; it is not `fixed_by_hypothesis`,
`calibration_resolved`, calibration selection, or graph-family qualification.
Cycle construction is not run. `CandidateGraph.cycle_support` therefore
contains the schema-required empty `<i8` array of shape `(0, 4)`; this means
that no cycle support was supplied, not that the graph was observed to be
cycleless.

The output contains no `CoreScore`, `CoreCandidate`, `EdgeConnection`, loop,
winding, calibration-selection, or confirmation artifact. Every emitted
F0/F1/F2 observation and supplied anchor remains at Level 0. Its positive/null
pair is a software-development cell, not an independent generator family and
not synthetic qualification. Two cold emissions are required to be
byte-identical in the executing environment; cross-environment numerical,
publication, or byte identity is not yet claimed.

This library slice does not reinterpret the frozen bundle. Instead:

- `spirallens.referents` declares the exact F0-F4 pointwise objects and
  same-object amplitude/direction laws while keeping field binding false;
- `open_numeric_payload_session()` is the first value-reading consumer, gated
  by a trusted parent-policy digest and one-consumer lineage; and
- `SpectralMomentGenerator` supplies a second construction-family foundation
  with disjoint fit/evaluation quadrature and separated oracle truth.

No existing P1 protocol, bundle schema, artifact schema, or frozen Pythia
protocol/receipt bytes are migrated by these additions.

The provisional [`spirallens.graphs`](src/spirallens/graphs) foundation now
adds three deterministic, exhaustive rounded-float64 adjacency
mechanisms—mutual-kNN, inclusive fixed-radius, and all-pair
shared-neighbor—plus structural diversity measurement. A graph-independent
`DiscreteDomainComplex` supplies an exact
integer oriented triangular complex, and `CycleClassBinding` can certify one
narrow relation: a graph cycle refines the same caller-declared, induced support
boundary exactly once. These records are in-memory fingerprints, not
persistence schemas, and do not verify when or why the caller selected that
support or refinement rule. The matched relation is not generic homology, a
latent manifold topology, a core, winding, graph-family cycle invariance, or
D4 qualification. See
[Graph and discrete-domain foundation](docs/GRAPH_AND_DISCRETE_DOMAIN_BOUNDARY.md).

Validate one generated canonical instrument manifest:

```bash
spirallens instrument-artifact validate \
  --path path/to/canonical-artifact.json \
  --expected-source-sha256 <sha256> \
  --expected-canonical-sha256 <sha256>
```

This is deliberately a single-manifest check. It does not resolve referenced
artifacts or payloads and reports `validation_scope=single_manifest`.

Validate a canonical closed-world integrity bundle:

```bash
spirallens instrument-bundle validate \
  --path path/to/instrument-bundle.json \
  --expected-source-sha256 <sha256> \
  --expected-canonical-sha256 <sha256>
```

The bundle command resolves every exact `ArtifactRef`, requires all indexed
artifacts to be reachable from declared roots in an acyclic dependency graph,
and requires at least one instrument artifact and instrument root. It requires
exact `PayloadRef` closure and streams payload bytes only to verify declared
length and SHA-256. It also validates the implemented cross-manifest metadata
joins and each ContextBank's declared allowed role. It rejects subject fit
roles and cannot authorize subject access or execution. It does not decode
arrays, validate payload semantics, or qualify the bundle scientifically.
Member loading is descriptor-relative and fail-closed: symlinks and files with
multiple hard links are rejected, and platforms without the required
`dir_fd`/no-follow support report `secure_member_open_unavailable` instead of
falling back to pathname reopening. A returned `LoadedBundlePayload` is an
integrity receipt only; it intentionally exposes no reusable payload path or
handle.

The example bank used by the separate Pythia atlas path contains only
project-authored synthetic engineering fixtures. It is not used by the
model-free P1 representation phantom described above. Every bank entry has
`role=example` and `claim_eligible=false`. Scientific discovery and held-out
banks are separate frozen artifacts beginning in M2.

The canonical receipt was produced by the following historical, bounded,
atlas-only Pythia-70M public-example plumbing invocation:

```bash
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
PYTHONPATH=src python3 -m spirallens public-example-plumbing run \
  --protocol protocols/pythia70_public_example_plumbing_v0_1.yaml \
  --output runs/pythia70-public-example-plumbing-v0.1 \
  --receipt \
    experiments/pythia/receipts/pythia70_public_example_plumbing_v0_1.json \
  --expected-protocol-source-sha256 \
    ef93891c7450ef13cc2c5da54bf1a80d4a0b679df2df04964f2cc505e00aaf4c \
  --expected-protocol-canonical-sha256 \
    968ad990e7c80ddae3cadcf71c5b39aa37f7b5cad88ea473df094cedb6b633d6
```

This is provenance, not a rerun command. The tracked receipt now occupies the
shown no-overwrite path, and the generated atlas may occupy the shown output
path in the execution workspace. Any independent replay must use fresh parent
directories while retaining the frozen output basename
`pythia70-public-example-plumbing-v0.1`; it must not replace the canonical
receipt.

The frozen protocol also binds implementation commit
`de24a2b73fa408d49ed4252c8a18332554978296`, and the runner requires that commit
to remain an ancestor of the execution checkout. Integration therefore must
preserve the PR commit ancestry; squash or rebase integration is incompatible
with this frozen engineering cell and fails closed. Ancestry is necessary but
not sufficient: the runner also rejects tracked or untracked drift under
`src/spirallens`, so a later independent replay requires a clean,
source-compatible checkout or dedicated worktree.

The strict tracked protocol selects the exact model revision and cached model
file hashes, ContextBank source and canonical digests, structured slot, 32
explicit row IDs, CPU/float32 runtime, resource ceilings, output identity, and
source implementation. Network access is disabled and the model is loaded
with local files only. The complete protocol content and identity are embedded
in the atlas request and run fingerprint.

The receipt records the access facts—`model_accessed=true` and
`activation_values_persisted=true`—and independently binds the manifest and
array hashes. It also records `scientific_claim_eligible=false`,
`p1_instrument_consumed=false`, D0-D8 `not_run`, and every candidate, neighbor,
graph, field, core, loop, holonomy, winding, semantic, SAE, and integer stage
as `not_run`. The only authorized consumer is atlas integrity validation;
downstream candidate and neighbor entry points reject this execution class
before opening activation arrays.

If atlas finalization succeeds but no receipt is published, that directory is
terminally unreceipted: do not analyze or reuse it. Preserve it under a
quarantine name for diagnosis, fix the publication failure, and rerun into the
original frozen output ID from a fresh path.

Low-level capture can still use `--context-ids` and `--position` directly.
`--position` is the observed residual position and, by default, also the slot
replaced by each swept row; pass `--sweep-position` when they differ. This raw
mode is an engineering escape hatch and carries no ContextBank identity.

This produces a fixed-context model-input-row activation atlas. It is not a
language-space or semantic atlas: a row ID is an address in the model input
embedding table, and SpiralLens attaches no decoded meaning or expected
outcome. It is also not a subject run, candidate source, model-bound
instrument bundle, P1 execution, or progress on D0-D8.

The following command belongs to the preserved historical retrieval workflow,
not to the public-example engineering atlas above. It can consume only an
atlas whose own execution contract authorizes candidate extraction:

```bash
spirallens candidates \
  --manifest runs/<retrieval-authorized-atlas>/manifest.json \
  --output runs/<retrieval-authorized-atlas>/candidates.jsonl \
  --protocol protocols/pythia_v0_1.yaml
```

Candidate ledger v0.3 separates retrieval from judgment. A backend sees only
the unprojected `resid_pre` row matrix and proposes canonical global row-index
pairs. SpiralLens then recomputes every state and drift metric in float64 from
the original arrays. Backend scores cannot pass a gate or enter candidate
identity.

The bounded exact implementation remains the reference backend. The selected
but unpromoted approximate implementation is `faiss-cpu==1.14.3`
`IndexHNSWFlat` with normalized float32 inner-product range search. Build and
search run single-threaded in fresh Python subprocesses; every proposal is
still judged from the original atlas values by the shared float64 reranker.

The reusable measurement and support rules are frozen in
[`protocols/neighbor_recall_gate_v0_1.yaml`](protocols/neighbor_recall_gate_v0_1.yaml).
They require `>= 0.99` aggregate, query-local, density-macro, and
density-by-cosine-boundary recall across deterministic cold rebuilds. Empty or
under-supported required cells are `insufficient`, never an automatic pass.
The atlas-specific v0.2 declaration remains preserved at
[`protocols/pythia_neighbor_v0_2.yaml`](protocols/pythia_neighbor_v0_2.yaml).
The published native-call producer contract remains preserved as historical in
[`protocols/pythia_neighbor_v0_3.yaml`](protocols/pythia_neighbor_v0_3.yaml);
it keeps the outer query artifact batch at 512 while bounding each native
Faiss range-search call to one query. Its bytes remain available for static
inspection only; it cannot authorize preflight, subject execution, or
approximate-candidate persistence. The preserved consumer-safe v0.4 template
is separately preregistered in
[`protocols/pythia_neighbor_v0_4.yaml`](protocols/pythia_neighbor_v0_4.yaml).
It keeps backend version 0.2 but requires qualification receipt schema v0.2
at one exact, non-selectable output path.
Receipt-gated approximate persistence uses the separate typed candidate
declaration
[`protocols/pythia_candidate_v0_2.yaml`](protocols/pythia_candidate_v0_2.yaml);
the older v0.1 declaration remains exact-only and cannot be made
ANN-authorizing by changing its status alone.

The first tracked subject-qualification pair is separately frozen for the
synthetic example bank, Pythia-70M, and `layer_index=0`:
[`protocols/pythia70_slot_only_001_layer0_candidate_v0_2.yaml`](protocols/pythia70_slot_only_001_layer0_candidate_v0_2.yaml)
and
[`protocols/pythia70_slot_only_001_layer0_neighbor_v0_2.yaml`](protocols/pythia70_slot_only_001_layer0_neighbor_v0_2.yaml).
The v0.2 subject attempt ended in a native infrastructure error before any
`pass`, `fail`, or `insufficient` outcome and is terminal under its one-shot
contract. Its reservation marker is retained as a tombstone. Those files do
not upgrade the run into semantic or scientific evidence. The bank is
`claim_eligible: false`, and even a future pass establishes
approximate-retrieval coverage only.

Index bytes, full states, row order, layer group, runtime, candidate protocol,
query contract, and exact rerank contract are bound into the audit identity.
Query selection uses a canonical row-universe digest over ordered token IDs,
the ContextBank/model revision, position, and token domain. Raw manifest bytes
and run UUIDs remain audit provenance but cannot change the query sample.
Every subject audit also requires an out-of-band-hashed execution-freeze
record that verifies the exact pushed source tree, interpreter, installed
NumPy/Faiss content, import root, paths, and argv. For backend v0.2 it also
binds a canonical, production-shape synthetic qualification receipt generated
by two fresh subprocesses, including the fixture, native binary, config, and
range-call limit digests plus the clean, live-pushed preflight commit and
`src/spirallens` tree. Its digest is persisted in the audit identity. The
final pathname is exclusively reserved before any outcome computation, and a
complete fsynced recovery sidecar is staged before the reservation marker can
be replaced.
Approximate candidate persistence accepts only the built-in Faiss backend and
a receipt loaded from persisted audit/protocol files against out-of-band
SHA-256 digests. The audit query subset may expand to all query rows at
persistence; no other target field may change.

The generic tracked v0.4 draft deliberately keeps
`issue_persistence_receipt_on_verified_pass: false`. A separate atlas-specific
v0.4 protocol froze the synthetic qualification receipt, row identity, layer,
and candidate declaration before its one-shot. That audit is terminal
`insufficient`, not `pass`: the exact reference contained zero retrieval pairs
and zero candidates for all 1,000 selected queries. Therefore no approximate
candidate ledger or backend promotion is authorized.
The compact tracked outcome witness is
[`protocols/pythia70_slot_only_001_layer0_subject_audit_v0_4_outcome_observation.yaml`](protocols/pythia70_slot_only_001_layer0_subject_audit_v0_4_outcome_observation.yaml);
it is observation-only and binds the
[exact tracked audit bytes](runs/pythia70-full-slot-only-001/layer-0-neighbor-audit-v0-4.json)
without reconstructing them.

The historical pre-outcome prepare-only invocation used to obtain
atlas-specific bindings without running the ANN or observing an audit outcome
was:

```bash
spirallens neighbor-audit \
  --manifest runs/pythia70-full/manifest.json \
  --layer 0 \
  --protocol protocols/pythia_neighbor_v0_4.yaml \
  --prepare-only
```

It is shown for provenance and must not be rerun against the consumed
Pythia-70M identity.

The v0.4 native path passed a separate subject-independent production-shape
qualification that accepted no atlas, token, drift, decoded string, or
semantic input. Its canonical receipt is preserved at
[`protocols/pythia70_slot_only_001_layer0_faiss_range_qualification_v0_2.json`](protocols/pythia70_slot_only_001_layer0_faiss_range_qualification_v0_2.json).
The receipt qualifies retrieval plumbing only and must not be regenerated at
the same one-shot path.

An earlier receipt-v0.1 producer run was observed to return `pass`, but its
volatile receipt was lost during reboot before it could be tracked. Loading
that receipt after Torch had entered the process exposed an OpenMP collision,
so consumer binding was never established. That observation is not a subject
audit outcome, does not authorize promotion, and did not consume the subject
one-shot. SpiralLens does not enable an unsafe duplicate-OpenMP environment
workaround; receipt v0.2 moves consumer regeneration into a fresh subprocess.

The complete freeze, audit, receipt, and persistence contract is documented in
[Neighbor Audit and Receipt Contract](docs/neighbor_audit.md).

`--full-vocabulary` is required to authorize every ID in the declared sweep
domain explicitly.
Atlas arrays are memory-mapped, manifests are written atomically, completed
files are checksummed, and a resume request must match the original capture
fingerprint.

## Roadmap: experiment to library

SpiralLens is intentionally growing in two stages: first prove that the
instrument is scientifically auditable, then stabilize the parts that deserve
to become a general library.

- **Now — instrument foundation (`0.1.x`):** analytic phantoms, Pythia
  activation atlases, structural candidate ledgers, versioned provenance, and
  fail-closed storage, plus exact and selected-unpromoted Faiss retrieval,
  full-index/subset-query audits, and verified receipt plumbing.
- **Next — synthetic field/graph qualification:** consume the implemented
  experimental substrate/order-parameter metadata contracts, compare competing
  field hypotheses on representation-shaped phantoms, and qualify the full
  crossed graph-family null before preparing another subject protocol.
- **Then — candidate-to-loop integration:** keep geometry/holonomy and
  field/defect paths separate, join them only through explicit same-substrate
  artifacts, and retain Pythia-70M as development material.
- **First scientific protocol:** create separate frozen discovery and held-out
  context-bank artifacts, freeze the integrated instrument, and run the same
  preregistered design on Pythia-160M without tuning on either held-out results
  or Pythia-70M outcomes.
- **Research validation:** test whether surviving relational structure is lost
  by SAE reconstruction and whether held-out, norm-preserving interventions
  change downstream behavior selectively.
- **Library alpha/beta:** extract stable core APIs, formalize adapter protocols,
  add schema migration and compatibility policy, publish documentation and
  benchmarks, then release on PyPI.
- **1.0:** stable documented API, supported artifact migrations, reproducible
  release process, multi-backend test matrix, and an explicit governance and
  deprecation policy.

The canonical milestone definitions, exit criteria, API boundaries, risks, and
immediate next plan live in the single
[Research-to-Library Roadmap](docs/ROADMAP.md).

## Repository boundaries

- `core/` contains framework-neutral stable-candidate primitives. Its
  compatibility tests have begun, but it is not yet a 1.0-stable API.
- `access/` contains provisional typed provenance, descriptor-only prepare
  access, consumer authorization, value-access lineage, and execution
  lifecycle contracts. It imports no model or numeric framework.
- `referents/` contains the provisional F0-F4 pointwise-referent contract and
  model-free same-object vector/spin-two numeric relations. Successful checks
  establish neither a substrate-bound field nor model-side construct validity.
- `holonomy/` contains continuous closed-loop transport quantities.
- `topology/` contains sampled-winding quantities and, later, topology
  promotion tests. A sampled charge is not a continuous-field certificate.
- `instrument_contracts/` contains implemented experimental metadata
  boundaries for the P0 registry, provisional canonical artifacts, and
  closed-world integrity bundles. Its ordinary bundle loader reads opaque
  payload bytes only for length and SHA-256 verification. A separate
  authorization-bound numeric session decodes declared arrays and validates
  closed numeric relations; neither path runs an estimator, graph constructor,
  or subject access;
- `synthetic/` contains the model-free, source-bound P1 development generator,
  a distinct spectral-moment generator-family foundation, numeric self-audit,
  conservative resource preflight, exact executed development graph, and
  current-environment exclusive bundle publisher. It is not a
  calibration-selection or subject-execution boundary;
- `graphs/` constructs provisional model-free rounded-float64 graph families
  and a graph-independent discrete-domain foundation from supplied numerical
  inputs. It remains separate from retrieval and does not qualify a scientific
  graph, field, core, loop, or topology claim;
- `factors/` accounts for LayerNorm, RoPE, attention value transport, routing,
  and MLP paths.
- `neighbors/` retrieves row-index pairs from unprojected states only; it never
  decides whether a pair is a candidate.
- `semantics/` is downstream annotation and evaluation, never discovery.
- `benchmarks/icicl/` is an optional external benchmark and is not imported by
  the core package.

See the [Fundamental Frame](docs/FUNDAMENTAL_FRAME.md),
[glossary](docs/glossary.md), and
[branched claim taxonomy](docs/claim_ladder.md) before adding a new metric or
persisted field.

## License

SpiralLens is licensed under the
[Apache License 2.0](LICENSE).
