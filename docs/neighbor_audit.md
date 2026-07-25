# Neighbor Audit and Receipt Contract

- **Status:** recall methodology frozen; v0.3 producer preserved; v0.4
  consumer-safe qualification and freeze completed; one-shot subject outcome
  terminal `insufficient`; no promotion
- **Backend:** legacy `spirallens.faiss-hnsw-range@0.1`; qualified native-call path `@0.2`
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

Receipt v0.2 also regenerates and validates its synthetic fixture in a fresh
Faiss subprocess. The Torch-bearing parent does not resolve an OpenMP collision
by setting `KMP_DUPLICATE_LIB_OK` or any equivalent unsafe environment
workaround.

Backend v0.2 separates the outer `query_batch_size=512` artifact batch from
`range_call_batch_size=1`. Before each native call, the worker proves that its
theoretical maximum result count is no greater than the frozen
`max_native_call_hits=50,304`; after the call it validates limits, score
finiteness, label bounds, and the cumulative raw-hit budget before
serialization.

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

Freezing this methodology did not freeze or pass a Pythia execution. The
generic tracked v0.4 protocol remains `preregistered-draft`, with null atlas
row/group and receipt digests and promotion disabled. A distinct
atlas-specific v0.4 copy later bound the methodology, qualification receipt,
row universe, layer, and candidate protocol before one subject execution. The
published v0.3 protocol bytes remain preserved for static parsing and
historical inspection only. Because the receipt-v0.1 bytes were never tracked
and consumer binding was never established, v0.3 cannot authorize preflight,
subject execution, or approximate-candidate persistence. The only executed
consumer-safe path used v0.4 with qualification receipt schema v0.2.

## 3. Production-shape native qualification

Backend v0.2 could not enter a subject audit without a canonical qualification
receipt. The completed preflight had no atlas or subject-data argument and ran
the same range-call helper twice in independent subprocesses over a
deterministic synthetic fixture with 50,304 float32 rows, hidden size 512, and
512 queries.
It binds the exact fixture and query digests, index and hit-array digests,
Faiss native/distribution digests, search config, and both cold-run results.
It also records the exact clean, live-pushed preflight commit and the
`src/spirallens` Git tree. The runner revalidates that source immediately
before replacing its exclusive reservation with the receipt. The results must
be byte-repeatable.

One receipt-v0.1 producer run was observed to return `pass`. Its volatile
artifact was lost during reboot before it could be tracked, and consumer
binding was not established: prepare-only loading after Torch had entered the
process exposed an OpenMP collision. This is not a failed retrieval audit or a
subject `pass`, `fail`, or `insufficient` outcome. It does not authorize
promotion and did not consume the subject one-shot. Receipt v0.2 is a distinct
schema and output identity; it moves consumer fixture regeneration across the
fresh-process boundary instead of weakening the runtime safety policy.

The executed producer bound the generic v0.4 draft protocol SHA-256
`c4c10eebc933d30c31cd7115ba6f23d5fc3aa8af07ff393c4150adc4bb3522cc`.
Its output path is occupied by the tracked canonical receipt and must not be
regenerated or overwritten. The receipt SHA-256 is
`3c8c136c1e0dbbd84033b3c7144708b496e79bedc21dd9d5768494d37ba46b76`.
It qualifies retrieval plumbing only. It never authorizes candidate
persistence, and it contains no subject recall observation.

## 4. Bound identities

The index build receipt binds:

- original state shape, dtype, and SHA-256;
- normalized float32 worker-state SHA-256;
- ordered global row-key SHA-256;
- comparison group, currently one `layer_index=N`;
- Faiss index bytes SHA-256;
- HNSW construction/search settings;
- Faiss, NumPy, Python, platform, and compile-option provenance;
- single-thread execution and worker isolation mode.
- for backend v0.2, the qualification receipt, fixture, native-call batch, and
  maximum native-call hit digests.

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

## 5. Historical trusted-digest workflow

Before the terminal v0.4 execution, the atlas-specific values were computed
without building an index or exposing audit results:

```bash
spirallens neighbor-audit \
  --manifest runs/pythia70-full/manifest.json \
  --layer 0 \
  --protocol protocols/pythia_neighbor_v0_4.yaml \
  --prepare-only
```

This invocation is historical provenance and must not be rerun against the
consumed Pythia-70M identity. Before a genuinely new audit, a separately
reviewed protocol copy must bind the emitted
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

The preserved v0.2 synthetic Pythia-70M layer-0 attempt used:

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

