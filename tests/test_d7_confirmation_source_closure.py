from __future__ import annotations

import inspect
import shutil
import subprocess
from pathlib import Path

import pytest
from test_d7_confirmation_c1 import (
    REPOSITORY,
    _bundle,
    _c1_inputs,
    _patch_c1_parent_pins,
)

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import (
    confirmation_source_closure as source_closure_module,
)
from spirallens.qualification.common import QualificationContractError
from spirallens.qualification.confirmation_c1 import (
    D7_C1_BUNDLE_REPOSITORY_PATH,
    D7_C2_RECEIPT_REPOSITORY_PATH,
)
from spirallens.qualification.confirmation_source_closure import (
    D7C2SourceClosureReceipt,
    issue_d7_c2_source_closure_receipt,
    load_committed_d7_source_closure,
)


@pytest.fixture(autouse=True)
def _pin_c1_test_lineage(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded_d6, parent = _c1_inputs()
    _patch_c1_parent_pins(monkeypatch, loaded_d6, parent)


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _c1_repository(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repository"
    (root / "src").mkdir(parents=True)
    shutil.copytree(
        REPOSITORY / "src" / "spirallens",
        root / "src" / "spirallens",
    )
    shutil.copy2(REPOSITORY / "pyproject.toml", root / "pyproject.toml")
    bundle_path = root / D7_C1_BUNDLE_REPOSITORY_PATH
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_bytes(_bundle().canonical_bytes)
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "SpiralLens Test")
    _git(root, "config", "user.email", "spirallens@example.invalid")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "C1")
    return root, _git(root, "rev-parse", "HEAD")


def _commit_c2(
    root: Path,
) -> tuple[object, str]:
    published = issue_d7_c2_source_closure_receipt(repository_root=root)
    _git(root, "add", D7_C2_RECEIPT_REPOSITORY_PATH)
    _git(root, "commit", "-q", "-m", "C2")
    return published, _git(root, "rev-parse", "HEAD")


def test_c2_issuer_and_committed_loader_prove_receipt_only_history(
    tmp_path: Path,
) -> None:
    root, c1_commit = _c1_repository(tmp_path)
    published = issue_d7_c2_source_closure_receipt(repository_root=root)

    assert published.receipt.to_dict()["c1_commit"] == c1_commit
    assert published.receipt.to_dict()["chronology"][
        "artifact_knowledge"
    ][
        "c2_commit_identity_embedded"
    ] is False
    assert published.committed_receipt_verified is False
    assert _git(root, "status", "--short") == (
        f"?? {D7_C2_RECEIPT_REPOSITORY_PATH}"
    )
    _git(root, "add", D7_C2_RECEIPT_REPOSITORY_PATH)
    _git(root, "commit", "-q", "-m", "C2")
    c2_commit = _git(root, "rev-parse", "HEAD")

    loaded = load_committed_d7_source_closure(
        repository_root=root,
        expected_source_sha256=published.receipt.canonical_sha256,
        expected_canonical_sha256=published.receipt.canonical_sha256,
    )

    assert loaded.c1_commit == c1_commit
    assert loaded.c2_commit == c2_commit
    assert loaded.current_head == c2_commit
    assert loaded.committed_receipt_verified is True
    assert loaded.historical_c1_source_closure_verified is True
    assert loaded.current_source_compatibility_verified is False


def test_c2_issuer_rejects_dirty_or_incomplete_c1(tmp_path: Path) -> None:
    dirty_root, _commit = _c1_repository(tmp_path / "dirty")
    (dirty_root / "dirty.txt").write_text("untracked", encoding="utf-8")
    with pytest.raises(QualificationContractError, match="completely clean"):
        issue_d7_c2_source_closure_receipt(repository_root=dirty_root)

    incomplete_root, _commit = _c1_repository(tmp_path / "incomplete")
    omitted = incomplete_root / "src" / "spirallens" / "qualification" / "blind.py"
    omitted.unlink()
    _git(incomplete_root, "add", "-u")
    _git(incomplete_root, "commit", "-q", "-m", "replace C1 with omission")
    with pytest.raises(
        QualificationContractError,
        match="differs from Git-tree re-enumeration",
    ):
        issue_d7_c2_source_closure_receipt(repository_root=incomplete_root)


def test_c2_issuer_bounds_git_source_metadata_before_blob_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _commit = _c1_repository(tmp_path)
    monkeypatch.setattr(
        source_closure_module,
        "MAX_D7_SOURCE_CLOSURE_GIT_METADATA_BYTES",
        1,
    )
    with pytest.raises(QualificationContractError, match="exceeds its byte cap"):
        issue_d7_c2_source_closure_receipt(repository_root=root)
    assert not (root / D7_C2_RECEIPT_REPOSITORY_PATH).exists()


