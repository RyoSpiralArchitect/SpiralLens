from __future__ import annotations

import json

import numpy as np
import pytest
import torch

from spirallens.adapters import PythiaAdapter
from spirallens.atlas import (
    ATLAS_SCHEMA_VERSION,
    AtlasIntegrityError,
    AtlasStateError,
    SweepConfig,
    load_manifest,
    run_id_sweep,
    select_token_ids,
)

from fake_pythia import FakePythiaForCausalLM


def _adapter(model: FakePythiaForCausalLM | None = None) -> PythiaAdapter:
    return PythiaAdapter(
        model or FakePythiaForCausalLM(),
        model_id="offline/fake-pythia",
        revision="fixed-test-weights",
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
    assert manifest["request"]["observation_position"] == 1
    assert manifest["request"]["sweep_position"] == 1


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
