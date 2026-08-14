import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_lib_l0_status_view.py"
SPEC = importlib.util.spec_from_file_location("_lib_l0_view", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)
EXACT_OWNERS = "scripts/generate_lib_l0_status_view.py docs/FUNDAMENTAL_FRAME.md docs/EXPERIMENT_INTERPRETATION_LEDGER.md docs/ROADMAP.md scripts/validate_distribution.py distribution/spirallens_installed_imports_v0_1.json distribution/spirallens_ordered_exports_v0_1.json distribution/spirallens_python_members_v0_1.json".split()


def _fixture(root: Path) -> Path:
    for relative in (*G.OWNER_PATHS, G.VIEW_RELATIVE_PATH):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return root


def _run(root: Path, *options: str) -> subprocess.CompletedProcess[bytes]:
    command = [sys.executable, "-I", "-B", str(root / G.GENERATOR_RELATIVE_PATH)]
    command += ["--source-root", str(root), *options]
    return subprocess.run(command, cwd=root, capture_output=True, check=False)


def _tree(root: Path) -> list[tuple[object, ...]]:
    def state(path: Path) -> tuple[object, ...]:
        metadata = path.lstat()
        content = path.read_bytes() if path.is_file() and not path.is_symlink() else b""
        return path.relative_to(root), metadata[:7], metadata.st_mtime_ns, content

    return [state(path) for path in sorted(root.rglob("*"))]


def _digest_record(path: str) -> tuple[str, str, int]:
    source = (ROOT / path).read_bytes()
    return path, hashlib.sha256(source).hexdigest(), len(source)


def _assert_failed_without_writes(root: Path) -> None:
    before = _tree(root)
    completed = _run(root, "--check")
    assert completed.returncode == 1 and completed.stdout == b""
    assert completed.stderr.startswith(b"LIB-L0 generated view error: ")
    assert _tree(root) == before


def test_committed_view_is_exact_canonical_bounded_projection() -> None:
    committed = (ROOT / G.VIEW_RELATIVE_PATH).read_bytes()
    assert committed == G.render_view(ROOT)
    assert len(committed) < 8192 and committed.count(b"\n") == 1
    document = json.loads(committed)
    assert set(document) == set(
        "claim_ceiling generator library_lane machine_views policy_inputs schema_version view_role".split()
    )
    assert document["schema_version"] == G.VIEW_SCHEMA_VERSION
    assert document["view_role"] == "generated-read-only-non-authoritative"
    assert document["claim_ceiling"] == G.CLAIM_CEILING
    lane = document["library_lane"]
    keys = {"path", "sha256", "size_bytes"}
    assert set(lane) == {"id", "owners", "status"}
    assert lane["id"] == "LIB-L0" and lane["status"] == "in progress"
    assert lane["owners"] == [
        "docs/ROADMAP.md#3-two-independent-maturity-axes",
        "docs/ROADMAP.md#lib-l0",
    ]
    records = [
        document["generator"],
        *document["policy_inputs"],
        *document["machine_views"],
    ]
    assert [item["path"] for item in records] == EXACT_OWNERS
    assert set(document["generator"]) == keys | {"version"}
    assert all(set(item) == keys for item in document["policy_inputs"])
    assert all(
        set(item) == keys | {"kind", "schema_version"}
        for item in document["machine_views"]
    )
    observed = [f"{x['kind']}:{x['schema_version']}" for x in document["machine_views"]]
    expected_contracts = "declared-diagnostic-schema:spirallens.distribution-validation.v0.10 manifest-schema:spirallens.installed-import-conformance.v0.1 manifest-schema:spirallens.ordered-package-exports.v0.1 manifest-schema:spirallens.python-distribution-members.v0.1".split()
    assert observed == expected_contracts
    expected = {_digest_record(path) for path in EXACT_OWNERS}
    assert {
        (item["path"], item["sha256"], item["size_bytes"]) for item in records
    } == expected
    canonical = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert canonical.encode() + b"\n" == committed


