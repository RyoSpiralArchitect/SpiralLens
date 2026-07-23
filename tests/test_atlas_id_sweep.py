from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
import torch

from spirallens.adapters import PythiaAdapter
from spirallens.atlas import (
    ATLAS_CONTEXT_BINDING_SCHEMA_VERSION,
    ATLAS_SCHEMA_VERSION,
    AtlasIntegrityError,
    AtlasStateError,
    ContextBankBinding,
    SweepConfig,
    load_manifest,
    run_id_sweep,
    select_token_ids,
)
from spirallens.contexts import (
    BankStatus,
    ContextBank,
    ContextRole,
    ContextSpec,
    LoadedContextBank,
    ModelBinding,
    SourceBinding,
    SweepDomain,
    TokenizerBinding,
)

from fake_pythia import FakePythiaForCausalLM


def _canonical_sha256(value) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _refresh_bound_request_digests(
    request,
    *,
    refresh_binding: bool = True,
) -> None:
    if refresh_binding:
        request["context_bank_binding_sha256"] = _canonical_sha256(
            request["context_bank_binding"]
        )
    identity = dict(request)
    identity.pop("batch_size_initial", None)
    identity.pop("batch_size_latest", None)
    identity.pop("request_identity_sha256", None)
    request["request_identity_sha256"] = _canonical_sha256(identity)


def _adapter(model: FakePythiaForCausalLM | None = None) -> PythiaAdapter:
    return PythiaAdapter(
        model or FakePythiaForCausalLM(),
        model_id="offline/fake-pythia",
        revision="fixed-test-weights",
    )


def _bound_adapter(
    model: FakePythiaForCausalLM | None = None,
) -> PythiaAdapter:
    return PythiaAdapter(
        model or FakePythiaForCausalLM(),
        model_id="offline/fake-pythia",
        revision="a" * 40,
    )


def _context_binding(
    tmp_path,
    *,
    sweep_domain: SweepDomain = SweepDomain.MODEL_EMBEDDING_ROWS,
    source_sha256: str = "9" * 64,
) -> ContextBankBinding:
    context = ContextSpec(
        context_id="synthetic-bound",
        role=ContextRole.EXAMPLE,
        family_id="mechanical-family",
        source_id="project-synthetic",
        template_id="interior-slot",
        template_ids=(1, None, 2),
        attention_mask=(1, 1, 1),
        observation_position=2,
    )
    bank = ContextBank(
        bank_id="offline-example-v1",
        status=BankStatus.EXAMPLE,
        license="Apache-2.0",
        claim_eligible=False,
        source=SourceBinding(
            kind="project_authored_synthetic",
            source_id="offline-fixture",
        ),
        model=ModelBinding(
            model_id="offline/fake-pythia",
            requested_revision="test",
            resolved_revision="a" * 40,
            vocab_size=11,
        ),
        tokenizer=TokenizerBinding(
            tokenizer_id="offline/fake-tokenizer",
            requested_revision="test",
            resolved_revision="b" * 40,
            addressable_size=9,
            tokenizer_class="FakeTokenizer",
            implementation="fast",
            transformers_version="test",
            tokenizers_version="test",
            add_special_tokens=False,
            file_sha256=(("tokenizer.json", "8" * 64),),
        ),
        sweep_domain=sweep_domain,
        contexts=(context,),
    )
    loaded = LoadedContextBank(
        bank=bank,
        source_path=tmp_path / "context-bank.yaml",
        source_sha256=source_sha256,
        canonical_sha256=bank.sha256,
    )
    return ContextBankBinding(
        loaded=loaded,
        context_id=context.context_id,
        role=ContextRole.EXAMPLE,
    )


def test_select_token_ids_supports_subset_and_max_tokens() -> None:
    np.testing.assert_array_equal(
        select_token_ids(7, subset=(6, 2, 4), max_tokens=2),
        np.asarray((6, 2), dtype=np.int64),
    )
    np.testing.assert_array_equal(
        select_token_ids(4), np.arange(4, dtype=np.int64)
    )
    with pytest.raises(ValueError, match="duplicate"):
        select_token_ids(7, subset=(1, 1))
    with pytest.raises(ValueError, match="out-of-range"):
        select_token_ids(7, subset=(7,))
    with pytest.raises(TypeError, match="integers"):
        select_token_ids(7, subset=(1.5,))


