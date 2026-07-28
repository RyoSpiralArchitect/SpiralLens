from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from access_fixtures import preparation_descriptor
from spirallens.access import (
    AtlasAccessContractError,
    AtlasConsumer,
    AtlasConsumerDenied,
    AtlasPreparationView,
    MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES,
    load_atlas_preparation_descriptor,
    prepare_descriptor_only_view,
    write_atlas_preparation_descriptor,
)
from spirallens.access import descriptor as descriptor_module


def _write_descriptor(path: Path, descriptor) -> None:
    path.write_bytes(descriptor.canonical_bytes)


def _load(path: Path, descriptor):
    return load_atlas_preparation_descriptor(
        path,
        expected_source_sha256=hashlib.sha256(descriptor.canonical_bytes).hexdigest(),
        expected_canonical_sha256=descriptor.canonical_sha256,
    )


def test_descriptor_writer_is_exclusive_and_loader_is_strict(
    tmp_path: Path,
) -> None:
    descriptor = preparation_descriptor()
    path = tmp_path / "atlas-access.json"

    loaded = write_atlas_preparation_descriptor(path, descriptor)

    assert path.read_bytes() == descriptor.canonical_bytes
    assert loaded.descriptor == descriptor
    assert loaded.source_sha256 == descriptor.canonical_sha256
    assert loaded.read_trace == (path.resolve(),)
    with pytest.raises(
        AtlasAccessContractError,
        match="overwrite is forbidden",
    ):
        write_atlas_preparation_descriptor(path, descriptor)

    pretty = tmp_path / "pretty.json"
    pretty_source = json.dumps(
        descriptor.to_dict(),
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    pretty.write_bytes(pretty_source)
    with pytest.raises(
        AtlasAccessContractError,
        match="not canonical JSON",
    ):
        load_atlas_preparation_descriptor(
            pretty,
            expected_source_sha256=hashlib.sha256(pretty_source).hexdigest(),
            expected_canonical_sha256=descriptor.canonical_sha256,
        )


def test_descriptor_writer_rejects_oversize_before_creating_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor = preparation_descriptor()
    output = tmp_path / "oversized.json"
    monkeypatch.setattr(
        descriptor_module,
        "MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES",
        len(descriptor.canonical_bytes) - 1,
    )

    with pytest.raises(
        AtlasAccessContractError,
        match="exceeds the size limit",
    ):
        write_atlas_preparation_descriptor(output, descriptor)

    assert not output.exists()


def test_descriptor_loader_rejects_symlinks_hardlinks_and_oversize(
    tmp_path: Path,
) -> None:
    descriptor = preparation_descriptor()
    target = tmp_path / "target.json"
    _write_descriptor(target, descriptor)

    symlink = tmp_path / "symlink.json"
    symlink.symlink_to(target)
    with pytest.raises(
        AtlasAccessContractError,
        match="cannot safely read",
    ):
        _load(symlink, descriptor)

    hardlink = tmp_path / "hardlink.json"
    os.link(target, hardlink)
    with pytest.raises(
        AtlasAccessContractError,
        match="exactly one link",
    ):
        _load(target, descriptor)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * (MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES + 1))
    digest = hashlib.sha256(oversized.read_bytes()).hexdigest()
    with pytest.raises(
        AtlasAccessContractError,
        match="exceeds the size limit",
    ):
        load_atlas_preparation_descriptor(
            oversized,
            expected_source_sha256=digest,
            expected_canonical_sha256="0" * 64,
        )


def test_descriptor_loader_rejects_symlinked_parent(
    tmp_path: Path,
) -> None:
    descriptor = preparation_descriptor()
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    path = real_parent / "atlas-access.json"
    _write_descriptor(path, descriptor)
    alias = tmp_path / "alias"
    alias.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(
        AtlasAccessContractError,
        match="cannot safely open descriptor parent",
    ):
        _load(alias / path.name, descriptor)


def test_descriptor_only_prepare_is_payload_noninterfering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor = preparation_descriptor()
    roots = [tmp_path / "canary-a", tmp_path / "canary-b"]
    for index, root in enumerate(roots):
        root.mkdir()
        _write_descriptor(root / "atlas-access.json", descriptor)
        (root / "manifest.json").write_text(
            json.dumps(
                {
                    "run_id": f"secret-run-{index}",
                    "summaries": {
                        "norm": 0.25 if index == 0 else 99_999.0,
                        "prediction": index,
                    },
                    "array_sha256": str(index) * 64,
                    "completed_at": f"2099-01-0{index + 1}",
                }
            ),
            encoding="utf-8",
        )
        (root / "resid.npy").write_bytes(
            (b"first-secret-payload" if index == 0 else b"other-payload")
        )
        (root / "resid.npy").chmod(0)

    actual_open = descriptor_module.os.open
    opened_leaf_files: list[str] = []

    def traced_open(path, flags, *args, **kwargs):
        directory_flag = getattr(os, "O_DIRECTORY", 0)
        if not flags & directory_flag:
            opened_leaf_files.append(os.fspath(path))
        return actual_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(descriptor_module.os, "open", traced_open)

    loaded = [_load(root / "atlas-access.json", descriptor) for root in roots]
    views = [
        prepare_descriptor_only_view(
            item,
            consumer=AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION,
        )
        for item in loaded
    ]

    assert views[0].canonical_bytes == views[1].canonical_bytes
    assert views[0].to_dict()["subject_values_observed"] is False
    assert views[0].to_dict()["manifest_read"] is False
    assert views[0].to_dict()["payload_files_read"] is False
    assert views[0].to_dict()["subject_execution_authorized"] is False
    assert opened_leaf_files == ["atlas-access.json", "atlas-access.json"]
    assert loaded[0].read_trace == (roots[0] / "atlas-access.json",)
    assert loaded[1].read_trace == (roots[1] / "atlas-access.json",)
    assert (
        AtlasPreparationView.from_dict(views[0].to_dict()).canonical_bytes
        == views[0].canonical_bytes
    )

    promoted = views[0].to_dict()
    promoted["subject_execution_authorized"] = True
    with pytest.raises(
        AtlasAccessContractError,
        match="subject_execution_authorized",
    ):
        AtlasPreparationView.from_dict(promoted)

    unknown = views[0].to_dict()
    unknown["run_id"] = "forbidden-outcome"
    with pytest.raises(
        AtlasAccessContractError,
        match="unknown=.*run_id",
    ):
        AtlasPreparationView.from_dict(unknown)


