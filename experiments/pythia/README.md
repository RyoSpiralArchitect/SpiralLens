# Pythia experiments

Tracked experiment manifests live here; generated arrays and journals live
under the ignored `runs/` directory.

The first implementation smoke uses `EleutherAI/pythia-70m`. The first
claim-bearing run is intended for `EleutherAI/pythia-160m` with the same frozen
protocol.

The 70M smoke validates capture, storage, checksum, resume, and candidate-ledger
plumbing only. It is not evidence for semantic phase, holonomy, or topology.
For a claim-bearing run, retain the resolved immutable model revision and the
capture backend recorded in the atlas manifest.