def test_bounded_prefix_is_not_labeled_as_full_vocabulary(tmp_path) -> None:
    manifest = run_id_sweep(
        _adapter(),
        SweepConfig(
            output_dir=tmp_path / "atlas",
            context_ids=(0,),
            position=0,
            max_tokens=2,
        ),
    )

    assert manifest["request"]["selection"]["kind"] == "vocabulary_prefix"
    assert manifest["request"]["num_tokens"] == 2
    assert set(manifest["request"]) == {
        "model_id",
        "requested_model_revision",
        "resolved_model_revision",
        "context_ids",
        "attention_mask",
        "position",
        "selection",
        "num_tokens",
        "token_ids_sha256",
        "batch_size_initial",
        "batch_size_latest",
        "capture_dtype",
        "capture_fingerprint",
        "config_sha256",
    }
    assert "context_bank_binding" not in manifest["request"]
    assert "context_bank_binding_sha256" not in manifest["request"]
    assert "token_domain" not in manifest["request"]
    assert "language_space_atlas" not in manifest["request"]
    assert "semantic_unit" not in manifest["request"]


def test_context_bank_binding_is_complete_and_load_validated(tmp_path) -> None:
    binding = _context_binding(tmp_path)
    output_dir = tmp_path / "bound-atlas"

    manifest = run_id_sweep(
        _bound_adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=binding.materialized_context_ids,
            position=binding.context.observation_position,
            subset=(3, 4),
            context_bank_binding=binding,
        ),
    )

    request = manifest["request"]
    persisted = request["context_bank_binding"]
    assert persisted["schema_version"] == ATLAS_CONTEXT_BINDING_SCHEMA_VERSION
    assert request["context_bank_binding_sha256"] == binding.sha256
    assert persisted["bank"]["source_sha256"] == "9" * 64
    assert persisted["bank"]["canonical_sha256"] == binding.loaded.bank.sha256
    assert persisted["bank"]["content"] == binding.loaded.bank.to_dict()
    assert persisted["selected_context"] == {
        "context_id": "synthetic-bound",
        "role": "example",
        "entry_order_index": 0,
        "context_spec_sha256": binding.context.sha256,
        "context_input_sha256": binding.context.input_sha256,
        "sweep_position": 1,
        "observation_position": 2,
    }
    assert (
        persisted["tokenizer_provenance_sha256"]
        == binding.loaded.bank.tokenizer.sha256
    )
    assert persisted["interpretation_contract"] == {
        "language_space_atlas": False,
        "semantic_unit": False,
        "decoded_strings_used_for_selection": False,
        "semantic_annotation_used": False,
        "sae_annotation_used": False,
        "projection_used": False,
    }
    assert request["context_ids"] == [1, 0, 2]
    assert request["sweep_position"] == 1
    assert request["observation_position"] == 2
    assert request["token_domain"] == {
        "kind": "model_embedding_rows",
        "size": 11,
        "model_vocab_size": 11,
        "tokenizer_addressable_size": 9,
    }
    assert request["language_space_atlas"] is False
    assert request["semantic_unit"] is False
    assert len(request["request_identity_sha256"]) == 64
    assert load_manifest(output_dir) == manifest

    resumed = run_id_sweep(
        _bound_adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=binding.materialized_context_ids,
            position=binding.context.observation_position,
            subset=(3, 4),
            batch_size=1,
            context_bank_binding=binding,
            resume=True,
        ),
    )
    assert resumed["run_id"] == manifest["run_id"]
    assert len(resumed["attempts"]) == 1


