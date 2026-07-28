# Schema and Compatibility Change Record

SpiralLens records public and provisional persistence changes separately from
scientific results. Entries describe software contracts only; they do not
promote a claim.

## 2026-07-29 — PR #6 boundary foundation

### Added

- `spirallens.atlas-preparation-descriptor.v0.1`: canonical,
  pre-observation-only protocol, model, context, row-domain, capture, access,
  attempt, and interpretation declarations.
- `spirallens.atlas-preparation-view.v0.1`: descriptor-only preparation result
  with explicit no-manifest, no-payload, and no-execution facts.
- `spirallens.execution-attempt-terminal.v0.1`: terminal execution
  classification, access facts, quarantine disposition, and restricted
  provenance policy.

All three schemas are provisional.

### Internal diagnostic output

- `spirallens.distribution-validation.v0.1` labels the ephemeral JSON emitted
  by the repository-only wheel validator. It is not a public persistence
  schema or Python API, and no downstream artifact may bind it as evidence.

### Compatibility

- Canonical JSON primitives moved to the stable-candidate
  `spirallens.core.canonical` namespace.
- `spirallens.instrument_contracts.canonical` remains a compatibility
  re-export. Existing import paths and canonical bytes are unchanged.
- The frozen Pythia-70M public-example engineering protocol and receipt remain
  byte-identical. Their consumer gate now delegates to the generic typed
  access policy while preserving the historical string call sites.

### Non-migrations

- Existing atlas manifests are not preparation descriptors and must not be
  converted into them after observation.
- The historical neighbor `--prepare-only` flow remains a retrieval preflight,
  not subject protocol preparation.
- No D0-D8, subject, graph, referent, semantic, SAE, causal, or topological
  schema is promoted by this entry.
