# SpiralLens glossary

SpiralLens keeps similarly named ideas separate in both prose and code.

- **State space**: the space in which an observed model state lives.
- **Regime**: a metastable or operationally distinct region of a state space.
- **Transport angle**: a continuous angular observable associated with a chosen
  transport operator or local frame. It is not automatically semantic.
- **Holonomy**: the frame mismatch remaining after transport around a closed
  path. It is generally continuous.
- **Topology class**: a property invariant under the declared class of
  deformations.
- **Sampled winding**: the principal-branch phase increment around a declared
  discrete loop, divided by \(2\pi\). It can alias unresolved turns between
  samples and is not, by itself, the winding of an unknown continuous field.
- **Topology promotion**: a later claim requiring explicit sampling or
  smoothness assumptions, multi-resolution controls, and deformation tests.
  SpiralLens v0.1 does not emit this claim.
- **Angular spectrum**: a Fourier decomposition around a preregistered loop.
  “OAM” is reserved for the motivating optical analogy.
- **Candidate**: an observation that passed the stated structural gates. A
  candidate is not a verified semantic feature or vortex.

Three evolution axes must also remain explicit:

- `token_position`: movement through a sequence;
- `layer_index`: transport through model depth;
- `training_step`: movement through model training.

No unqualified field named `phase` or `time` should be added to a persisted
artifact.
