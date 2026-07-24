# SpiralLens

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)

SpiralLens is an auditable instrument for asking whether transformer
representations contain closed-loop transport structure that is missed by
static, one-direction-at-a-time feature descriptions.

> **Project status:** experimental research software. The repository is being
> designed toward a reusable library, but the public API and artifact schemas
> remain pre-1.0 and may change.

The v0.1 question is deliberately narrow:

> Can we detect reproducible loop, relative-holonomy, or sampled-winding
> candidates in Pythia activations after separating norm changes and accounting
> for known architectural factors?

SpiralLens does **not** assume that a model contains literal optical vortices.
It does not call a large drift “phase,” does not treat projected curl as a
physical quantity, and does not label a structural candidate as semantic until
held-out prediction and causal intervention succeed.

## v0.1 pipeline

1. Validate the instrument on analytic rotation, winding, stretch, radial, and
   shear phantoms.
2. Stream a fixed-context Pythia model-input-row activation atlas to
   memory-mapped arrays.
3. Separate radial/norm effects from angular and layer-drift effects.
4. Emit a schema-validated, provenance-bound candidate ledger without semantic
   labels.
5. Run protocol-declared loop, gauge, architecture, radius, and orientation nulls
   on shortlisted candidates.

Pythia-70M is a plumbing smoke. Pythia-160M is the first intended scientific
run. SAE annotation, training-checkpoint trajectories, transfer operators, and
natural-language interpretation are intentionally deferred.

The executable path currently reaches step 4 through a state-only neighbor
backend contract, a deterministic exact reference, and shared exact reranking.
The mathematical loop/holonomy tools and architecture-factor/null primitives
exist, but are not yet wired from a Pythia candidate into a Level-2 result.
The exact pairwise reference fails loudly above 10,000 all-pair rows. No
approximate backend has been promoted yet. A pinned Faiss HNSW range-search
implementation and its receipt-gated audit path now exist, but the tracked
Pythia execution protocol remains an unpromoted draft. The reusable
query-local, relative-density, cosine-boundary, and worst-case recall
methodology is frozen separately; no full-vocabulary audit outcome is claimed.

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

The example bank contains only project-authored synthetic engineering fixtures.
Every entry has `role=example` and `claim_eligible=false`. Scientific discovery
and held-out banks are separate frozen artifacts beginning in M2.

Capture a bounded, bank-bound Pythia-70M plumbing atlas:

```bash
spirallens atlas \
  --output runs/pythia70-smoke \
  --context-bank protocols/context_bank_example_v0_1.yaml \
  --context-id synthetic-slot-only-001 \
  --allow-role example \
  --expected-context-bank-source-sha256 \
    db9df614ad68bd20646da29740354624b8be075719e7ef4ca2ad8023d4dcef4f \
  --expected-context-bank-canonical-sha256 \
    46c23fb8f1c0f2136537bab5717473c2cc8b03a9121d89db267a29b89ef0a438 \
  --max-tokens 32 \
  --batch-size 8 \
  --device auto
```

The bank selects the exact model revision, structured slot, attention mask,
sweep position, and observation position. Its raw and canonical SHA-256
digests, ordered entries, role, tokenizer fingerprint, and token domain are
bound into the run fingerprint; resume rejects a mismatch before appending an
attempt.

Low-level capture can still use `--context-ids` and `--position` directly.
`--position` is the observed residual position and, by default, also the slot
replaced by each swept row; pass `--sweep-position` when they differ. This raw
mode is an engineering escape hatch and carries no ContextBank identity.

This produces a fixed-context model-input-row activation atlas. It is not a
language-space or semantic atlas: a row ID is an address in the model input
embedding table, and SpiralLens attaches no decoded meaning or expected outcome
to it during discovery.

Then apply the tracked, semantics-free structural gates:

```bash
spirallens candidates \
  --manifest runs/pythia70-smoke/manifest.json \
  --output runs/pythia70-smoke/candidates.jsonl \
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
The versioned native-call remediation is separately preregistered in
[`protocols/pythia_neighbor_v0_3.yaml`](protocols/pythia_neighbor_v0_3.yaml);
it keeps the outer query artifact batch at 512 while bounding each native
Faiss range-search call to one query.
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

The tracked v0.3 draft deliberately has
`issue_persistence_receipt_on_verified_pass: false` until its synthetic
qualification receipt and atlas bindings are frozen. Aggregate recall can hide
a query-local collapse, but freezing that measurement rule does not freeze a
Pythia run. No passing full-vocabulary audit has been observed. Therefore no
tracked full-vocabulary Pythia audit or approximate candidate ledger is
claimed yet.

To obtain the atlas-specific bindings without running the ANN or observing an
audit outcome:

```bash
spirallens neighbor-audit \
  --manifest runs/pythia70-full/manifest.json \
  --layer 0 \
  --protocol protocols/pythia_neighbor_v0_3.yaml \
  --prepare-only
```

The v0.3 native path must first pass the separate subject-independent
production-shape qualification. It accepts no atlas, token, drift, decoded
string, or semantic input:

```bash
spirallens faiss-range-preflight \
  --protocol protocols/pythia_neighbor_v0_3.yaml \
  --expected-protocol-sha256 "<trusted draft SHA-256>" \
  --output protocols/pythia70_slot_only_001_layer0_faiss_range_qualification_v0_1.json
```

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
- **Next — candidate-to-loop system:** a public synthetic engineering context
  bank, an atlas-bound qualification run under the frozen query-local
  approximate-retrieval gates, cycle construction, relative holonomy, and
  architecture/null accounting on Pythia-70M.
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

- `holonomy/` contains continuous closed-loop transport quantities.
- `topology/` contains sampled-winding quantities and, later, topology
  promotion tests. A sampled charge is not a continuous-field certificate.
- `factors/` accounts for LayerNorm, RoPE, attention value transport, routing,
  and MLP paths.
- `neighbors/` retrieves row-index pairs from unprojected states only; it never
  decides whether a pair is a candidate.
- `semantics/` is downstream annotation and evaluation, never discovery.
- `benchmarks/icicl/` is an optional external benchmark and is not imported by
  the core package.

See [the glossary](docs/glossary.md) and
[the claim ladder](docs/claim_ladder.md) before adding a new metric or persisted
field.

## License

SpiralLens is licensed under the
[Apache License 2.0](LICENSE).
