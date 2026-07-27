# Pythia experiments

Tracked experiment manifests live here; generated arrays and journals live
under the ignored `runs/` directory.

The first implementation smoke uses `EleutherAI/pythia-70m`. The first
claim-bearing run is intended for `EleutherAI/pythia-160m` with the same frozen
protocol.

The current 70M public-example smoke validates only exact offline model-file
resolution, bounded capture, storage, checksum, manifest reload, and receipt
plumbing. Its frozen protocol allows only atlas integrity validation.
Candidate-ledger and neighbor plumbing belong to the preserved historical
retrieval path or synthetic/fake fixtures; they are not consumers of a new
public-example engineering atlas.

The frozen declaration is
[`protocols/pythia70_public_example_plumbing_v0_1.yaml`](../../protocols/pythia70_public_example_plumbing_v0_1.yaml).
Its no-overwrite canonical receipt is published under
[`receipts/`](receipts/) only after checksum and reload validation.

The receipt records `model_accessed=true` and
`activation_values_persisted=true`, while keeping scientific claim eligibility
false and D0-D8 plus candidate, graph, field, core, loop, semantic, SAE, and
integer stages `not_run`. It is not evidence for semantic phase, holonomy, or
topology and is not a subject run. For any future claim-bearing run, retain the
resolved immutable model revision and capture backend recorded in its own
separately authorized manifest.
