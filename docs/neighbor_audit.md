# Neighbor Audit and Receipt Contract

- **Status:** mechanism implemented; tracked Faiss promotion not yet authorized
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
7. reports candidate-boundary recall and determinism.

For 50,304 rows, the tracked query count of 1,000 keeps the exact comparison
budget below 50 million while auditing the same full HNSW index intended for
discovery.

The current tracked draft requires aggregate candidate-boundary recall of at
least 0.99, two identical cold rebuilds, and at least 100 exact reference
candidates. That is not yet sufficient for promotion: aggregate recall can
hide failure concentrated in one query or density region. The tracked protocol
therefore keeps promotion disabled until query-local/worst-case coverage is
implemented.

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
until its query-local coverage gate is implemented.

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
  --protocol protocols/pythia_v0_1.yaml \
  --layers 0 \
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

## 6. Current non-claims and next gate

No tracked artifact currently says that Faiss has passed the Pythia
full-vocabulary audit. No approximate ledger is committed as evidence.
Candidate-boundary recall measures retrieval coverage only. It does not prove
semantic structure, topology, holonomy, phase, or causal relevance.

The next promotion work is to define and implement query-local, density/boundary
stratified, and worst-case recall requirements; freeze them before observing
the full audit outcome; then run the Pythia-70M integration pilot. Only after
that does the roadmap advance to deterministic candidate-graph and loop
construction.