def test_cli_renders_and_checks_without_writes(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    committed = (root / G.VIEW_RELATIVE_PATH).read_bytes()
    rendered = _run(root)
    assert rendered.returncode == 0
    assert rendered.stdout == committed
    assert rendered.stderr == b""
    before = _tree(root)
    checked = _run(root, "--check")
    assert (checked.returncode, checked.stdout, checked.stderr) == (0, b"", b"")
    assert _tree(root) == before


@pytest.mark.parametrize("relative", G.OWNER_PATHS)
def test_check_rejects_each_stale_owner(tmp_path: Path, relative: str) -> None:
    root = _fixture(tmp_path)
    owner = root / relative
    owner.write_bytes(owner.read_bytes() + b"\n")
    _assert_failed_without_writes(root)


def test_roadmap_owner_ambiguity_and_decoys_fail_closed() -> None:
    source = (ROOT / "docs/ROADMAP.md").read_bytes()
    decoy = b'| Library | `LIB-L0` through `LIB-L3` | `LIB-L0` done | x |\n<a id="lib-l0"></a>\n#### LIB-L0 -- decoy\n**Status:** done.\n<a id="lib-l1"></a>\n'
    start = b'<a id="lib-l0"></a>'
    end = b'<a id="lib-l1"></a>'
    temporary = b"TEMPORARY-ANCHOR"
    bad = [
        source.replace(b"`LIB-L0` in progress", b"`LIB-L0` blocked", 1),
        source.replace(
            b'<a id="lib-l0"></a>', b'<a id="lib-l0"></a>\n**Status:** extra.', 1
        ),
        source.replace(
            b"#### LIB-L0 \xe2\x80\x94 Research-package consolidation",
            b"#### LIB-L0 wrong",
            1,
        ),
        b"```\n" + decoy + b"```\n" + source,
        source.replace(start, temporary, 1)
        .replace(end, start, 1)
        .replace(temporary, end, 1),
    ]
    for value in bad:
        with pytest.raises(G.ViewGenerationError):
            G._roadmap_status(value)


def test_validator_schema_rejects_all_competing_binding_forms() -> None:
    bad = b"REPORT_SCHEMA_VERSION = value\0if True:\n REPORT_SCHEMA_VERSION = 'x'\0REPORT_SCHEMA_VERSION = 'x'\ndel REPORT_SCHEMA_VERSION\0REPORT_SCHEMA_VERSION = 'x'\nfrom x import y as REPORT_SCHEMA_VERSION\0REPORT_SCHEMA_VERSION = 'x'\ndef REPORT_SCHEMA_VERSION(): pass\0REPORT_SCHEMA_VERSION = 'x'\nasync def REPORT_SCHEMA_VERSION(): pass\0REPORT_SCHEMA_VERSION = 'x'\nclass REPORT_SCHEMA_VERSION: pass\0REPORT_SCHEMA_VERSION = 'x'\nREPORT_SCHEMA_VERSION = 'y'\0REPORT_SCHEMA_VERSION: str = 'x'\0REPORT_SCHEMA_VERSION = 'x'\nREPORT_SCHEMA_VERSION += 'y'\0REPORT_SCHEMA_VERSION = 'x'\ntry: 1 / 0\nexcept Exception as REPORT_SCHEMA_VERSION: pass\0REPORT_SCHEMA_VERSION = 'x'\nmatch 1:\n case REPORT_SCHEMA_VERSION: pass\0REPORT_SCHEMA_VERSION = 'x'\nmatch {}:\n case {**REPORT_SCHEMA_VERSION}: pass".split(
        b"\0"
    )
    for source in bad:
        with pytest.raises(G.ViewGenerationError):
            G._validator_schema(source)


def test_manifest_schema_rejects_non_strict_or_wrong_documents() -> None:
    relative, expected = next(iter(G.MANIFEST_SCHEMAS.items()))
    bad = [
        f'{{"schema_version":"{expected}","nested":{{"x":1,"x":2}}}}'.encode(),
        f'{{"schema_version":"{expected}","value":NaN}}'.encode(),
        b'{"schema_version":"wrong"}',
        b"{}",
        b"[]",
    ]
    for source in bad:
        with pytest.raises(G.ViewGenerationError):
            G._manifest_schema(source, relative)


def test_check_rejects_missing_aliases_and_oversized_input(tmp_path: Path) -> None:
    roots = [_fixture(tmp_path / str(index)) for index in range(6)]
    (roots[0] / G.VIEW_RELATIVE_PATH).unlink()
    leaf, copy = roots[1] / G.POLICY_INPUTS[0], roots[1] / "copied-owner"
    shutil.copy2(leaf, copy)
    leaf.unlink()
    leaf.symlink_to(copy)
    docs = roots[2] / "docs"
    docs.rename(roots[2] / "moved-docs")
    docs.symlink_to(roots[2] / "moved-docs", target_is_directory=True)
    alias = roots[3] / G.POLICY_INPUTS[1]
    alias.unlink()
    os.link(roots[3] / G.POLICY_INPUTS[0], alias)
    view = roots[4] / G.VIEW_RELATIVE_PATH
    view.unlink()
    os.link(roots[4] / G.MANIFEST_INPUTS[0], view)
    (roots[5] / G.MANIFEST_INPUTS[0]).write_bytes(b" " * (64 * 1024 + 1))
    for root in roots:
        _assert_failed_without_writes(root)
    with pytest.raises(G.ViewGenerationError):
        G.render_view(roots[0])
