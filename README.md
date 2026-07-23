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
2. Stream a fixed-context Pythia token-ID atlas to memory-mapped arrays.
3. Separate radial/norm effects from angular and layer-drift effects.
4. Emit a schema-validated, provenance-bound candidate ledger without semantic
   labels.
5. Run protocol-declared loop, gauge, architecture, radius, and orientation nulls
   on shortlisted candidates.

Pythia-70M is a plumbing smoke. Pythia-160M is the first intended scientific
run. SAE annotation, training-checkpoint trajectories, transfer operators, and
natural-language interpretation are intentionally deferred.

The executable path currently reaches step 4 for bounded exact searches.
The mathematical loop/holonomy tools and architecture-factor/null primitives
exist, but are not yet wired from a Pythia candidate into a Level-2 result.
The exact pairwise search fails loudly above 10,000 rows until an audited
nearest-neighbor stage lands; a full-vocabulary atlas can still be captured.

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

Capture a bounded Pythia-70M plumbing atlas. `context-ids` declares the fixed
sequence and `position` is the slot replaced by each swept token ID:

```bash
spirallens atlas \
  --model EleutherAI/pythia-70m \
  --output runs/pythia70-smoke \
  --context-ids 0 \
  --position 0 \
  --max-tokens 32 \
  --batch-size 8 \
  --device auto
```

Then apply the tracked, semantics-free structural gates:

```bash
spirallens candidates \
  --manifest runs/pythia70-smoke/manifest.json \
  --output runs/pythia70-smoke/candidates.jsonl \
  --protocol protocols/pythia_v0_1.yaml
```

`--full-vocabulary` is required to authorize an unbounded atlas explicitly.
Atlas arrays are memory-mapped, manifests are written atomically, completed
files are checksummed, and a resume request must match the original capture
fingerprint.

## Roadmap: experiment to library

SpiralLens is intentionally growing in two stages: first prove that the
instrument is scientifically auditable, then stabilize the parts that deserve
to become a general library.

- **Now — instrument foundation (`0.1.x`):** analytic phantoms, Pythia
  activation atlases, structural candidate ledgers, versioned provenance, and
  fail-closed storage.
- **Next — candidate-to-loop system:** context banks, audited full-vocabulary
  neighbor search within each declared context/position slice, cycle
  construction, relative holonomy, and architecture/null accounting on
  Pythia-70M.
- **First scientific protocol:** freeze the integrated instrument and run the
  same preregistered design on Pythia-160M without tuning on the result.
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
- `semantics/` is downstream annotation and evaluation, never discovery.
- `benchmarks/icicl/` is an optional external benchmark and is not imported by
  the core package.

See [the glossary](docs/glossary.md) and
[the claim ladder](docs/claim_ladder.md) before adding a new metric or persisted
field.

## License

SpiralLens is licensed under the
[Apache License 2.0](LICENSE).
