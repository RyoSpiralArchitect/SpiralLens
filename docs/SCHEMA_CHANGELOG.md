# Schema and Compatibility Change Record

SpiralLens records public and provisional persistence changes separately from
scientific results. Entries describe software contracts only; they do not
promote a claim.

## 2026-07-29 — PR #7 referent and numeric foundation

### Added

- `spirallens.referent-contract-set.v0.1`: canonical, registry-bound F0-F4
  pointwise referents, same-object rules, transformation formula identities,
  explicit unbound-field/interpolation state, ceilings, qualifiers, and
  non-claims.
- `spirallens.value-access-lineage.v0.1`: trusted-parent-bound, exact
  one-consumer value-decoding policy derivation.
- `spirallens.synthetic-generator-family-identity.v0.1`: mathematical
  construction-family identity separated from seed, implementation, and source
  digest.
- Provisional in-memory spectral-moment phantom/spec, estimator-input,
  oracle-truth, and case fingerprints: model-free F2/F4 development controls
  with fit/evaluation and truth/input separation, spec-derived canonical-case
  binding, harmonic resolvability/recovery and derived-arithmetic safety gates,
  and a conservative pre-allocation resource gate.
- `spirallens.observation-partition-receipt.v0.1`: an in-memory identity
  fingerprint with immutable array backing. It is not a persistence schema or
  parser contract.

The spectral and partition records' versioned `to_dict()` forms are content
fingerprints, not persistence schemas or parser contracts.

The persisted schemas are provisional. The tracked registry maps to
referent-contract digest
`4108ccda4f2a76920091bf2bf422b97297fe4d91ee54f14e2b03362e53e358f2`.

### Value-consumer boundary

- `load_instrument_bundle()` remains value-opaque. It exposes manifest relative
  paths and source-root metadata, but retains no payload descriptor and returns
  no payload bytes or decoded arrays; path secrecy is not the boundary.
- `open_numeric_payload_session()` is a separate lineage-gated API. It retains
  only requested descriptors from the same secure validation transaction and
  validates strict NPY, content row identity, and closed numeric relations.
  Decoded arrays use immutable `bytes` backing, so callers cannot re-enable
  their write flag.

### Compatibility and non-migrations

- Existing instrument artifact and bundle schema bytes and structural fields
  are unchanged.
- The closed `AtlasConsumer` vocabulary gains the compatible
  `numeric_payload_validation` value. Existing serialized policies keep their
  canonical bytes; this is an accepted-vocabulary extension, not a migration
  of stored records.
- The tracked P1 representation-phantom protocol and generator source are
  unchanged; the spectral-moment family is a separate foundation rather than a
  migration of that bundle.
- The frozen Pythia-70M engineering protocol and receipt remain byte-identical.
- No graph, domain, cycle, core, winding, D0-D8, subject, semantic, SAE, causal,
  or topology schema is promoted by this entry.

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
