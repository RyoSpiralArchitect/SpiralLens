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
approximate backend has been selected or promoted yet; a full-vocabulary atlas
can still be captured.

## Development install

```bash
python -m pip install -e '.[models,dev]'
```

The analytic calibration requires only the core dependencies:

```bash
python -m pip install -e .
spirallens calibrate
```

The full test suite includes the offline Pythia adapter and therefore uses both
extras:

```bash
python -m pip install -e '.[models,dev]'
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

Candidate ledger v0.2 separates retrieval from judgment. A backend sees only
the unprojected `resid_pre` row matrix and proposes canonical global row-index
pairs. SpiralLens then recomputes every state and drift metric in float64 from
the original arrays. Backend scores cannot pass a gate or enter candidate
identity.

The bounded exact implementation is the current reference backend. The current
preregistered-draft candidate-boundary recall contract for a future approximate
backend is declared in
[`protocols/pythia_neighbor_v0_2.yaml`](protocols/pythia_neighbor_v0_2.yaml):
the initial target is `>= 0.99` across deterministic repeats. A reference set
with zero exact candidates is `insufficient`, never an automatic pass. The
audit API and internally validated, tamper-evident JSON artifact are
implemented. Every audit backend receives a detached read-only state snapshot,
with pre/post input digests checked on each cold rebuild. No real
full-vocabulary approximate backend is yet called audited; approximate-backend
candidate persistence remains disabled until an audit-receipt binding is
implemented.

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
  fail-closed storage, plus a state-only neighbor interface and exact reference.
- **Next — candidate-to-loop system:** a public synthetic engineering context
  bank, a real approximate full-vocabulary backend that passes the frozen
  recall audit within each declared context/position slice, cycle construction,
  relative holonomy, and architecture/null accounting on Pythia-70M.
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