def test_interrupted_bound_sweep_resumes_with_only_batch_size_changed(
    tmp_path,
) -> None:
    binding = _context_binding(tmp_path)
    output_dir = tmp_path / "bound-resumable"
    model = FakePythiaForCausalLM()
    model.fail_on_token = 5
    adapter = _bound_adapter(model)

    with pytest.raises(RuntimeError, match="intentional failure"):
        run_id_sweep(
            adapter,
            SweepConfig(
                output_dir=output_dir,
                context_ids=binding.materialized_context_ids,
                position=binding.context.observation_position,
                subset=(3, 4, 5, 6),
                batch_size=2,
                context_bank_binding=binding,
            ),
        )
    failed = load_manifest(output_dir)
    assert failed["status"] == "failed"
    assert failed["progress"]["completed_rows"] == 2

    model.fail_on_token = None
    completed = run_id_sweep(
        adapter,
        SweepConfig(
            output_dir=output_dir,
            context_ids=binding.materialized_context_ids,
            position=binding.context.observation_position,
            subset=(3, 4, 5, 6),
            batch_size=1,
            context_bank_binding=binding,
            resume=True,
        ),
    )

    assert completed["status"] == "complete"
    assert completed["progress"]["completed_rows"] == 4
    assert completed["request"]["batch_size_initial"] == 2
    assert completed["request"]["batch_size_latest"] == 1
    assert completed["attempts"][-1]["resume_from_row"] == 2
    assert load_manifest(output_dir) == completed


@pytest.mark.parametrize(
    ("override", "message"),
    (
        ({"context_ids": (0, 0, 0)}, "context_ids do not match"),
        ({"position": 1}, "observation position"),
        ({"sweep_position": 0}, "ContextSpec slot"),
        ({"attention_mask": (0, 1, 1)}, "attention_mask"),
    ),
)
def test_sweep_config_rejects_context_bank_override(
    tmp_path,
    override,
    message,
) -> None:
    binding = _context_binding(tmp_path)
    kwargs = {
        "output_dir": tmp_path / "atlas",
        "context_ids": binding.materialized_context_ids,
        "position": binding.context.observation_position,
        "context_bank_binding": binding,
    }
    kwargs.update(override)

    with pytest.raises(ValueError, match=message):
        SweepConfig(**kwargs)


def test_bound_sweep_rejects_model_and_token_domain_mismatch(tmp_path) -> None:
    binding = _context_binding(
        tmp_path,
        sweep_domain=SweepDomain.TOKENIZER_ADDRESSABLE,
    )
    config = SweepConfig(
        output_dir=tmp_path / "atlas",
        context_ids=binding.materialized_context_ids,
        position=binding.context.observation_position,
        subset=(9,),
        context_bank_binding=binding,
    )

    wrong_model = PythiaAdapter(
        FakePythiaForCausalLM(),
        model_id="offline/other-pythia",
        revision="a" * 40,
    )
    with pytest.raises(ValueError, match="adapter model ID"):
        run_id_sweep(wrong_model, config)
    with pytest.raises(ValueError, match="out-of-range"):
        run_id_sweep(_bound_adapter(), config)


