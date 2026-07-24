# Neighbor Audit and Receipt Contract

- **Status:** recall methodology frozen; Pythia execution/promotion not frozen
- **Backend:** `spirallens.faiss-hnsw-range@0.1`
- **Distribution:** `faiss-cpu==1.14.3`
- **Artifact maturity:** experimental, pre-1.0

This document defines the only current path from approximate neighbor retrieval
to a persisted SpiralLens candidate ledger. It is an engineering and
provenance contract, not evidence that Pythia contains a vortex, phase payload,
semantic unit, or SAE-hidden concept.

## 1. Separation of responsibilities

The approximate backend proposes pairs from unprojected `resid_pre` states.
It never receives drift vectors, decoded strings, semantic labels, SAE labels,
or projected coordinates through the built-in interface. SpiralLens then
recomputes every state and drift gate in float64 from the original atlas
values. A Faiss score cannot pass a candidate gate or enter candidate identity.

The built-in Faiss worker runs in a fresh Python subprocess with only state,
index, query, and numeric configuration paths. This isolates it from Torch's
process-global OpenMP runtime and keeps the in-tree worker on the state-only
side of the API. It is not an operating-system sandbox against malicious local
Python code or a hostile user with filesystem access. Custom Python backends
may be audited experimentally, but current candidate persistence authorizes
only the built-in `FaissHNSWBackend`.

## 2. Same full index, bounded exact audit

An audit does not build a small ANN index and extrapolate its result. It:

1. validates one complete atlas and ordered global row identity;
2. builds HNSW on the full state matrix for one exact layer group;
3. selects query rows by SHA-256 ranking from a frozen seed and row identity;
4. limits only the exact reference query scope;
5. runs independent cold Faiss rebuilds;
6. exact-reranks both reference and subject proposals;
7. reports aggregate, query-local, density-macro, density-by-boundary, and
   worst-case recall together with determinism and support status.

For 50,304 rows, the tracked query count of 1,000 keeps the exact comparison
budget below 50 million while auditing the same full HNSW index intended for
discovery.

The reusable methodology is frozen in
[`../protocols/neighbor_recall_gate_v0_1.yaml`](../protocols/neighbor_recall_gate_v0_1.yaml).
It requires at least 0.99 recall globally, at every evaluable query, in every
relative-density macro, and in every required density-by-cosine-boundary joint
cell across both cold rebuilds. Zero denominators remain null and required
cells below frozen support minima are `insufficient`.

This does not freeze or pass the Pythia execution. The tracked Pythia protocol
binds the methodology digest but remains `preregistered-draft`, with null atlas
row/group bindings and promotion disabled.

## 3. Bound identities

The index build receipt binds:

- original state shape, dtype, and SHA-256;
- normalized float32 worker-state SHA-256;
- ordered global row-key SHA-256;
- comparison group, currently one `layer_index=N`;
- Faiss index bytes SHA-256;
- HNSW construction/search settings;
- Faiss, NumPy, Python, platform, and compile-option provenance;
- single-thread execution and worker isolation mode.

The promotion receipt additionally binds:

- audit artifact and audit identity SHA-256;
- coverage-evaluator contract, SpiralLens version, and NumPy version;
- exact frozen neighbor-protocol bytes;
- exact candidate-protocol ID and SHA-256;
- atlas manifest, run, state, drift, and row identities;
- preregistered query selection;
- exact candidate and audit configurations;
- exact-rerank contract;
- the authorized all-row persistence query.

The audit uses a query subset. Persistence may change only
`query_indices: <frozen subset> -> null`. Full input, index bytes, group,
backend, runtime, thresholds, drift values, candidate protocol, and rerank
contract must remain identical.

## 4. Trusted-digest workflow

First compute the atlas-specific values without building an index or exposing
audit results:

```bash
spirallens neighbor-audit \
  --manifest runs/pythia70-full/manifest.json \
  --layer 0 \
  --protocol protocols/pythia_neighbor_v0_2.yaml \
  --prepare-only
```

Before a real audit, a separately reviewed protocol copy must bind the emitted
`global_row_key_sha256` and `comparison_group`, set `status: frozen`, and be
hashed out of band. The tracked draft must not be switched to promotion-ready
until those atlas-specific bindings, its frozen candidate protocol, and the
complete promotion-readiness declaration have been independently reviewed.

`global_row_key_sha256` is an immutable row-universe identity. It binds the
ordered token IDs, ContextBank/model revision, observation and sweep positions,
selection declaration, and token domain. It deliberately excludes raw
manifest bytes and the run UUID so harmless JSON serialization or recapture
metadata cannot silently resample the audit queries. Manifest, run, state, and
drift digests remain bound separately in the audit and receipt identity.

The current synthetic Pythia-70M layer-0 qualification uses:

