from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
import inspect

import pytest

import spirallens.atlas as atlas
from spirallens.atlas import engineering_protocol as profiles


def test_only_exact_pythia70_public_example_profile_is_registered() -> None:
    profile = profiles._require_engineering_model_profile(
        "EleutherAI/pythia-70m"
    )

    assert set(profiles._ENGINEERING_MODEL_PROFILES_BY_ID) == {
        "EleutherAI/pythia-70m"
    }
    assert profile is profiles._PYTHIA70_ENGINEERING_MODEL_PROFILE
    assert profile.model_id == "EleutherAI/pythia-70m"
    assert profile.display_name == "Pythia-70M"
    assert profile.architecture == "GPTNeoXForCausalLM"
    assert profile.dimensions == {
        "num_layers": 6,
        "hidden_size": 512,
        "vocab_size": 50304,
        "num_attention_heads": 8,
        "intermediate_size": 2048,
        "max_position_embeddings": 2048,
    }
    assert profile.model_file_names == (
        "config.json",
        "model.safetensors",
    )
    assert profile.parameter_count == 70_426_624
    assert profile.effective_parameter_layout == [
        {
            "device": "cpu",
            "dtype": "float32",
            "parameter_tensors": 76,
            "parameter_values": 70_426_624,
        }
    ]


@pytest.mark.parametrize(
    "model_id",
    [
        "EleutherAI/pythia-160m",
        "EleutherAI/pythia-70m ",
        "",
        None,
    ],
)
def test_unregistered_or_noncanonical_model_ids_fail_closed(model_id) -> None:
    with pytest.raises(profiles._UnsupportedEngineeringModelProfileError):
        profiles._require_engineering_model_profile(model_id)


def test_profile_and_registry_are_immutable_and_private() -> None:
    profile = profiles._PYTHIA70_ENGINEERING_MODEL_PROFILE
    with pytest.raises(FrozenInstanceError):
        profile.hidden_size = 768  # type: ignore[misc]
    with pytest.raises(TypeError):
        profiles._ENGINEERING_MODEL_PROFILES_BY_ID[
            "EleutherAI/pythia-160m"
        ] = profile  # type: ignore[index]

    assert "_EngineeringModelProfile" not in atlas.__all__
    assert "_require_engineering_model_profile" not in atlas.__all__


def test_private_profile_seam_has_no_model_or_io_capability() -> None:
    source = "\n".join(
        (
            inspect.getsource(profiles._EngineeringModelProfile),
            inspect.getsource(profiles._require_engineering_model_profile),
        )
    )
    tree = ast.parse(source)
    forbidden_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"open", "exec", "eval", "__import__"}
    }
    assert forbidden_calls == set()
    assert not any(
        isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
                ast.With,
                ast.AsyncWith,
                ast.Await,
            ),
        )
        for node in ast.walk(tree)
    )