def test_resume_rejects_changed_context_bank_source_digest(tmp_path) -> None:
    output_dir = tmp_path / "atlas"
    original = _context_binding(tmp_path, source_sha256="1" * 64)
    run_id_sweep(
        _bound_adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=original.materialized_context_ids,
            position=original.context.observation_position,
            subset=(3,),
            context_bank_binding=original,
        ),
    )
    changed = _context_binding(tmp_path, source_sha256="2" * 64)

    with pytest.raises(AtlasStateError, match="fingerprint"):
        run_id_sweep(
            _bound_adapter(),
            SweepConfig(
                output_dir=output_dir,
                context_ids=changed.materialized_context_ids,
                position=changed.context.observation_position,
                subset=(3,),
                context_bank_binding=changed,
                resume=True,
            ),
        )
    persisted = json.loads(
        (output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert len(persisted["attempts"]) == 1


def test_load_rejects_tampered_context_bank_binding(tmp_path) -> None:
    binding = _context_binding(tmp_path)
    output_dir = tmp_path / "atlas"
    run_id_sweep(
        _bound_adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=binding.materialized_context_ids,
            position=binding.context.observation_position,
            subset=(3,),
            context_bank_binding=binding,
        ),
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["request"]["context_bank_binding"]["bank"]["content"]["contexts"][0][
        "role"
    ] = "held_out"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(AtlasIntegrityError, match="binding digest mismatch"):
        load_manifest(output_dir)


def test_load_rejects_context_binding_downgrade_to_legacy(tmp_path) -> None:
    binding = _context_binding(tmp_path)
    output_dir = tmp_path / "atlas"
    run_id_sweep(
        _bound_adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=binding.materialized_context_ids,
            position=binding.context.observation_position,
            subset=(3,),
            context_bank_binding=binding,
        ),
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["request"]["context_bank_binding"]
    del manifest["request"]["context_bank_binding_sha256"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(AtlasIntegrityError, match="context-bank-only"):
        load_manifest(output_dir)


@pytest.mark.parametrize(
    "field",
    (
        "language_space_atlas",
        "semantic_unit",
        "decoded_strings_used_for_selection",
        "semantic_annotation_used",
        "sae_annotation_used",
        "projection_used",
    ),
)
def test_load_rejects_relaxed_interpretation_contract(
    tmp_path,
    field,
) -> None:
    binding = _context_binding(tmp_path)
    output_dir = tmp_path / field
    run_id_sweep(
        _bound_adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=binding.materialized_context_ids,
            position=binding.context.observation_position,
            subset=(3,),
            context_bank_binding=binding,
        ),
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    request = manifest["request"]
    request["context_bank_binding"]["interpretation_contract"][field] = True
    _refresh_bound_request_digests(request)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(AtlasIntegrityError, match="interpretation flags"):
        load_manifest(output_dir)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("bank_content", "bank canonical digest"),
        ("tokenizer", "tokenizer provenance digest"),
        ("selected_spec", "ContextSpec digest"),
        ("token_domain", "model or token domain"),
    ),
)
def test_load_recomputes_bound_content_digests(
    tmp_path,
    mutation,
    message,
) -> None:
    binding = _context_binding(tmp_path)
    output_dir = tmp_path / mutation
    run_id_sweep(
        _bound_adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=binding.materialized_context_ids,
            position=binding.context.observation_position,
            subset=(3,),
            context_bank_binding=binding,
        ),
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    request = manifest["request"]
    persisted_binding = request["context_bank_binding"]
    bank = persisted_binding["bank"]
    if mutation == "bank_content":
        bank["content"]["license"] = "CC0-1.0"
    elif mutation == "tokenizer":
        bank["content"]["tokenizer"]["files"]["tokenizer.json"] = "7" * 64
        bank["canonical_sha256"] = _canonical_sha256(bank["content"])
    elif mutation == "selected_spec":
        persisted_binding["selected_context"]["context_spec_sha256"] = "7" * 64
    else:
        request["token_domain"]["size"] = 10
    _refresh_bound_request_digests(request)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(AtlasIntegrityError, match=message):
        load_manifest(output_dir)


def test_sweep_position_defaults_to_observation_position_without_breaking_positionals(
    tmp_path,
) -> None:
    config = SweepConfig(tmp_path / "atlas", (0, 1), 1, 8)

    assert config.position == 1
    assert config.batch_size == 8
    assert config.sweep_position is None
    assert config.effective_sweep_position == 1

    manifest = run_id_sweep(
        _adapter(),
        SweepConfig(
            output_dir=tmp_path / "default-atlas",
            context_ids=(0, 1),
            position=1,
            subset=(2,),
        ),
    )
    assert manifest["request"]["position"] == 1
    assert "observation_position" not in manifest["request"]
    assert "sweep_position" not in manifest["request"]


@pytest.mark.parametrize(
    ("field", "value", "error", "message"),
    (
        ("position", True, TypeError, "position must be an integer"),
        ("position", 2, ValueError, r"position must be in \[0, 1\]"),
        ("sweep_position", True, TypeError, "sweep_position must be an integer"),
        (
            "sweep_position",
            2,
            ValueError,
            r"sweep_position must be in \[0, 1\]",
        ),
    ),
)
def test_sweep_and_observation_positions_are_validated_independently(
    tmp_path,
    field,
    value,
    error,
    message,
) -> None:
    kwargs = {
        "output_dir": tmp_path / "atlas",
        "context_ids": (0, 1),
        "position": 0,
        "sweep_position": 1,
    }
    kwargs[field] = value

    with pytest.raises(error, match=message):
        SweepConfig(**kwargs)


@pytest.mark.parametrize(
    ("attention_mask", "message"),
    (
        ((1, 1, 0), "observation position must be attended"),
        ((0, 1, 1), "sweep position must be attended"),
    ),
)
def test_sweep_and_observation_positions_must_be_attended(
    tmp_path,
    attention_mask,
    message,
) -> None:
    with pytest.raises(ValueError, match=message):
        SweepConfig(
            output_dir=tmp_path / "atlas",
            context_ids=(0, 1, 2),
            position=2,
            sweep_position=0,
            attention_mask=attention_mask,
        )


def test_distinct_sweep_and_observation_positions_are_applied_and_persisted(
    tmp_path,
) -> None:
    output_dir = tmp_path / "split-position-atlas"
    model = FakePythiaForCausalLM()
    seen_input_ids: list[torch.Tensor] = []

    def capture_input_ids(_module, _args, kwargs) -> None:
        seen_input_ids.append(kwargs["input_ids"].detach().cpu().clone())

    handle = model.register_forward_pre_hook(capture_input_ids, with_kwargs=True)
    try:
        manifest = run_id_sweep(
            _adapter(model),
            SweepConfig(
                output_dir=output_dir,
                context_ids=(1, 2, 3),
                position=2,
                sweep_position=0,
                subset=(4, 7),
                batch_size=2,
            ),
        )
    finally:
        handle.remove()

    assert len(seen_input_ids) == 1
    torch.testing.assert_close(
        seen_input_ids[0],
        torch.tensor(((4, 2, 3), (7, 2, 3)), dtype=torch.long),
    )
    assert manifest["request"]["position"] == 2
    assert manifest["request"]["observation_position"] == 2
    assert manifest["request"]["sweep_position"] == 0

    resid_pre = np.load(output_dir / "resid_pre.npy", mmap_mode="r")
    np.testing.assert_array_equal(resid_pre[0], resid_pre[1])


def test_sweep_writes_row_aligned_memmaps_and_complete_manifest(tmp_path) -> None:
    output_dir = tmp_path / "atlas"
    manifest = run_id_sweep(
        _adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=(0, 1, 2),
            position=1,
            subset=(4, 2, 5),
            max_tokens=2,
            batch_size=2,
        ),
    )

    assert manifest["status"] == "complete"
    assert manifest["progress"] == {
        "completed_rows": 2,
        "total_rows": 2,
        "committed_batches": 1,
    }
    assert manifest["model"]["rope"]["kind"] == "partial_rope"
    assert manifest["request"]["selection"]["kind"] == "subset"
    assert manifest["schema_version"] == "spirallens.activation_atlas.v2"
    assert manifest["schema_version"] == ATLAS_SCHEMA_VERSION
    assert manifest["capture"]["atlas_schema_version"] == ATLAS_SCHEMA_VERSION
    assert manifest["capture"]["spirallens_version"]
    assert manifest["capture"]["torch_version"]
    assert manifest["capture"]["transformers_version"]
    assert manifest["capture"]["effective_parameter_layout"][0] == {
        "device": "cpu",
        "dtype": "float32",
        "parameter_tensors": 2,
        "parameter_values": 132,
    }
    assert manifest["attempts"][0]["capture"] == manifest["capture"]
    assert (
        manifest["attempts"][0]["capture_fingerprint"]
        == manifest["capture_fingerprint"]
        == manifest["request"]["capture_fingerprint"]
    )
    assert len(manifest["batch_commits"]) == 1
    assert manifest["batch_commits"][0]["start_row"] == 0
    assert manifest["batch_commits"][0]["end_row"] == 2
    assert set(manifest["batch_commits"][0]["array_sha256"]) == set(
        manifest["arrays"]
    )
    np.testing.assert_array_equal(
        np.load(output_dir / "token_ids.npy", mmap_mode="r"), (4, 2)
    )
    assert np.load(output_dir / "resid_pre.npy", mmap_mode="r").shape == (2, 2, 6)
    assert np.load(output_dir / "resid_post.npy", mmap_mode="r").shape == (2, 2, 6)
    assert np.load(output_dir / "norm_summary.npy", mmap_mode="r").shape == (2, 2, 2)
    assert np.load(output_dir / "logit_summary.npy", mmap_mode="r").shape == (2, 6)
    assert np.load(output_dir / "prediction_ids.npy", mmap_mode="r").shape == (2,)
    assert manifest["arrays"]["logit_summary"]["columns"] == [
        "max_logit",
        "mean_logit",
        "std_logit",
        "logsumexp_logit",
        "entropy_nats",
        "input_token_logit",
    ]
    assert all(spec["sha256"] for spec in manifest["arrays"].values())
    assert load_manifest(output_dir) == manifest


