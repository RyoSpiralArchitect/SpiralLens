# Pythia experiments

Tracked experiment manifests live here; generated arrays and journals live
under the ignored `runs/` directory.

The first implementation smoke uses `EleutherAI/pythia-70m`. The historically
intended first claim-bearing family is `EleutherAI/pythia-160m`, but it requires
a separately versioned and reviewed `SubjectProtocolManifest` that follows the
same capture discipline. Neither this 70M protocol nor the model-family intent
authorizes that future preparation or run.

A private source-only identity-acquisition contract now defines how a later
review may record bounded provider model metadata and exact `config.json`
bytes for Pythia-160M. The contract source itself performs no request and ships
no receipt instance. Its unregistered script has only been exercised through
blocked preflight and synthetic tests in the change that introduces it; a later
invocation must use a separately reviewed exact source commit. Equality with a
local `origin/main` tracking ref alone is not remote-current or review proof.
Any resulting four-file directory remains `review_pending`,
with provider sibling metadata unrecomputed, weights and tokenizer unread, and
all preparation, model-access, execution, capture, scientific, `SCI-S1`, and
`SCI-S2` authority closed.
The later one-shot acquisition reserves and fsyncs an empty private stage before
its first request; any failure after successful reservation retains the stage
and permits no cleanup, resume, or retry. Its no-replace publication assumes a
quiescent, honest local checkout and does not claim resistance to a hostile
same-user rename race.

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