def test_committed_loader_rejects_a_c2_with_any_extra_delta(
    tmp_path: Path,
) -> None:
    root, _c1_commit = _c1_repository(tmp_path)
    published = issue_d7_c2_source_closure_receipt(repository_root=root)
    (root / "extra.txt").write_text("not receipt-only", encoding="utf-8")
    _git(root, "add", D7_C2_RECEIPT_REPOSITORY_PATH, "extra.txt")
    _git(root, "commit", "-q", "-m", "invalid C2")

    with pytest.raises(
        QualificationContractError,
        match="anything besides the one added receipt",
    ):
        load_committed_d7_source_closure(
            repository_root=root,
            expected_source_sha256=published.receipt.canonical_sha256,
            expected_canonical_sha256=published.receipt.canonical_sha256,
        )


def test_committed_loader_rejects_receipt_drift_after_c2(tmp_path: Path) -> None:
    root, _c1_commit = _c1_repository(tmp_path)
    published = issue_d7_c2_source_closure_receipt(repository_root=root)
    _git(root, "add", D7_C2_RECEIPT_REPOSITORY_PATH)
    _git(root, "commit", "-q", "-m", "C2")
    receipt_path = root / D7_C2_RECEIPT_REPOSITORY_PATH
    receipt_path.write_bytes(receipt_path.read_bytes() + b"\n")
    _git(root, "add", D7_C2_RECEIPT_REPOSITORY_PATH)
    _git(root, "commit", "-q", "-m", "mutate receipt")

    with pytest.raises(QualificationContractError, match="SHA-256 differs"):
        load_committed_d7_source_closure(
            repository_root=root,
            expected_source_sha256=published.receipt.canonical_sha256,
            expected_canonical_sha256=published.receipt.canonical_sha256,
        )


def test_committed_loader_rejects_receipt_deletion_and_exact_restoration(
    tmp_path: Path,
) -> None:
    root, _c1_commit = _c1_repository(tmp_path)
    published = issue_d7_c2_source_closure_receipt(repository_root=root)
    receipt_path = root / D7_C2_RECEIPT_REPOSITORY_PATH
    original = receipt_path.read_bytes()
    _git(root, "add", D7_C2_RECEIPT_REPOSITORY_PATH)
    _git(root, "commit", "-q", "-m", "C2")
    receipt_path.unlink()
    _git(root, "add", "-u", D7_C2_RECEIPT_REPOSITORY_PATH)
    _git(root, "commit", "-q", "-m", "delete receipt")
    receipt_path.write_bytes(original)
    _git(root, "add", D7_C2_RECEIPT_REPOSITORY_PATH)
    _git(root, "commit", "-q", "-m", "restore receipt")

    with pytest.raises(
        QualificationContractError,
        match="deleted, replaced, or changed",
    ):
        load_committed_d7_source_closure(
            repository_root=root,
            expected_source_sha256=published.receipt.canonical_sha256,
            expected_canonical_sha256=published.receipt.canonical_sha256,
        )


def test_c2_receipt_rejects_nested_field_laundering(tmp_path: Path) -> None:
    root, _c1_commit = _c1_repository(tmp_path)
    published = issue_d7_c2_source_closure_receipt(repository_root=root)
    for nested_name in ("c1_bundle", "source_inventory"):
        document = published.receipt.to_dict()
        nested = document[nested_name]
        assert isinstance(nested, dict)
        nested["unreviewed_extension"] = False
        source = canonical_json_bytes(document)
        with pytest.raises(
            QualificationContractError,
            match="fields differ",
        ):
            D7C2SourceClosureReceipt.from_canonical_bytes(
                source,
                expected_sha256=sha256_bytes(source),
            )


def test_c2_receipt_rejects_boolean_integer_laundering(
    tmp_path: Path,
) -> None:
    root, _c1_commit = _c1_repository(tmp_path)
    published = issue_d7_c2_source_closure_receipt(repository_root=root)
    mutations = (
        (("verification", "c1_head_derived_not_supplied"), 1),
        (
            (
                "chronology",
                "artifact_knowledge",
                "c1_commit_contains_receipt",
            ),
            0,
        ),
        (("authority", "scientific_claim_eligible"), 0),
        (
            (
                "source_inventory",
                "enumeration_rule",
                "future_c2_git_tree_reenumeration_required",
            ),
            1,
        ),
    )
    for path, replacement in mutations:
        document = published.receipt.to_dict()
        cursor = document
        for key in path[:-1]:
            nested = cursor[key]
            assert isinstance(nested, dict)
            cursor = nested
        cursor[path[-1]] = replacement
        source = canonical_json_bytes(document)
        with pytest.raises(QualificationContractError, match="differs"):
            D7C2SourceClosureReceipt.from_canonical_bytes(
                source,
                expected_sha256=sha256_bytes(source),
            )