def test_failed_batch_resumes_from_last_committed_row(tmp_path) -> None:
    output_dir = tmp_path / "resumable"
    model = FakePythiaForCausalLM()
    model.fail_on_token = 3
    adapter = _adapter(model)
    initial = SweepConfig(
        output_dir=output_dir,
        context_ids=(0,),
        position=0,
        subset=(0, 1, 2, 3, 4),
        batch_size=2,
    )

    with pytest.raises(RuntimeError, match="intentional failure"):
        run_id_sweep(adapter, initial)
    failed = json.loads((output_dir / "manifest.json").read_text())
    assert failed["status"] == "failed"
    assert failed["progress"]["completed_rows"] == 2
    first_committed_rows = np.load(
        output_dir / "resid_post.npy", mmap_mode="r"
    )[:2].copy()

    model.fail_on_token = None
    completed = run_id_sweep(
        adapter,
        SweepConfig(
            output_dir=output_dir,
            context_ids=(0,),
            position=0,
            subset=(0, 1, 2, 3, 4),
            batch_size=1,
            resume=True,
        ),
    )

    assert completed["status"] == "complete"
    assert completed["progress"]["completed_rows"] == 5
    assert completed["request"]["batch_size_initial"] == 2
    assert completed["request"]["batch_size_latest"] == 1
    assert completed["attempts"][-1]["resume_from_row"] == 2
    np.testing.assert_array_equal(
        np.load(output_dir / "resid_post.npy", mmap_mode="r")[:2],
        first_committed_rows,
    )