def test_declared_descriptor_mutation_changes_prepare_view(
    tmp_path: Path,
) -> None:
    original = preparation_descriptor()
    mutated = replace(
        original,
        capture=replace(
            original.capture,
            output_id="subject-atlas-v0.2",
        ),
    )
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write_descriptor(first, original)
    _write_descriptor(second, mutated)

    first_view = prepare_descriptor_only_view(
        _load(first, original),
        consumer=AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION,
    )
    second_view = prepare_descriptor_only_view(
        _load(second, mutated),
        consumer=AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION,
    )

    assert original.canonical_sha256 != mutated.canonical_sha256
    assert first_view.canonical_bytes != second_view.canonical_bytes
    assert first_view.output_id == "subject-atlas-v0.1"
    assert second_view.output_id == "subject-atlas-v0.2"


def test_descriptor_only_prepare_has_process_level_deny_open_canary(
    tmp_path: Path,
) -> None:
    descriptor = preparation_descriptor()
    roots = (tmp_path / "audit-a", tmp_path / "audit-b")
    for index, root in enumerate(roots):
        root.mkdir()
        _write_descriptor(root / "atlas-access.json", descriptor)
        (root / "manifest.json").write_text(
            json.dumps({"outcome": index, "run_id": f"secret-{index}"}),
            encoding="utf-8",
        )
        (root / "payload.npy").write_bytes(
            b"first-secret" if index == 0 else b"second-secret"
        )

    source_root = Path(__file__).resolve().parents[1] / "src"
    probe = f"""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, {str(source_root)!r})
from spirallens.access import (
    AtlasConsumer,
    load_atlas_preparation_descriptor,
    prepare_descriptor_only_view,
)
opened = []
def audit(event, arguments):
    if event != "open":
        return
    path, _, flags = arguments
    if isinstance(flags, int) and flags & getattr(os, "O_DIRECTORY", 0):
        return
    leaf = Path(os.fspath(path)).name
    if leaf != "atlas-access.json":
        raise RuntimeError("forbidden non-descriptor read: " + leaf)
    opened.append(leaf)
sys.addaudithook(audit)
loaded = load_atlas_preparation_descriptor(
    sys.argv[1],
    expected_source_sha256=sys.argv[2],
    expected_canonical_sha256=sys.argv[3],
)
view = prepare_descriptor_only_view(
    loaded,
    consumer=AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION,
)
print(json.dumps({{"opened": opened, "view": view.to_dict()}}, sort_keys=True))
"""
    results = []
    for root in roots:
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                probe,
                str(root / "atlas-access.json"),
                descriptor.canonical_sha256,
                descriptor.canonical_sha256,
            ],
            cwd=tmp_path,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        results.append(json.loads(completed.stdout))

    assert results[0] == results[1]
    assert results[0]["opened"] == ["atlas-access.json"]


def test_descriptor_only_view_never_authorizes_subject_execution(
    tmp_path: Path,
) -> None:
    descriptor = preparation_descriptor(
        allowed_consumers=frozenset(
            {
                AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION,
                AtlasConsumer.SUBJECT_EXECUTION,
            }
        )
    )
    path = tmp_path / "atlas-access.json"
    _write_descriptor(path, descriptor)
    loaded = _load(path, descriptor)

    with pytest.raises(
        AtlasConsumerDenied,
        match="descriptor-only preparation cannot authorize",
    ):
        prepare_descriptor_only_view(
            loaded,
            consumer=AtlasConsumer.SUBJECT_EXECUTION,
        )


def test_descriptor_source_mutation_is_rejected_before_prepare(
    tmp_path: Path,
) -> None:
    descriptor = preparation_descriptor()
    path = tmp_path / "atlas-access.json"
    _write_descriptor(path, descriptor)
    expected_source = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = descriptor.to_dict()
    payload["descriptor_id"] = "mutated-after-freeze"
    path.write_bytes(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    with pytest.raises(
        AtlasAccessContractError,
        match="source SHA-256 mismatch",
    ):
        load_atlas_preparation_descriptor(
            path,
            expected_source_sha256=expected_source,
            expected_canonical_sha256=descriptor.canonical_sha256,
        )
