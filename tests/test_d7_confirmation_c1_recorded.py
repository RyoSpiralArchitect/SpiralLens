from __future__ import annotations

from pathlib import Path

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification.confirmation_c1 import (
    D7_C1_BUNDLE_REPOSITORY_PATH,
    D7_C2_RECEIPT_REPOSITORY_PATH,
    MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES,
    D7C1SeedFreeSourceSet,
)
from spirallens.qualification.confirmation_source_closure import (
    load_committed_d7_source_closure,
)

REPOSITORY = Path(__file__).resolve().parents[1]
EXPECTED_RECORDED_C1_SHA256 = (
    "b7b3b416738c9d02ed76764e35bb131f6bcc6df2948bff200b51df83aee33a5d"
)
EXPECTED_RECORDED_C1_BYTE_COUNT = 539_310
EXPECTED_RECORDED_C2_SHA256 = (
    "d28a87bce5ec80c3388df1e21bccbc052f34beb637ff86f81f4f502d9fdd71a3"
)
EXPECTED_RECORDED_C1_COMMIT = "e58a8169b41be688628ab7dda583e68088d3affc"
EXPECTED_RECORDED_C2_COMMIT = "2f4e715a951211af8ca0ca4f6b2f7473134bf92b"


def test_recorded_c1_and_committed_c2_are_canonical_and_documented() -> None:
    artifact = REPOSITORY / D7_C1_BUNDLE_REPOSITORY_PATH
    assert artifact.is_file()
    assert not artifact.is_symlink()
    source = artifact.read_bytes()

    assert 0 < len(source) <= MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES
    assert len(source) == EXPECTED_RECORDED_C1_BYTE_COUNT
    assert sha256_bytes(source) == EXPECTED_RECORDED_C1_SHA256
    loaded = D7C1SeedFreeSourceSet.from_canonical_bytes(
        source,
        expected_sha256=EXPECTED_RECORDED_C1_SHA256,
    )
    document = loaded.to_dict()
    assert canonical_json_bytes(document) == source
    assert document["claim_ceiling"] == "level_0"
    assert document["d7_state"] == "not_run"
    assert document["d8_state"] == "not_run"
    assert all(value is False for value in document["authority"].values())
    assert (
        document["components"]["source_set_manifest"]["body"][
            "source_closure_verified"
        ]
        is False
    )
    assert (
        document["chronology"]["artifact_knowledge"][
            "source_closure_attestation_embedded"
        ]
        is False
    )
    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    assert f"`{EXPECTED_RECORDED_C1_SHA256}`" in readme
    assert f"`{EXPECTED_RECORDED_C2_SHA256}`" in readme

    receipt_path = REPOSITORY / D7_C2_RECEIPT_REPOSITORY_PATH
    assert receipt_path.is_file()
    assert not receipt_path.is_symlink()
    receipt_source = receipt_path.read_bytes()
    assert sha256_bytes(receipt_source) == EXPECTED_RECORDED_C2_SHA256
    committed = load_committed_d7_source_closure(
        repository_root=REPOSITORY,
        expected_source_sha256=EXPECTED_RECORDED_C2_SHA256,
        expected_canonical_sha256=EXPECTED_RECORDED_C2_SHA256,
    )
    assert committed.c1_commit == EXPECTED_RECORDED_C1_COMMIT
    assert committed.c2_commit == EXPECTED_RECORDED_C2_COMMIT
    assert committed.committed_receipt_verified is True
    assert committed.historical_c1_source_closure_verified is True
    assert committed.current_source_compatibility_verified is False

    receipt = committed.receipt.to_dict()
    assert canonical_json_bytes(receipt) == receipt_source
    assert receipt["status"] == "c1-source-closure-verified"
    assert receipt["claim_ceiling"] == "level_0"
    assert receipt["d7_state"] == "not_run"
    assert receipt["d8_state"] == "not_run"
    assert all(value is False for value in receipt["authority"].values())
    assert receipt["limitations"] == {
        "source_only": True,
        "historical_code_executed": False,
        "python_runtime_attested": False,
        "native_runtime_attested": False,
        "in_process_callable_identity_verified": False,
        "hostile_local_mutation_resistant": False,
        "current_source_compatibility_verified": False,
    }
