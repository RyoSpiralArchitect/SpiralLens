# P4 bounded-witness and noisy-observation prototype

Decision date: 2026-09-13. Synthetic development / Level 0.
This specifies a new local mathematical prototype and deterministic controls,
not a new Furnace campaign, calibrated coverage result, or model experiment.
The specification is committed before exercising its new control fixtures.
All #122 observations, rules, receipts and failures remain historical evidence.

## Question and the missing assumption

Can an explicitly bounded, separately measured background witness bound the
chosen reference's common offset, while evaluation error propagates into
center and separation ranges rather than an arbitrarily enlarged scalar gate?

Independent repeat seeds or a wider spatial stencil cannot identify an affine
bias shared by every channel. Agreement is not absolute calibration. Without
a bounded witness the readout must remain `common_mode_unidentified`, with
no center/separation bounds. A declared independent witness is a synthetic
assumption, not a certification of physical independence or a real-model
background-only channel. A shared reference/witness bias is a mandatory
assumption-violation control and must not be silently repaired.

## Reference budget and equal-cost placement comparison

Measure the witness at the five-point cross (origin, +/-h on each axis), for
h=0.5 and h=1.0. Both placements use five observations and the same declared
pointwise moment-error radius. Fit the affine design X=[1,x,y]. If each
two-vector observation has norm error at most epsilon_i, use

    witness_row_radii = abs(pinv(X)) @ epsilon + numerical_margin
    reference_row_radii[j] = norm(reference[j] - witness[j])
                             + witness_row_radii[j] + numerical_margin

The second line is the triangle inequality, not a fitted confidence level.
For equal epsilon, the first line before numerical margins is
(epsilon, epsilon/h, epsilon/h). Wider placement halves the linear budgets
but leaves the constant budget unchanged. It does not remove common bias.
The selected reference is not corrected or replaced by an ideal coefficient.
The inherited empirical envelope is neither enlarged nor relabeled.

Affine witness fit residuals are diagnostics, not a procedure for learning
or inflating the pointwise bound. The affine-background assumption remains
explicit: even a finite held-out check cannot certify global affinity.

## Propagate evaluation error before interpreting roots

Keep the predecessor's nine fit and sixteen held-out coordinates. New input
epsilon_i bounds the Euclidean error in the observed two-component **moment
field**, after the adapter. This is deliberately different from #122's
unbounded Gaussian raw-probe perturbations. No Gaussian standard deviation
is converted to a hard bound, and no bound is fitted to clean/noisy differences.

For the quadratic design Q=[1,x,y,x*x,x*y,y*y], propagate

    coefficient_noise_radii = abs(pinv(Q_fit)) @ epsilon_fit
    heldout_limits = epsilon_heldout
                     + abs(Q_heldout @ pinv(Q_fit)) @ epsilon_fit

Add the reference budgets only to the constant/x/y coefficient radii.
Add an explicit 1e-12 numerical allowance to each coefficient and held-out
limit. This fixed float64 allowance is an engineering guard, not a formally
verified roundoff certificate. Do not reuse or silently modify the old 1e-9
gate. Triangle bounds do not assume independent errors or combine variances.

For complex polynomial coefficients c,bx,by,qxx,qxy,qyy, define the existing
A=(qxx-qyy-i*qxy)/4, B=(qxx-qyy+i*qxy)/4, C=(qxx+qyy)/2.
Their radii are rA=rB=(rxx+rxy+ryy)/4 and rC=(rxx+ryy)/2.
The active and inactive linear radii are rL=(rx+ry)/2.

Retain both orientations; reject inconsistent inactive curvature/linear
terms. If active curvature is not separated from zero, report unavailable
root bounds (`curvature_unresolved` or `zero_not_excluded`), not a verified
affine/zero field. For one compatible orientation with abs(a)>rA and the
existing amplitude floor, use

    m = -L/(2*a); D = m*m - c/a
    rm = (rL + 2*abs(m)*rA)/(2*(abs(a)-rA))
    rD = 2*abs(m)*rm + rm*rm
         + (rc + abs(c/a)*rA)/(abs(a)-rA)
    separation = [2*sqrt(max(0,abs(D)-rD)), 2*sqrt(abs(D)+rD)]
    root_radius = rm + sqrt(rD)