def test_resume_fails_closed_on_request_mismatch(tmp_path) -> None:
    output_dir = tmp_path / "atlas"
    run_id_sweep(
        _adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=(0,),
            position=0,
            max_tokens=2,
        ),
    )

    with pytest.raises(AtlasStateError, match="fingerprint"):
        run_id_sweep(
            _adapter(),
            SweepConfig(
                output_dir=output_dir,
                context_ids=(1,),
                position=0,
                max_tokens=2,
                resume=True,
            ),
        )


def test_resume_fails_when_effective_parameter_dtype_changes(tmp_path) -> None:
    output_dir = tmp_path / "dtype-mismatch"
    model = FakePythiaForCausalLM()
    model.fail_on_token = 3
    adapter = _adapter(model)
    config = SweepConfig(
        output_dir=output_dir,
        context_ids=(0,),
        position=0,
        subset=(0, 1, 2, 3),
        batch_size=2,
    )
    with pytest.raises(RuntimeError, match="intentional failure"):
        run_id_sweep(adapter, config)

    model.fail_on_token = None
    model.double()
    with pytest.raises(AtlasStateError, match="fingerprint"):
        run_id_sweep(
            adapter,
            SweepConfig(
                output_dir=output_dir,
                context_ids=(0,),
                position=0,
                subset=(0, 1, 2, 3),
                batch_size=2,
                resume=True,
            ),
        )
    unchanged = json.loads((output_dir / "manifest.json").read_text())
    assert unchanged["status"] == "failed"
    assert len(unchanged["attempts"]) == 1