That v0.2 worker terminated after the observed native
`RangeSearchResult.do_allocation` exception, before any scientific outcome;
this identifies the failure boundary, not a proven upstream root cause. Its one
shot is consumed, its marker is retained, and it is not retried. The v0.3
producer remediation introduced a new backend version and preregistered
neighbor protocol. Its receipt-v0.1 producer pass was observed, but the later
consumer boundary aborted before a frozen neighbor protocol or execution
   freeze was issued and produced no subject outcome. The v0.4 successor
   therefore preserved backend version 0.2 while using a distinct receipt
   schema, qualification path, neighbor protocol, execution freeze, and subject
   output.

The v0.4 successor then executed once under:

- qualification receipt SHA-256
  `3c8c136c1e0dbbd84033b3c7144708b496e79bedc21dd9d5768494d37ba46b76`;
- frozen neighbor protocol SHA-256
  `12f204db95a5e01687935304ab93d56e94bcb8d33e5653a56b18437badaa7ff7`;
- execution-freeze SHA-256
  `8060ae367075e3eeab6c6dc9f9e709b982840384b4bfd043e5af14204a2b8940`.

Its terminal result was `insufficient`: all 1,000 selected queries had zero
exact-reference retrieval and candidate support. Deterministic empty output
passed, every recall quantity remained null, and no promotion receipt was
issued. The output is not rerun or used to retune its boundary. The exact
outcome witness is preserved in
[`../protocols/pythia70_slot_only_001_layer0_subject_audit_v0_4_outcome_observation.yaml`](../protocols/pythia70_slot_only_001_layer0_subject_audit_v0_4_outcome_observation.yaml);
its exact interpretation is recorded in the
[Experiment Interpretation Ledger](EXPERIMENT_INTERPRETATION_LEDGER.md).

For a genuinely new protocol with new identities and an unreserved output, the
generic execution shape remains:

```bash
NEIGHBOR_PROTOCOL_SHA="$(shasum -a 256 protocols/frozen-neighbor.yaml | awk '{print $1}')"
EXECUTION_FREEZE="protocols/frozen-subject-execution.yaml"
EXECUTION_FREEZE_SHA="$(shasum -a 256 "$EXECUTION_FREEZE" | awk '{print $1}')"

spirallens neighbor-audit \
  --manifest runs/pythia70-full/manifest.json \
  --layer 0 \
  --protocol protocols/frozen-neighbor.yaml \
  --expected-protocol-sha256 "$NEIGHBOR_PROTOCOL_SHA" \
  --execution-freeze "$EXECUTION_FREEZE" \
  --expected-execution-freeze-sha256 "$EXECUTION_FREEZE_SHA" \
  --output runs/pythia70-full/layer-0-neighbor-audit.json
```

This example must not be substituted back into either consumed subject output
path. The command may emit `pass`, `fail`, or `insufficient`. Only a frozen,
deviation-free `pass` under a protocol that explicitly authorizes promotion
can produce a verified receipt. The audit output prints its SHA-256; preserve
that value outside the artifact before candidate extraction.
Before computation, the CLI verifies the freeze record against its trusted
digest, literal argv and absolute paths, clean pushed Git state, fixed Git
binary, source-only import cache state, Python executable, and
content-addressed NumPy/Faiss distributions. It then reserves the non-symlink
output pathname exclusively. Before touching that marker, the writer fsyncs a
complete recovery sidecar. A failure therefore leaves either the original
reservation marker or a complete recovery artifact, and the reserved path
blocks an implicit retry.

The validated Python object is an internal fail-closed execution witness, not
an in-process security boundary against code that is already executing inside
the interpreter.

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

## 6. Fail-closed behavior

Publication is rejected when any of the following changes:

- protocol bytes, audit bytes, candidate protocol, or trusted digest;
- atlas manifest, token-row identity, selected states, or drifts;
- layer group, query boundary, or query sampling;
- backend ID/version/config/runtime or index bytes;
- qualification receipt, fixture, native binary, or native-call batch;
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

## 7. Current non-claims and next gate

No tracked artifact currently says that Faiss has passed the Pythia
full-vocabulary audit. No approximate ledger is committed as evidence.
Candidate-boundary recall measures retrieval coverage only. It does not prove
semantic structure, topology, holonomy, phase, or causal relevance.

The atlas-specific v0.4 row/layer binding, adversarial review, freeze, and
one-shot execution are complete. The result was `insufficient`, so the backend
was not promoted and that execution path is terminal.

Separately, a post-outcome conceptual review established prospective
order-parameter and graph-family gates for a new Level-0 question under the
[Fundamental Frame](FUNDAMENTAL_FRAME.md). No inference from the audit status
or empty support selected those objects. Even a future retrieval pass would
authorize retrieval coverage only; geometry, defect, topology, and semantics
retain their separate gates.