These are conservative outer bounds conditional on the specified exact
holomorphic/antiholomorphic quadratic family and the declared error bounds.
Passing finite observations does not establish global family membership or
joint feasibility of every enclosing disk. Never infer topology from that
compatibility. Failure to exclude a single center is not proof of one center.

## Fixed local development controls

Use development seed 7 in a new namespace; no campaign seeds or independent
coverage cohort are allocated here. Measure clean F2/F4 through the existing
P128 probe/moment construction before adding bounded moment-space error.
Witness error radius is 1e-6, with distinct witness/reference noise streams.

- Two witness placements h=0.5/1.0, paired equal-cost noise draws.
- Four reference stresses: none, constant bias 5e-4, linear-row bias 5e-4,
  and constant bias 5e-4 shared by reference and witness. Fixed directions
  pi/7 and, for the y row, pi/7+pi/3. Bias is a coefficient-space stress,
  not a measured physical sensor drift.
- Four declared evaluation-error radii: 0, 1e-7, 1e-5, 1e-3. A bounded disk
  draw is reused across scales, fixtures, placements and F2/F4 for pairing.
- Nine fixtures: double-root single, same-sign pairs 0.08/0.16, reverse pair
  0.16, zero, nonzero constant, linear, dipole and cubic; alpha=0.10.
- Independently bounded witness and absent-witness readouts are both kept.

This gives 2*4*4*9*2*2=1,152 deterministic development readouts, not 1,152
independent trials, a statistical power estimate, or a discovery rate.
Inference consumes only measurements and declared contracts. Geometry and
actual contract coverage are scored only after the readout is sealed.
The shared-bias cases deliberately violate the witness assumption and remain
separate from valid-contract checks; they demonstrate the blind spot.

Unit tests additionally exercise underdeclared noise, nonaffine data,
unresolved curvature, malformed/missing budgets, source binding and replay.
All statuses/missing intervals are retained. No successful fixture may select
a reference, noise radius, orientation threshold or revised rule.

## Evidence, exit and next experiment

The local CLI produces an exclusive-create JSON report with full readouts,
measurement inputs, scoring, source hashes and deterministic replay. Record
tests separately from developmental fixture observations. No legacy local
component/loop score is changed; this does not acquire new full-grid loops.

Before a future campaign: freeze actual witness availability/transfer checks,
new independent cohort roles and seeds, moment-error calibration and external
validation, resource limits and terminal handling. A raw-probe noise model
requires its own adapter propagation/qualification; it is not implemented by
this post-adapter contract. Until then the campaign remains not frozen/not run.

The September research watch informs distinct lanes:

- [CausalArena](https://arxiv.org/abs/2609.11897): keep conditions and failure
  modes separate; do not import its DAG benchmark as evidence for these fields.
- [Information geometry](https://arxiv.org/abs/2609.11063): later compare
  activation displacement and output effect. Fisher cost does not estimate
  shared bias. Its constructed weekday/month phase coordinates may inform a
  known-cycle control, not a discovered model vortex. No implementation here.
- [Legible Failures](https://arxiv.org/abs/2609.11216),
  [MUtE](https://arxiv.org/abs/2609.11253), and
  [Looped Flows](https://arxiv.org/abs/2609.11801): future readout/intervention,
  known-zero cycle, and recurrent-dynamics controls, respectively. Probe
  failure is not information absence; reversibility is not holonomy.

No model phase/transition/winding, order parameter, verified core, digital
twin validation or scientific authority follows. D7/D8, SCI-S1/S2 and the
Pythia-160M gate are unchanged. No automation or remote compute is changed.