def test_resume_rejects_tampered_attempt_capture_provenance(tmp_path) -> None:
    output_dir = tmp_path / "attempt-provenance"
    model = FakePythiaForCausalLM()
    model.fail_on_token = 3
    adapter = _adapter(model)
    config = SweepConfig(
        output_dir=output_dir,
        context_ids=(0,),
        position=0,
        subset=(0, 1, 2, 3),
        batch_size=2,
    )
    with pytest.raises(RuntimeError, match="intentional failure"):
        run_id_sweep(adapter, config)

    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["attempts"][0]["capture"]["torch_version"] = "tampered"
    manifest_path.write_text(json.dumps(manifest))
    model.fail_on_token = None

    with pytest.raises(AtlasIntegrityError, match="attempt 0 capture"):
        run_id_sweep(
            adapter,
            SweepConfig(
                output_dir=output_dir,
                context_ids=(0,),
                position=0,
                subset=(0, 1, 2, 3),
                batch_size=2,
                resume=True,
            ),
        )


def test_resume_rejects_mutated_committed_batch_row(tmp_path) -> None:
    output_dir = tmp_path / "committed-corruption"
    model = FakePythiaForCausalLM()
    model.fail_on_token = 3
    adapter = _adapter(model)
    config = SweepConfig(
        output_dir=output_dir,
        context_ids=(0,),
        position=0,
        subset=(0, 1, 2, 3),
        batch_size=2,
    )
    with pytest.raises(RuntimeError, match="intentional failure"):
        run_id_sweep(adapter, config)
    before = json.loads((output_dir / "manifest.json").read_text())
    assert before["progress"]["completed_rows"] == 2
    assert len(before["batch_commits"]) == 1

    resid_pre = np.load(output_dir / "resid_pre.npy", mmap_mode="r+")
    resid_pre[0, 0, 0] += 1.0
    resid_pre.flush()
    del resid_pre
    model.fail_on_token = None

    with pytest.raises(AtlasIntegrityError, match="batch commit digest mismatch"):
        run_id_sweep(
            adapter,
            SweepConfig(
                output_dir=output_dir,
                context_ids=(0,),
                position=0,
                subset=(0, 1, 2, 3),
                batch_size=2,
                resume=True,
            ),
        )
    unchanged = json.loads((output_dir / "manifest.json").read_text())
    assert unchanged["status"] == "failed"
    assert unchanged["progress"]["completed_rows"] == 2
    assert len(unchanged["attempts"]) == 1


def test_v1_manifest_is_not_silently_resumed_or_read(tmp_path) -> None:
    output_dir = tmp_path / "old-schema"
    run_id_sweep(
        _adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=(0,),
            position=0,
            max_tokens=1,
        ),
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["schema_version"] = "spirallens.activation_atlas.v1"
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(AtlasIntegrityError, match="unsupported atlas schema"):
        load_manifest(output_dir)
    with pytest.raises(AtlasIntegrityError, match="unsupported atlas schema"):
        run_id_sweep(
            _adapter(),
            SweepConfig(
                output_dir=output_dir,
                context_ids=(0,),
                position=0,
                max_tokens=1,
                resume=True,
            ),
        )


def test_checksum_corruption_is_detected(tmp_path) -> None:
    output_dir = tmp_path / "atlas"
    run_id_sweep(
        _adapter(),
        SweepConfig(
            output_dir=output_dir,
            context_ids=(0,),
            position=0,
            max_tokens=2,
        ),
    )
    values = np.load(output_dir / "resid_pre.npy", mmap_mode="r+")
    values[0, 0, 0] += 1.0
    values.flush()
    del values

    with pytest.raises(AtlasIntegrityError, match="checksum mismatch"):
        load_manifest(output_dir)


def test_nonempty_unclaimed_directory_is_never_overwritten(tmp_path) -> None:
    output_dir = tmp_path / "unclaimed"
    output_dir.mkdir()
    (output_dir / "notes.txt").write_text("belongs to someone else")

    with pytest.raises(AtlasStateError, match="non-empty"):
        run_id_sweep(
            _adapter(),
            SweepConfig(
                output_dir=output_dir,
                context_ids=(0,),
                position=0,
                max_tokens=1,
            ),
        )