- candidate protocol
  `protocols/pythia70_slot_only_001_layer0_candidate_v0_2.yaml`
  (`d6f60d38237825178f4d7c799e27da370049787d47ca999172121f07c84d212e`);
- neighbor protocol
  `protocols/pythia70_slot_only_001_layer0_neighbor_v0_2.yaml`
  (`296609585f4f165e44a235d6a8af9416b840477313a63013414abb1ed9a55661`);
- atlas manifest
  `runs/pythia70-full-slot-only-001/manifest.json`
  (`6acc23da3726b65bc6151b96a57c949892da9286b98849b300408a3820380eea`);
- row-universe identity
  `d39cd127bd50f564a8ea13e080f19806a3ce390b9ed4436b49d2701054409c43`.

The environment and pre-outcome source commit are bound by the tracked freeze
record created immediately after the implementation/protocol commit. A frozen
audit refuses `--overwrite`; `fail` and `insufficient` are terminal observed
outcomes, not tuning input for another run under the same qualification ID.

Once such a future protocol has been reviewed and frozen:

```bash
NEIGHBOR_PROTOCOL_SHA="$(shasum -a 256 protocols/frozen-neighbor.yaml | awk '{print $1}')"

spirallens neighbor-audit \
  --manifest runs/pythia70-full/manifest.json \
  --layer 0 \
  --protocol protocols/frozen-neighbor.yaml \
  --expected-protocol-sha256 "$NEIGHBOR_PROTOCOL_SHA" \
  --output runs/pythia70-full/layer-0-neighbor-audit.json
```

The command may emit `pass`, `fail`, or `insufficient`. Only a frozen,
deviation-free `pass` under a protocol that explicitly authorizes promotion
can produce a verified receipt. The audit output prints its SHA-256; preserve
that value outside the artifact before candidate extraction.

```bash
AUDIT_SHA="<trusted audit_sha256 from the completed audit>"

spirallens candidates \
  --manifest runs/pythia70-full/manifest.json \
  --output runs/pythia70-full/layer-0-candidates.jsonl \
  --protocol protocols/frozen-candidate.yaml \
  --neighbor-backend faiss-hnsw \
  --neighbor-audit runs/pythia70-full/layer-0-neighbor-audit.json \
  --neighbor-audit-protocol protocols/frozen-neighbor.yaml \
  --expected-audit-sha256 "$AUDIT_SHA" \
  --expected-neighbor-protocol-sha256 "$NEIGHBOR_PROTOCOL_SHA"
```

Approximate ledgers are one layer per file and cannot overwrite an existing
path. Atlas-backed publication is owned by the manifest extraction path, so
the public low-level ledger writer cannot relabel atlas candidates or accept
self-declared approximate candidates. Every group, including a group with zero
candidates, remains present in the footer.

Frozen qualification also requires the exact built-in
`FaissHNSWBackend` Python type for every cold rebuild. A subclass, wrapper, or
custom backend can be measured under a draft protocol, but its result carries
an unverified runner contract and cannot be relabelled into a promotion
receipt.

## 5. Fail-closed behavior

Publication is rejected when any of the following changes:

- protocol bytes, audit bytes, candidate protocol, or trusted digest;
- atlas manifest, token-row identity, selected states, or drifts;
- layer group, query boundary, or query sampling;
- backend ID/version/config/runtime or index bytes;
- worker state cache before or during retrieval;
- exact-rerank contract;
- receipt verification status;
- ledger header/group/candidate retrieval bindings.

Atlas files are opened and checksum-verified through the same file descriptor
used for memory mapping, then revalidated before publication. Candidate
ledgers contain a whole-content digest and a strict reader that reconstructs
typed backend, query, and embedded receipt records. For authenticity rather
than corruption detection, callers should also retain and supply an external
ledger SHA-256.

The v0.2 audit artifact stores local membership digests and recomputable
counts, recalls, support states, and gate outcomes, but not the full pair
membership matrices as an external sidecar. Its digest therefore detects
post-write corruption under the local audit-process trust boundary; it is not
a cryptographic proof that an independently implemented evaluator would
derive the same strata. A future independently replayable evidence sidecar is
required before treating the receipt mechanism itself as scientific evidence.

## 6. Current non-claims and next gate

No tracked artifact currently says that Faiss has passed the Pythia
full-vocabulary audit. No approximate ledger is committed as evidence.
Candidate-boundary recall measures retrieval coverage only. It does not prove
semantic structure, topology, holonomy, phase, or causal relevance.

The next promotion work is to bind a specific atlas row identity and layer,
complete the frozen-protocol adversarial review, and only then execute the
full-vocabulary Pythia audit. A frozen methodology is not an audit result.
Only after a separately verified pass does the roadmap advance to
deterministic candidate-graph and loop construction.
