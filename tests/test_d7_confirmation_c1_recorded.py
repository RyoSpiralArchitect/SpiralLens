from __future__ import annotations

from pathlib import Path

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_c1 as confirmation_c1_module
from spirallens.qualification.confirmation_c1 import (
    D7_C1_BUNDLE_REPOSITORY_PATH,
    D7_C2_RECEIPT_REPOSITORY_PATH,
    MAX_D7_C1_SEED_FREE_SOURCE_SET_BYTES,
    D7C1SeedFreeSourceSet,
)

REPOSITORY = Path(__file__).resolve().parents[1]
EXPECTED_RECORDED_C1_SHA256 = (
    "b7b3b416738c9d02ed76764e35bb131f6bcc6df2948bff200b51df83aee33a5d"
)
EXPECTED_RECORDED_C1_BYTE_COUNT = 539_310


def test_recorded_c1_is_canonical_current_source_bound_and_documented() -> None:
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
        document["components"]["source_set_manifest"]["body"]
        == confirmation_c1_module._source_set_document(REPOSITORY)
    )

    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    assert f"`{EXPECTED_RECORDED_C1_SHA256}`" in readme
    assert not (REPOSITORY / D7_C2_RECEIPT_REPOSITORY_PATH).exists()
