from __future__ import annotations

from spirallens.access import (
    AtlasAccessPolicy,
    AtlasConsumer,
    AtlasPreparationDescriptor,
    AttemptPolicy,
    CaptureDeclaration,
    ContextIdentity,
    InterpretationContract,
    ModelIdentity,
    ProtocolIdentity,
    ProvenanceTaint,
    RowDomainIdentity,
)


def preparation_descriptor(
    *,
    descriptor_id: str = "subject-preparation-v0.1",
    output_id: str = "subject-atlas-v0.1",
    allowed_consumers: frozenset[AtlasConsumer] | None = None,
    provenance_taints: frozenset[ProvenanceTaint] = frozenset(),
    scientific_claim_eligible: bool = False,
    context_claim_eligible: bool = True,
    attempt_policy: AttemptPolicy | None = None,
) -> AtlasPreparationDescriptor:
    return AtlasPreparationDescriptor(
        descriptor_id=descriptor_id,
        protocol=ProtocolIdentity(
            schema_version="spirallens.subject-protocol.v0.1",
            protocol_id="subject-protocol-v0.1",
            source_sha256="1" * 64,
            canonical_sha256="2" * 64,
        ),
        access_policy=AtlasAccessPolicy(
            origin_execution_class="subject_preparation",
            claim_ceiling="level_0",
            scientific_claim_eligible=scientific_claim_eligible,
            allowed_consumers=(
                frozenset({AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION})
                if allowed_consumers is None
                else allowed_consumers
            ),
            provenance_taints=provenance_taints,
        ),
        model=ModelIdentity(
            model_id="Example/model",
            revision="3" * 40,
            architecture="ExampleArchitecture",
            files=(
                ("config.json", "4" * 64),
                ("model.safetensors", "5" * 64),
            ),
        ),
        context=ContextIdentity(
            binding_sha256="6" * 64,
            context_id="held-out-context-001",
            role="held_out",
            claim_eligible=context_claim_eligible,
        ),
        row_domain=RowDomainIdentity(
            selection_kind="explicit_sorted_ids",
            row_count=32,
            row_ids_sha256="7" * 64,
        ),
        capture=CaptureDeclaration(
            output_id=output_id,
            device="cpu",
            dtype="float32",
            observation_contract="all_residual_pre_post_layers",
        ),
        attempt_policy=(
            AttemptPolicy(
                resume_same_attempt_authorized=False,
                reuse_output_authorized=False,
                fresh_replay_same_protocol_authorized=True,
                retry_after_outcome_observation_authorized=False,
                relabel_authorized=False,
            )
            if attempt_policy is None
            else attempt_policy
        ),
        interpretation_contract=InterpretationContract(
            language_space_atlas=False,
            semantic_unit=False,
            p1_instrument_consumed=False,
            tokenizer_runtime_verified=False,
        ),
    )