def test_loader_accepts_normal_merge_then_rejects_sibling_history(
    tmp_path: Path,
) -> None:
    root, c1_commit = _c1_repository(tmp_path)
    main_branch = _git(root, "branch", "--show-current")
    _git(root, "switch", "-q", "-c", "receipt-only")
    published, c2_commit = _commit_c2(root)
    _git(root, "switch", "-q", main_branch)
    _git(root, "merge", "-q", "--no-ff", "receipt-only", "-m", "merge C2")

    loaded = load_committed_d7_source_closure(
        repository_root=root,
        expected_source_sha256=published.receipt.canonical_sha256,
        expected_canonical_sha256=published.receipt.canonical_sha256,
    )
    assert loaded.c1_commit == c1_commit
    assert loaded.c2_commit == c2_commit

    _git(root, "switch", "-q", "-c", "post-c1-sibling", c1_commit)
    sibling_path = root / "src" / "spirallens" / "post_c1_sibling.py"
    sibling_path.write_text("SIBLING = True\n", encoding="utf-8")
    _git(root, "add", str(sibling_path.relative_to(root)))
    _git(root, "commit", "-q", "-m", "post-C1 sibling")
    _git(root, "switch", "-q", main_branch)
    _git(
        root,
        "merge",
        "-q",
        "--no-ff",
        "post-c1-sibling",
        "-m",
        "merge non-dominated sibling",
    )

    with pytest.raises(
        QualificationContractError,
        match="not dominated",
    ):
        load_committed_d7_source_closure(
            repository_root=root,
            expected_source_sha256=published.receipt.canonical_sha256,
            expected_canonical_sha256=published.receipt.canonical_sha256,
        )


@pytest.mark.parametrize(
    "repository_path, expected_message",
    (
        (D7_C2_RECEIPT_REPOSITORY_PATH, "C2 receipt"),
        (D7_C1_BUNDLE_REPOSITORY_PATH, "C1 bundle"),
    ),
)
def test_loader_rejects_mode_drift_even_after_exact_restoration(
    tmp_path: Path,
    repository_path: str,
    expected_message: str,
) -> None:
    root, _c1_commit = _c1_repository(tmp_path)
    published, _c2_commit = _commit_c2(root)
    _git(root, "update-index", "--chmod=+x", repository_path)
    _git(root, "commit", "-q", "-m", "change tracked mode")
    _git(root, "update-index", "--chmod=-x", repository_path)
    _git(root, "commit", "-q", "-m", "restore tracked mode")

    with pytest.raises(
        QualificationContractError,
        match=expected_message,
    ):
        load_committed_d7_source_closure(
            repository_root=root,
            expected_source_sha256=published.receipt.canonical_sha256,
            expected_canonical_sha256=published.receipt.canonical_sha256,
        )


def test_loader_rejects_executable_receipt_at_c2(tmp_path: Path) -> None:
    root, _c1_commit = _c1_repository(tmp_path)
    published = issue_d7_c2_source_closure_receipt(repository_root=root)
    _git(root, "add", D7_C2_RECEIPT_REPOSITORY_PATH)
    _git(
        root,
        "update-index",
        "--chmod=+x",
        D7_C2_RECEIPT_REPOSITORY_PATH,
    )
    (root / D7_C2_RECEIPT_REPOSITORY_PATH).chmod(0o755)
    _git(root, "commit", "-q", "-m", "executable C2")

    with pytest.raises(
        QualificationContractError,
        match="receipt blob changed",
    ):
        load_committed_d7_source_closure(
            repository_root=root,
            expected_source_sha256=published.receipt.canonical_sha256,
            expected_canonical_sha256=published.receipt.canonical_sha256,
        )


def test_c2_issuer_is_choice_free_and_receipt_path_is_fixed() -> None:
    assert set(
        inspect.signature(issue_d7_c2_source_closure_receipt).parameters
    ) == {"repository_root"}
    assert "c1_commit" not in (
        inspect.signature(issue_d7_c2_source_closure_receipt).parameters
    )
    assert D7_C2_RECEIPT_REPOSITORY_PATH.endswith(
        "c2-source-closure-receipt.json"
    )
