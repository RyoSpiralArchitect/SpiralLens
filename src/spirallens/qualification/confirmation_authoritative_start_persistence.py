"""Atomic structural persistence for one future authoritative D7 start.

The word ``authoritative`` in this module names a dedicated filesystem lane;
it is not an authority claim.  The writer accepts already-derived attempt
records plus a canonical source descriptor and verification-evidence record,
binds them into one closed start transaction, and publishes the directory with
a native descriptor-relative no-replace rename.  The strict loader reparses
those records and proves their exact bytes, semantic joins, filesystem
identities, and the publication facts directly observed by the current call.

This module does not authenticate the documents or their issuers, independently
repeat their live observations, issue a launch authorization, grant an exclusive
start, invoke a runner, infer execution, reconstruct ownership from disk, or
confer scientific, D7, or D8 authority.  A byte-identical existing destination
is a conflict, never permission to resume.
"""

from __future__ import annotations

import errno
import os
import secrets
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import ClassVar, Self

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from . import confirmation_attempt_authority as a
from . import confirmation_attempt_evidence as e
from . import confirmation_attempt_evidence_validation as ev
from . import confirmation_attempt_persistence as p
from . import confirmation_attempt_records as r
from . import confirmation_attempt_terminal_persistence as tp
from . import confirmation_attempt_validation as v
from .common import QualificationContractError

__all__: tuple[str, ...] = ()

D7_AUTHORITATIVE_START_LANE_BASENAME = "d7-authoritative-start-v0"
D7_AUTHORITATIVE_START_MANIFEST_FILENAME = "start-manifest.json"
D7_AUTHORITATIVE_START_MANIFEST_SCHEMA_VERSION = (
    "spirallens.d7-authoritative-start-manifest.v0.1"
)
D7_AUTHORITATIVE_START_MEMBER_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-authoritative-start-member-binding.v0.1"
)

D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME = "launch-authority-source-envelope.json"
D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME = "authority-verification-evidence.json"
D7_ATTEMPT_DECLARATION_FILENAME = "attempt-declaration.json"
D7_AUTHORIZATION_OUTPUT_ABSENCE_FILENAME = "authorization-output-absence-receipt.json"
D7_AUTHORIZATION_TERMINAL_ABSENCE_FILENAME = (
    "authorization-terminal-absence-receipt.json"
)
D7_LAUNCH_AUTHORIZATION_FILENAME = "launch-authorization.json"
D7_ATTEMPT_CLAIM_FILENAME = "attempt-claim.json"
D7_PRE_START_OUTPUT_ABSENCE_FILENAME = "pre-start-output-absence-receipt.json"
D7_PRE_START_TERMINAL_ABSENCE_FILENAME = "pre-start-terminal-absence-receipt.json"
D7_EXECUTION_START_FILENAME = "execution-start.json"

_AUTHORITY_SOURCE_ROLE = "launch-authority-source-envelope"
_VERIFICATION_EVIDENCE_ROLE = "launch-authority-verification-evidence"
_TEMPORARY_SUFFIX = ".tmp"
_STAGING_MARKER = ".d7-authoritative-start-transaction."
_MAX_STAGE_NAME_ATTEMPTS = 32
_MAX_OPAQUE_AUTHORITY_BYTES = a.MAX_D7_LAUNCH_AUTHORITY_INPUT_BYTES
_MAX_MANIFEST_BYTES = 512 * 1024

_MEMBER_ORDER = (
    (
        "launch-authority-source-envelope",
        D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME,
    ),
    ("authority-verification-evidence", D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME),
    ("attempt-declaration", D7_ATTEMPT_DECLARATION_FILENAME),
    (
        "authorization-output-absence-receipt",
        D7_AUTHORIZATION_OUTPUT_ABSENCE_FILENAME,
    ),
    (
        "authorization-terminal-absence-receipt",
        D7_AUTHORIZATION_TERMINAL_ABSENCE_FILENAME,
    ),
    ("launch-authorization", D7_LAUNCH_AUTHORIZATION_FILENAME),
    ("attempt-claim", D7_ATTEMPT_CLAIM_FILENAME),
    ("pre-start-output-absence-receipt", D7_PRE_START_OUTPUT_ABSENCE_FILENAME),
    (
        "pre-start-terminal-absence-receipt",
        D7_PRE_START_TERMINAL_ABSENCE_FILENAME,
    ),
    ("execution-start", D7_EXECUTION_START_FILENAME),
)
_KIND_BY_FILENAME = MappingProxyType(
    {filename: kind for kind, filename in _MEMBER_ORDER}
)


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be an exact JSON object")
    return dict(value)


def _sequence(value: object, *, label: str) -> list[object]:
    if type(value) is not list:
        raise QualificationContractError(f"{label} must be an exact JSON array")
    return list(value)


def _exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    if set(value) != expected:
        raise QualificationContractError(f"{label} fields differ")


def _string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty string")
    return value


def _positive_int(value: object, *, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise QualificationContractError(f"{label} must be a positive plain integer")
    return value


def _false(value: object, *, label: str) -> None:
    if value is not False:
        raise QualificationContractError(f"{label} must remain false")


def _true(value: object, *, label: str) -> None:
    if value is not True:
        raise QualificationContractError(f"{label} must equal true")


def _contract_id(value: object, *, label: str) -> str:
    result = _string(value, label=label)
    # Reuse the exact authority binding parser for its contract-id grammar.
    a.D7AuthorityArtifactBinding(
        artifact_role="contract-id-validation",
        artifact_contract_id=result,
        canonical_sha256="0" * 64,
        byte_count=1,
    )
    return result


@dataclass(frozen=True, slots=True)
class D7AuthoritativeStartMemberBinding:
    """One exact immutable member of the structural start transaction."""

    member_kind: str
    filename: str
    contract_id: str
    member_canonical_sha256: str
    byte_count: int

    schema_version: ClassVar[str] = D7_AUTHORITATIVE_START_MEMBER_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        kind = _string(self.member_kind, label="member_kind")
        filename = _string(self.filename, label="filename")
        if _KIND_BY_FILENAME.get(filename) != kind:
            raise QualificationContractError(
                "authoritative-start member kind and filename differ"
            )
        if PurePosixPath(filename).name != filename or not filename.endswith(".json"):
            raise QualificationContractError(
                "authoritative-start member filename must be one JSON basename"
            )
        _contract_id(self.contract_id, label="contract_id")
        p._sha256(self.member_canonical_sha256, "member_canonical_sha256")
        _positive_int(self.byte_count, label="byte_count")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "member_kind": self.member_kind,
            "filename": self.filename,
            "contract_id": self.contract_id,
            "member_canonical_sha256": self.member_canonical_sha256,
            "byte_count": self.byte_count,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="authoritative-start member binding")
        _exact_keys(
            item,
            {
                "schema_version",
                "member_kind",
                "filename",
                "contract_id",
                "member_canonical_sha256",
                "byte_count",
            },
            label="authoritative-start member binding",
        )
        if item["schema_version"] != cls.schema_version:
            raise QualificationContractError(
                "authoritative-start member binding schema differs"
            )
        return cls(
            member_kind=_string(item["member_kind"], label="member_kind"),
            filename=_string(item["filename"], label="filename"),
            contract_id=_contract_id(item["contract_id"], label="contract_id"),
            member_canonical_sha256=p._sha256(
                item["member_canonical_sha256"],
                "member_canonical_sha256",
            ),
            byte_count=_positive_int(item["byte_count"], label="byte_count"),
        )


@dataclass(frozen=True, slots=True)
class D7AuthoritativeStartManifest:
    """Closed canonical inventory and local filesystem identity binding."""

    replay_target_sha256: str
    attempt_key_sha256: str
    attempt_declaration_sha256: str
    launch_authorization_sha256: str
    attempt_claim_sha256: str
    execution_start_sha256: str
    store_root_realpath: str
    store_device: int
    store_inode: int
    lane_realpath: str
    lane_device: int
    lane_inode: int
    start_directory_device: int
    start_directory_inode: int
    immutable_members: tuple[D7AuthoritativeStartMemberBinding, ...]

    schema_version: ClassVar[str] = D7_AUTHORITATIVE_START_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "replay_target_sha256",
            "attempt_key_sha256",
            "attempt_declaration_sha256",
            "launch_authorization_sha256",
            "attempt_claim_sha256",
            "execution_start_sha256",
        ):
            p._sha256(getattr(self, name), name)
        for name in ("store_root_realpath", "lane_realpath"):
            path = Path(_string(getattr(self, name), label=name))
            if not path.is_absolute() or Path(os.path.realpath(path)) != path:
                raise QualificationContractError(
                    f"{name} must be one absolute real path"
                )
        for name in (
            "store_device",
            "store_inode",
            "lane_device",
            "lane_inode",
            "start_directory_device",
            "start_directory_inode",
        ):
            _positive_int(getattr(self, name), label=name)
        if Path(self.lane_realpath) != (
            Path(self.store_root_realpath) / D7_AUTHORITATIVE_START_LANE_BASENAME
        ):
            raise QualificationContractError(
                "authoritative-start lane differs from the exact store child"
            )
        if type(self.immutable_members) is not tuple or any(
            type(member) is not D7AuthoritativeStartMemberBinding
            for member in self.immutable_members
        ):
            raise TypeError("immutable_members must be exact start member bindings")
        observed_order = tuple(
            (member.member_kind, member.filename) for member in self.immutable_members
        )
        if observed_order != _MEMBER_ORDER:
            raise QualificationContractError(
                "authoritative-start manifest inventory or order differs"
            )
        digests = tuple(
            member.member_canonical_sha256 for member in self.immutable_members
        )
        if len(digests) != len(set(digests)):
            raise QualificationContractError(
                "authoritative-start member canonical identities must be distinct"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "record_kind": "authoritative-start-structural-manifest",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "replay_target_sha256": self.replay_target_sha256,
            "attempt_key_sha256": self.attempt_key_sha256,
            "attempt_declaration_sha256": self.attempt_declaration_sha256,
            "launch_authorization_sha256": self.launch_authorization_sha256,
            "attempt_claim_sha256": self.attempt_claim_sha256,
            "execution_start_sha256": self.execution_start_sha256,
            "store_root_realpath": self.store_root_realpath,
            "store_device": self.store_device,
            "store_inode": self.store_inode,
            "lane_realpath": self.lane_realpath,
            "lane_device": self.lane_device,
            "lane_inode": self.lane_inode,
            "start_directory_device": self.start_directory_device,
            "start_directory_inode": self.start_directory_inode,
            "immutable_members": [
                member.to_dict() for member in self.immutable_members
            ],
            "publication_mode": "descriptor-relative-native-no-replace-directory-rename",
            "member_file_fsync_required": True,
            "staging_directory_fsync_required": True,
            "authority_authenticated": False,
            "authority_granted": False,
            "exclusive_start_authorized": False,
            "ownership_issued": False,
            "execution_observed": False,
            "scientific_claim_eligible": False,
            "retry_authorized": False,
            "replay_authorized": False,
            "d8_eligible": False,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        item = _mapping(value, label="authoritative-start manifest")
        constants: dict[str, object] = {
            "schema_version": cls.schema_version,
            "record_kind": "authoritative-start-structural-manifest",
            "claim_ceiling": r.D7_RECORD_CLAIM_CEILING,
            "publication_mode": (
                "descriptor-relative-native-no-replace-directory-rename"
            ),
            "member_file_fsync_required": True,
            "staging_directory_fsync_required": True,
            "authority_authenticated": False,
            "authority_granted": False,
            "exclusive_start_authorized": False,
            "ownership_issued": False,
            "execution_observed": False,
            "scientific_claim_eligible": False,
            "retry_authorized": False,
            "replay_authorized": False,
            "d8_eligible": False,
        }
        fields = {
            "replay_target_sha256",
            "attempt_key_sha256",
            "attempt_declaration_sha256",
            "launch_authorization_sha256",
            "attempt_claim_sha256",
            "execution_start_sha256",
            "store_root_realpath",
            "store_device",
            "store_inode",
            "lane_realpath",
            "lane_device",
            "lane_inode",
            "start_directory_device",
            "start_directory_inode",
            "immutable_members",
        }
        _exact_keys(item, set(constants) | fields, label="authoritative-start manifest")
        for name, expected in constants.items():
            if item[name] != expected or type(item[name]) is not type(expected):
                raise QualificationContractError(
                    f"authoritative-start manifest {name} differs"
                )
        return cls(
            replay_target_sha256=p._sha256(
                item["replay_target_sha256"], "replay_target_sha256"
            ),
            attempt_key_sha256=p._sha256(
                item["attempt_key_sha256"], "attempt_key_sha256"
            ),
            attempt_declaration_sha256=p._sha256(
                item["attempt_declaration_sha256"],
                "attempt_declaration_sha256",
            ),
            launch_authorization_sha256=p._sha256(
                item["launch_authorization_sha256"],
                "launch_authorization_sha256",
            ),
            attempt_claim_sha256=p._sha256(
                item["attempt_claim_sha256"], "attempt_claim_sha256"
            ),
            execution_start_sha256=p._sha256(
                item["execution_start_sha256"], "execution_start_sha256"
            ),
            store_root_realpath=_string(
                item["store_root_realpath"], label="store_root_realpath"
            ),
            store_device=_positive_int(item["store_device"], label="store_device"),
            store_inode=_positive_int(item["store_inode"], label="store_inode"),
            lane_realpath=_string(item["lane_realpath"], label="lane_realpath"),
            lane_device=_positive_int(item["lane_device"], label="lane_device"),
            lane_inode=_positive_int(item["lane_inode"], label="lane_inode"),
            start_directory_device=_positive_int(
                item["start_directory_device"], label="start_directory_device"
            ),
            start_directory_inode=_positive_int(
                item["start_directory_inode"], label="start_directory_inode"
            ),
            immutable_members=tuple(
                D7AuthoritativeStartMemberBinding.from_dict(member)
                for member in _sequence(
                    item["immutable_members"], label="immutable_members"
                )
            ),
        )

    @classmethod
    def from_canonical_bytes(cls, source: bytes, *, expected_sha256: str) -> Self:
        expected = p._sha256(expected_sha256, "expected_sha256")
        if type(source) is not bytes or not source or len(source) > _MAX_MANIFEST_BYTES:
            raise QualificationContractError(
                "authoritative-start manifest bytes exceed the cap"
            )
        if sha256_bytes(source) != expected:
            raise QualificationContractError(
                "authoritative-start manifest SHA-256 differs before parse"
            )
        try:
            parsed = parse_canonical_json(
                source,
                label="authoritative-start manifest",
            )
        except (CanonicalJsonError, RecursionError) as error:
            raise QualificationContractError(
                "authoritative-start manifest is not canonical JSON"
            ) from error
        result = cls.from_dict(parsed)
        if result.canonical_bytes != source:
            raise QualificationContractError(
                "authoritative-start manifest canonical bytes differ"
            )
        return result


@dataclass(frozen=True, slots=True)
class D7LoadedAuthoritativeStartTransaction:
    """Strictly loaded structural start bytes; never runner ownership."""

    path: Path
    store_root: Path
    lane_path: Path
    manifest: D7AuthoritativeStartManifest
    launch_authority_source_envelope_binding: a.D7AuthorityArtifactBinding
    verification_evidence_binding: a.D7AuthorityArtifactBinding
    immutable_member_sources: Mapping[str, bytes]
    declaration: r.D7AttemptDeclarationRecord
    authorization_output_receipt: e.D7AuthorizationPathAbsenceReceipt
    authorization_terminal_receipt: e.D7AuthorizationPathAbsenceReceipt
    authorization: r.D7LaunchAuthorizationRecord
    claim: r.D7AttemptClaimRecord
    pre_start_output_receipt: e.D7PreStartPathAbsenceReceipt
    pre_start_terminal_receipt: e.D7PreStartPathAbsenceReceipt
    start: r.D7ExecutionStartRecord
    store_device: int
    store_inode: int
    lane_device: int
    lane_inode: int
    directory_device: int
    directory_inode: int
    created_by_call: bool
    atomic_no_replace_performed_by_call: bool
    parent_directory_fsync_proved: bool | None

    start_structure_validated: ClassVar[bool] = True
    authority_authenticated: ClassVar[bool] = False
    authority_granted: ClassVar[bool] = False
    authoritative_lifecycle_eligible: ClassVar[bool] = False
    exclusive_start_authorized: ClassVar[bool] = False
    ownership_issued: ClassVar[bool] = False
    execution_observed: ClassVar[bool] = False
    started_unresolved_established: ClassVar[bool] = False
    verification_evidence_strictly_parsed: ClassVar[bool] = True
    verification_evidence_descriptor_and_start_subset_rejoined: ClassVar[bool] = True
    live_observation_digests_reauthenticated: ClassVar[bool] = False
    all_live_observation_digests_semantically_rejoined: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False
    retry_authorized: ClassVar[bool] = False
    replay_authorized: ClassVar[bool] = False
    d8_eligible: ClassVar[bool] = False

    @property
    def directory_identity_sha256(self) -> str:
        """Deterministic binding for this exact visible start directory."""

        return sha256_bytes(
            canonical_json_bytes(
                {
                    "schema_version": (
                        "spirallens.d7-authoritative-start-directory-identity.v0.1"
                    ),
                    "path": str(self.path),
                    "device": self.directory_device,
                    "inode": self.directory_inode,
                    "attempt_key_sha256": self.start.attempt_key_sha256,
                    "manifest_sha256": self.manifest.canonical_sha256,
                }
            )
        )

    def __post_init__(self) -> None:
        for name in ("path", "store_root", "lane_path"):
            value = getattr(self, name)
            if not isinstance(value, Path) or not value.is_absolute():
                raise TypeError(f"{name} must be an absolute Path")
        if type(self.manifest) is not D7AuthoritativeStartManifest:
            raise TypeError("manifest must be an exact start manifest")
        if type(self.launch_authority_source_envelope_binding) is not (
            a.D7AuthorityArtifactBinding
        ) or type(self.verification_evidence_binding) is not (
            a.D7AuthorityArtifactBinding
        ):
            raise TypeError("source/evidence bindings must have exact types")
        expected_types = (
            r.D7AttemptDeclarationRecord,
            e.D7AuthorizationPathAbsenceReceipt,
            e.D7AuthorizationPathAbsenceReceipt,
            r.D7LaunchAuthorizationRecord,
            r.D7AttemptClaimRecord,
            e.D7PreStartPathAbsenceReceipt,
            e.D7PreStartPathAbsenceReceipt,
            r.D7ExecutionStartRecord,
        )
        values = (
            self.declaration,
            self.authorization_output_receipt,
            self.authorization_terminal_receipt,
            self.authorization,
            self.claim,
            self.pre_start_output_receipt,
            self.pre_start_terminal_receipt,
            self.start,
        )
        if tuple(type(value) for value in values) != expected_types:
            raise TypeError("loaded authoritative-start records have wrong types")
        if not isinstance(self.immutable_member_sources, Mapping):
            raise TypeError("immutable_member_sources must be a mapping")
        for name in (
            "store_device",
            "store_inode",
            "lane_device",
            "lane_inode",
            "directory_device",
            "directory_inode",
        ):
            _positive_int(getattr(self, name), label=name)
        for name in ("created_by_call", "atomic_no_replace_performed_by_call"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be a plain boolean")
        if self.atomic_no_replace_performed_by_call is not self.created_by_call:
            raise QualificationContractError("start publication call facts differ")
        if (
            self.parent_directory_fsync_proved is not None
            and type(self.parent_directory_fsync_proved) is not bool
        ):
            raise TypeError("parent_directory_fsync_proved must be bool or None")
        if not self.created_by_call and self.parent_directory_fsync_proved is not None:
            raise QualificationContractError(
                "a reload cannot reconstruct historical parent fsync proof"
            )
        _validate_attempt_values(
            declaration=self.declaration,
            authorization_output_receipt=self.authorization_output_receipt,
            authorization_terminal_receipt=self.authorization_terminal_receipt,
            authorization=self.authorization,
            claim=self.claim,
            pre_start_output_receipt=self.pre_start_output_receipt,
            pre_start_terminal_receipt=self.pre_start_terminal_receipt,
            start=self.start,
        )
        if (
            self.path != self.lane_path / _start_leaf(self.start.attempt_key_sha256)
            or self.store_root != Path(self.manifest.store_root_realpath)
            or self.lane_path != Path(self.manifest.lane_realpath)
            or (self.store_device, self.store_inode)
            != (self.manifest.store_device, self.manifest.store_inode)
            or (self.lane_device, self.lane_inode)
            != (self.manifest.lane_device, self.manifest.lane_inode)
            or (self.directory_device, self.directory_inode)
            != (
                self.manifest.start_directory_device,
                self.manifest.start_directory_inode,
            )
        ):
            raise QualificationContractError(
                "loaded authoritative-start filesystem identities differ"
            )


def _start_leaf(attempt_key_sha256: str) -> str:
    return f"{p._sha256(attempt_key_sha256, 'attempt_key_sha256')}.authoritative-start"


def _staging_prefix(attempt_key_sha256: str) -> str:
    return f".{p._sha256(attempt_key_sha256, 'attempt_key_sha256')}{_STAGING_MARKER}"


def _open_existing_child_directory(
    parent: p._DirectoryAnchor,
    *,
    leaf: str,
    label: str,
) -> p._DirectoryAnchor:
    try:
        descriptor = os.open(leaf, p._directory_flags(), dir_fd=parent.descriptor)
    except OSError as error:
        raise QualificationContractError(f"cannot open {label}: {error}") from error
    try:
        opened = os.fstat(descriptor)
        displayed = p._relative_stat(parent, leaf)
        if (
            displayed is None
            or not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(displayed.st_mode)
            or p._identity(opened) != p._identity(displayed)
        ):
            raise QualificationContractError(
                f"{label} is not one stable real directory"
            )
        return p._DirectoryAnchor(
            path=parent.path / leaf,
            descriptor=descriptor,
            device=opened.st_dev,
            inode=opened.st_ino,
        )
    except BaseException:
        os.close(descriptor)
        raise


def _matching_staging_entries(
    lane: p._DirectoryAnchor,
    attempt_key_sha256: str,
) -> tuple[str, ...]:
    prefix = _staging_prefix(attempt_key_sha256)
    try:
        names = os.listdir(lane.descriptor)
    except OSError as error:
        raise QualificationContractError(
            f"cannot enumerate authoritative-start lane: {error}"
        ) from error
    return tuple(
        sorted(
            name
            for name in names
            if name.startswith(prefix) and name.endswith(_TEMPORARY_SUFFIX)
        )
    )


def _reject_staging_entries(
    lane: p._DirectoryAnchor,
    attempt_key_sha256: str,
) -> None:
    if _matching_staging_entries(lane, attempt_key_sha256):
        raise QualificationContractError(
            "authoritative-start lane contains unpublished staging entries; "
            "offline recovery is required after orphanhood is established"
        )


def _create_stage(
    lane: p._DirectoryAnchor,
    attempt_key_sha256: str,
) -> tuple[p._DirectoryAnchor, str]:
    prefix = _staging_prefix(attempt_key_sha256)
    for _index in range(_MAX_STAGE_NAME_ATTEMPTS):
        leaf = f"{prefix}{secrets.token_hex(12)}{_TEMPORARY_SUFFIX}"
        try:
            os.mkdir(leaf, 0o700, dir_fd=lane.descriptor)
        except FileExistsError:
            continue
        except OSError as error:
            raise QualificationContractError(
                f"cannot create authoritative-start staging directory: {error}"
            ) from error
        try:
            os.fsync(lane.descriptor)
        except OSError as error:
            try:
                os.rmdir(leaf, dir_fd=lane.descriptor)
                os.fsync(lane.descriptor)
            except OSError:
                pass
            raise QualificationContractError(
                "authoritative-start staging-directory creation durability is unproved"
            ) from error
        return (
            _open_existing_child_directory(
                lane,
                leaf=leaf,
                label="authoritative-start staging directory",
            ),
            leaf,
        )
    raise QualificationContractError(
        "cannot allocate an authoritative-start staging directory"
    )


def _published_stage_identity_matches(
    lane: p._DirectoryAnchor,
    *,
    stage_leaf: str,
    start_leaf: str,
    stage_identity: tuple[int, int],
) -> bool:
    staged = p._relative_stat(lane, stage_leaf)
    published = p._relative_stat(lane, start_leaf)
    return (
        staged is None
        and published is not None
        and stat.S_ISDIR(published.st_mode)
        and p._identity(published) == stage_identity
    )


def _opaque_source(
    source: bytes,
    binding: a.D7AuthorityArtifactBinding,
    *,
    expected_role: str,
    label: str,
) -> bytes:
    if type(binding) is not a.D7AuthorityArtifactBinding:
        raise TypeError(f"{label} binding must be exact D7AuthorityArtifactBinding")
    if binding.artifact_role != expected_role:
        raise QualificationContractError(f"{label} binding role differs")
    if (
        type(source) is not bytes
        or not source
        or len(source) > _MAX_OPAQUE_AUTHORITY_BYTES
        or len(source) != binding.byte_count
        or sha256_bytes(source) != binding.canonical_sha256
    ):
        raise QualificationContractError(
            f"{label} bytes differ from their opaque binding"
        )
    try:
        parse_canonical_json(source, label=label)
    except (CanonicalJsonError, RecursionError) as error:
        raise QualificationContractError(f"{label} is not canonical JSON") from error
    return source


def _parse_launch_authority_source_envelope(
    source: bytes,
    binding: a.D7AuthorityArtifactBinding,
) -> object:
    # Local imports keep this persistence module independently importable and
    # avoid making the fused execution module part of its initialization graph.
    from . import confirmation_fused_authority as fused_authority

    validated = _opaque_source(
        source,
        binding,
        expected_role=_AUTHORITY_SOURCE_ROLE,
        label="launch authority source envelope",
    )
    if (
        binding.artifact_contract_id
        != fused_authority.D7_FUSED_AUTHORITY_DESCRIPTOR_SCHEMA_VERSION
    ):
        raise QualificationContractError(
            "launch authority source envelope contract differs"
        )
    try:
        parsed = parse_canonical_json(
            validated,
            label="launch authority source envelope",
        )
    except (CanonicalJsonError, RecursionError) as error:
        raise QualificationContractError(
            "launch authority source envelope is not canonical JSON"
        ) from error
    descriptor = fused_authority._D7FusedAuthorityLaunchDescriptor.from_dict(parsed)
    if (
        descriptor.canonical_bytes != validated
        or descriptor.canonical_sha256 != binding.canonical_sha256
    ):
        raise QualificationContractError(
            "launch authority source envelope canonical round-trip differs"
        )
    return descriptor


def _parse_verification_evidence(
    source: bytes,
    binding: a.D7AuthorityArtifactBinding,
) -> object:
    # This is intentionally local: confirmation_fused_start imports this module.
    from . import confirmation_fused_start as fused_start

    validated = _opaque_source(
        source,
        binding,
        expected_role=_VERIFICATION_EVIDENCE_ROLE,
        label="authority verification evidence",
    )
    if (
        binding.artifact_contract_id
        != fused_start.D7_FUSED_START_VERIFICATION_EVIDENCE_SCHEMA_VERSION
    ):
        raise QualificationContractError(
            "authority verification evidence contract differs"
        )
    return fused_start._D7FusedStartVerificationEvidence.from_canonical_bytes(
        validated,
        expected_sha256=binding.canonical_sha256,
    )


def _rejoin_persisted_verification_evidence(
    descriptor: object,
    verification: object,
    *,
    declaration: r.D7AttemptDeclarationRecord,
    authorization: r.D7LaunchAuthorizationRecord,
    start: r.D7ExecutionStartRecord,
) -> None:
    descriptor_sha256 = sha256_bytes(descriptor.canonical_bytes)  # type: ignore[attr-defined]
    if verification.descriptor_sha256 != descriptor_sha256:  # type: ignore[attr-defined]
        raise QualificationContractError(
            "verification evidence descriptor source digest differs"
        )

    inventory = {
        member.artifact_role: member.canonical_sha256
        for member in descriptor.inventory  # type: ignore[attr-defined]
    }
    expected_inventory = {
        "launch-authority-input-bundle": verification.launch_bundle_sha256,
        "replay-target": verification.replay_target_sha256,
        "launch-intent": verification.launch_intent_sha256,
        "execution-source-runtime-closure": (
            verification.source_runtime_closure_sha256
        ),
        "runtime-specification": verification.runtime_specification_sha256,
        "family-admission": verification.family_admission_sha256,
        "execution-identity": verification.execution_identity_sha256,
        "physical-store-lane-identity": verification.physical_identity_sha256,
        "full-design-freeze": verification.full_design_freeze_sha256,
    }
    if inventory != expected_inventory:
        raise QualificationContractError(
            "verification evidence differs from descriptor inventory"
        )

    if not (
        verification.attempt_key_sha256
        == declaration.attempt_key_sha256
        == start.attempt_key_sha256
    ):
        raise QualificationContractError(
            "verification evidence attempt binding differs"
        )
    if not (
        verification.replay_target_sha256
        == declaration.replay_target_sha256
        == start.replay_target_sha256
    ):
        raise QualificationContractError(
            "verification evidence replay-target binding differs"
        )
    if verification.launch_intent_sha256 != declaration.launch_intent_sha256:
        raise QualificationContractError(
            "verification evidence launch-intent binding differs"
        )
    if not (
        verification.execution_identity_sha256
        == declaration.execution_identity_receipt_sha256
        == start.execution_identity_receipt_sha256
        == start.observed_execution_identity_receipt_sha256
    ):
        raise QualificationContractError(
            "verification evidence execution-identity binding differs"
        )
    if not (
        verification.runtime_specification_sha256
        == authorization.runtime_specification_sha256
        == start.observed_runtime_specification_sha256
    ):
        raise QualificationContractError(
            "verification evidence runtime-specification binding differs"
        )
    if (
        verification.full_design_freeze_sha256
        != authorization.full_design_freeze_receipt_sha256
    ):
        raise QualificationContractError(
            "verification evidence full-design-freeze binding differs"
        )


def _validate_attempt_values(
    *,
    declaration: r.D7AttemptDeclarationRecord,
    authorization_output_receipt: e.D7AuthorizationPathAbsenceReceipt,
    authorization_terminal_receipt: e.D7AuthorizationPathAbsenceReceipt,
    authorization: r.D7LaunchAuthorizationRecord,
    claim: r.D7AttemptClaimRecord,
    pre_start_output_receipt: e.D7PreStartPathAbsenceReceipt,
    pre_start_terminal_receipt: e.D7PreStartPathAbsenceReceipt,
    start: r.D7ExecutionStartRecord,
) -> None:
    expected_types = (
        r.D7AttemptDeclarationRecord,
        e.D7AuthorizationPathAbsenceReceipt,
        e.D7AuthorizationPathAbsenceReceipt,
        r.D7LaunchAuthorizationRecord,
        r.D7AttemptClaimRecord,
        e.D7PreStartPathAbsenceReceipt,
        e.D7PreStartPathAbsenceReceipt,
        r.D7ExecutionStartRecord,
    )
    values = (
        declaration,
        authorization_output_receipt,
        authorization_terminal_receipt,
        authorization,
        claim,
        pre_start_output_receipt,
        pre_start_terminal_receipt,
        start,
    )
    if tuple(type(value) for value in values) != expected_types:
        raise TypeError("authoritative-start persistence values have wrong exact types")
    if declaration.attempt_role is not r.D7AttemptRole.PRIMARY_CONFIRMATION:
        raise QualificationContractError(
            "authoritative-start persistence currently requires a primary attempt"
        )
    v.validate_d7_attempt_prefix(
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        start=start,
    )
    ev.validate_d7_path_absence_receipt_chain(
        declaration=declaration,
        authorization=authorization,
        claim=claim,
        start=start,
        authorization_output_receipt=authorization_output_receipt,
        authorization_terminal_receipt=authorization_terminal_receipt,
        pre_start_output_receipt=pre_start_output_receipt,
        pre_start_terminal_receipt=pre_start_terminal_receipt,
    )


def _record_sources(
    *,
    launch_authority_source_envelope_source: bytes,
    verification_evidence_source: bytes,
    declaration: r.D7AttemptDeclarationRecord,
    authorization_output_receipt: e.D7AuthorizationPathAbsenceReceipt,
    authorization_terminal_receipt: e.D7AuthorizationPathAbsenceReceipt,
    authorization: r.D7LaunchAuthorizationRecord,
    claim: r.D7AttemptClaimRecord,
    pre_start_output_receipt: e.D7PreStartPathAbsenceReceipt,
    pre_start_terminal_receipt: e.D7PreStartPathAbsenceReceipt,
    start: r.D7ExecutionStartRecord,
) -> dict[str, bytes]:
    return {
        D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME: (
            launch_authority_source_envelope_source
        ),
        D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME: verification_evidence_source,
        D7_ATTEMPT_DECLARATION_FILENAME: declaration.canonical_bytes,
        D7_AUTHORIZATION_OUTPUT_ABSENCE_FILENAME: (
            authorization_output_receipt.canonical_bytes
        ),
        D7_AUTHORIZATION_TERMINAL_ABSENCE_FILENAME: (
            authorization_terminal_receipt.canonical_bytes
        ),
        D7_LAUNCH_AUTHORIZATION_FILENAME: authorization.canonical_bytes,
        D7_ATTEMPT_CLAIM_FILENAME: claim.canonical_bytes,
        D7_PRE_START_OUTPUT_ABSENCE_FILENAME: (
            pre_start_output_receipt.canonical_bytes
        ),
        D7_PRE_START_TERMINAL_ABSENCE_FILENAME: (
            pre_start_terminal_receipt.canonical_bytes
        ),
        D7_EXECUTION_START_FILENAME: start.canonical_bytes,
    }


def _member_bindings(
    sources: Mapping[str, bytes],
    *,
    launch_authority_source_envelope_binding: a.D7AuthorityArtifactBinding,
    verification_evidence_binding: a.D7AuthorityArtifactBinding,
) -> tuple[D7AuthoritativeStartMemberBinding, ...]:
    contract_ids = {
        D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME: (
            launch_authority_source_envelope_binding.artifact_contract_id
        ),
        D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME: (
            verification_evidence_binding.artifact_contract_id
        ),
        D7_ATTEMPT_DECLARATION_FILENAME: r.D7_ATTEMPT_DECLARATION_SCHEMA_VERSION,
        D7_AUTHORIZATION_OUTPUT_ABSENCE_FILENAME: (
            e.D7_AUTHORIZATION_PATH_ABSENCE_RECEIPT_CONTRACT_ID
        ),
        D7_AUTHORIZATION_TERMINAL_ABSENCE_FILENAME: (
            e.D7_AUTHORIZATION_PATH_ABSENCE_RECEIPT_CONTRACT_ID
        ),
        D7_LAUNCH_AUTHORIZATION_FILENAME: r.D7_LAUNCH_AUTHORIZATION_SCHEMA_VERSION,
        D7_ATTEMPT_CLAIM_FILENAME: r.D7_ATTEMPT_CLAIM_SCHEMA_VERSION,
        D7_PRE_START_OUTPUT_ABSENCE_FILENAME: (
            e.D7_PRE_START_PATH_ABSENCE_RECEIPT_CONTRACT_ID
        ),
        D7_PRE_START_TERMINAL_ABSENCE_FILENAME: (
            e.D7_PRE_START_PATH_ABSENCE_RECEIPT_CONTRACT_ID
        ),
        D7_EXECUTION_START_FILENAME: r.D7_EXECUTION_START_SCHEMA_VERSION,
    }
    return tuple(
        D7AuthoritativeStartMemberBinding(
            member_kind=kind,
            filename=filename,
            contract_id=contract_ids[filename],
            member_canonical_sha256=sha256_bytes(sources[filename]),
            byte_count=len(sources[filename]),
        )
        for kind, filename in _MEMBER_ORDER
    )


def _member_cap(filename: str) -> int:
    if filename in {
        D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME,
        D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME,
    }:
        return _MAX_OPAQUE_AUTHORITY_BYTES
    if filename in {
        D7_AUTHORIZATION_OUTPUT_ABSENCE_FILENAME,
        D7_AUTHORIZATION_TERMINAL_ABSENCE_FILENAME,
        D7_PRE_START_OUTPUT_ABSENCE_FILENAME,
        D7_PRE_START_TERMINAL_ABSENCE_FILENAME,
    }:
        return e.MAX_D7_ATTEMPT_EVIDENCE_BYTES
    return r.MAX_D7_CHRONOLOGY_RECORD_BYTES


def _validate_store_coordinates(
    store: p._DirectoryAnchor,
    lane: p._DirectoryAnchor,
    *,
    declaration: r.D7AttemptDeclarationRecord,
    receipts: tuple[
        e.D7AuthorizationPathAbsenceReceipt | e.D7PreStartPathAbsenceReceipt,
        ...,
    ],
) -> None:
    if lane.path != store.path / D7_AUTHORITATIVE_START_LANE_BASENAME:
        raise QualificationContractError(
            "authoritative-start lane is not the exact store child"
        )
    p._reject_reserved_subjects(store.path, declaration.attempt_key_sha256, *receipts)
    reserved = (lane.path, lane.path / _start_leaf(declaration.attempt_key_sha256))
    for receipt in receipts:
        subject = Path(receipt.subject_path)
        if any(p._paths_overlap(subject, path) for path in reserved):
            raise QualificationContractError(
                "D7 output/terminal subject overlaps authoritative-start persistence"
            )
        p._verify_receipt_location(store.path, receipt)
    p._verify_anchor(store, label="authoritative-start store")
    p._verify_anchor(lane, label="authoritative-start lane")


def _parse_member_records(
    sources: Mapping[str, bytes],
    bindings: Mapping[str, D7AuthoritativeStartMemberBinding],
) -> tuple[
    r.D7AttemptDeclarationRecord,
    e.D7AuthorizationPathAbsenceReceipt,
    e.D7AuthorizationPathAbsenceReceipt,
    r.D7LaunchAuthorizationRecord,
    r.D7AttemptClaimRecord,
    e.D7PreStartPathAbsenceReceipt,
    e.D7PreStartPathAbsenceReceipt,
    r.D7ExecutionStartRecord,
]:
    def parse(filename: str, record_type: type[object]) -> object:
        member = bindings[filename]
        return record_type.from_canonical_bytes(  # type: ignore[attr-defined,no-any-return]
            sources[filename],
            expected_sha256=member.member_canonical_sha256,
        )

    declaration = parse(D7_ATTEMPT_DECLARATION_FILENAME, r.D7AttemptDeclarationRecord)
    authorization_output = parse(
        D7_AUTHORIZATION_OUTPUT_ABSENCE_FILENAME,
        e.D7AuthorizationPathAbsenceReceipt,
    )
    authorization_terminal = parse(
        D7_AUTHORIZATION_TERMINAL_ABSENCE_FILENAME,
        e.D7AuthorizationPathAbsenceReceipt,
    )
    authorization = parse(
        D7_LAUNCH_AUTHORIZATION_FILENAME,
        r.D7LaunchAuthorizationRecord,
    )
    claim = parse(D7_ATTEMPT_CLAIM_FILENAME, r.D7AttemptClaimRecord)
    pre_start_output = parse(
        D7_PRE_START_OUTPUT_ABSENCE_FILENAME,
        e.D7PreStartPathAbsenceReceipt,
    )
    pre_start_terminal = parse(
        D7_PRE_START_TERMINAL_ABSENCE_FILENAME,
        e.D7PreStartPathAbsenceReceipt,
    )
    start = parse(D7_EXECUTION_START_FILENAME, r.D7ExecutionStartRecord)
    assert type(declaration) is r.D7AttemptDeclarationRecord
    assert type(authorization_output) is e.D7AuthorizationPathAbsenceReceipt
    assert type(authorization_terminal) is e.D7AuthorizationPathAbsenceReceipt
    assert type(authorization) is r.D7LaunchAuthorizationRecord
    assert type(claim) is r.D7AttemptClaimRecord
    assert type(pre_start_output) is e.D7PreStartPathAbsenceReceipt
    assert type(pre_start_terminal) is e.D7PreStartPathAbsenceReceipt
    assert type(start) is r.D7ExecutionStartRecord
    return (
        declaration,
        authorization_output,
        authorization_terminal,
        authorization,
        claim,
        pre_start_output,
        pre_start_terminal,
        start,
    )


def _load_transaction(
    store_directory: str | Path,
    *,
    attempt_key_sha256: str,
    expected_manifest_sha256: str,
    created_by_call: bool,
    parent_directory_fsync_proved: bool | None,
) -> D7LoadedAuthoritativeStartTransaction:
    key = p._sha256(attempt_key_sha256, "attempt_key_sha256")
    expected_manifest = p._sha256(expected_manifest_sha256, "expected_manifest_sha256")
    store = p._open_real_directory(store_directory, label="authoritative-start store")
    lane: p._DirectoryAnchor | None = None
    transaction: p._DirectoryAnchor | None = None
    try:
        lane = _open_existing_child_directory(
            store,
            leaf=D7_AUTHORITATIVE_START_LANE_BASENAME,
            label="authoritative-start lane",
        )
        start_leaf = _start_leaf(key)
        displayed = p._relative_stat(lane, start_leaf)
        if displayed is None:
            if _matching_staging_entries(lane, key):
                raise QualificationContractError(
                    "authoritative start is absent with unpublished staging; "
                    "offline recovery is required"
                )
            raise QualificationContractError("authoritative start is absent")
        if not stat.S_ISDIR(displayed.st_mode):
            raise QualificationContractError(
                "authoritative start must be one real directory"
            )
        transaction = _open_existing_child_directory(
            lane,
            leaf=start_leaf,
            label="authoritative-start transaction",
        )
        manifest_source, manifest_stat = p._read_exact_file(
            transaction,
            D7_AUTHORITATIVE_START_MANIFEST_FILENAME,
            expected_sha256=expected_manifest,
            maximum_bytes=_MAX_MANIFEST_BYTES,
            label="authoritative-start manifest",
        )
        manifest = D7AuthoritativeStartManifest.from_canonical_bytes(
            manifest_source,
            expected_sha256=expected_manifest,
        )
        expected_names = {
            *(member.filename for member in manifest.immutable_members),
            D7_AUTHORITATIVE_START_MANIFEST_FILENAME,
        }
        try:
            observed_names = set(os.listdir(transaction.descriptor))
        except OSError as error:
            raise QualificationContractError(
                f"cannot enumerate authoritative-start transaction: {error}"
            ) from error
        if observed_names != expected_names:
            raise QualificationContractError(
                "authoritative-start transaction differs from its closed inventory"
            )
        bindings = {member.filename: member for member in manifest.immutable_members}
        sources: dict[str, bytes] = {}
        identities: dict[str, tuple[int, int]] = {}
        for member in manifest.immutable_members:
            source, observed = p._read_exact_file(
                transaction,
                member.filename,
                expected_sha256=member.member_canonical_sha256,
                maximum_bytes=_member_cap(member.filename),
                label=f"authoritative-start member {member.filename}",
            )
            if len(source) != member.byte_count:
                raise QualificationContractError(
                    f"authoritative-start member {member.filename} byte count differs"
                )
            sources[member.filename] = source
            identities[member.filename] = p._identity(observed)
        all_identities = (p._identity(manifest_stat), *identities.values())
        if len(all_identities) != len(set(all_identities)):
            raise QualificationContractError(
                "authoritative-start files must have distinct unaliased identities"
            )
        authority_source_binding = a.D7AuthorityArtifactBinding(
            artifact_role=_AUTHORITY_SOURCE_ROLE,
            artifact_contract_id=bindings[
                D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME
            ].contract_id,
            canonical_sha256=bindings[
                D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME
            ].member_canonical_sha256,
            byte_count=bindings[
                D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME
            ].byte_count,
        )
        verification_binding = a.D7AuthorityArtifactBinding(
            artifact_role=_VERIFICATION_EVIDENCE_ROLE,
            artifact_contract_id=bindings[
                D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME
            ].contract_id,
            canonical_sha256=bindings[
                D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME
            ].member_canonical_sha256,
            byte_count=bindings[D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME].byte_count,
        )
        source_descriptor = _parse_launch_authority_source_envelope(
            sources[D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME],
            authority_source_binding,
        )
        verification_evidence = _parse_verification_evidence(
            sources[D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME],
            verification_binding,
        )
        (
            declaration,
            authorization_output,
            authorization_terminal,
            authorization,
            claim,
            pre_start_output,
            pre_start_terminal,
            start,
        ) = _parse_member_records(sources, bindings)
        _validate_attempt_values(
            declaration=declaration,
            authorization_output_receipt=authorization_output,
            authorization_terminal_receipt=authorization_terminal,
            authorization=authorization,
            claim=claim,
            pre_start_output_receipt=pre_start_output,
            pre_start_terminal_receipt=pre_start_terminal,
            start=start,
        )
        _rejoin_persisted_verification_evidence(
            source_descriptor,
            verification_evidence,
            declaration=declaration,
            authorization=authorization,
            start=start,
        )
        if (
            manifest.replay_target_sha256 != start.replay_target_sha256
            or manifest.attempt_key_sha256 != start.attempt_key_sha256
            or manifest.attempt_declaration_sha256 != declaration.canonical_sha256
            or manifest.launch_authorization_sha256 != authorization.canonical_sha256
            or manifest.attempt_claim_sha256 != claim.canonical_sha256
            or manifest.execution_start_sha256 != start.canonical_sha256
            or manifest.store_root_realpath != str(store.path)
            or (manifest.store_device, manifest.store_inode)
            != (store.device, store.inode)
            or manifest.lane_realpath != str(lane.path)
            or (manifest.lane_device, manifest.lane_inode) != (lane.device, lane.inode)
            or (
                manifest.start_directory_device,
                manifest.start_directory_inode,
            )
            != (transaction.device, transaction.inode)
        ):
            raise QualificationContractError(
                "authoritative-start manifest joins or filesystem identities differ"
            )
        receipts = (
            authorization_output,
            authorization_terminal,
            pre_start_output,
            pre_start_terminal,
        )
        _validate_store_coordinates(
            store,
            lane,
            declaration=declaration,
            receipts=receipts,
        )
        try:
            final_names = set(os.listdir(transaction.descriptor))
        except OSError as error:
            raise QualificationContractError(
                "cannot re-enumerate authoritative-start transaction"
            ) from error
        if final_names != expected_names:
            raise QualificationContractError(
                "authoritative-start inventory changed during strict reload"
            )
        tp._revalidate_file_set(
            transaction,
            {
                D7_AUTHORITATIVE_START_MANIFEST_FILENAME: (
                    manifest_source,
                    p._identity(manifest_stat),
                    manifest.canonical_sha256,
                    _MAX_MANIFEST_BYTES,
                    "authoritative-start manifest",
                ),
                **{
                    member.filename: (
                        sources[member.filename],
                        identities[member.filename],
                        member.member_canonical_sha256,
                        _member_cap(member.filename),
                        f"authoritative-start member {member.filename}",
                    )
                    for member in manifest.immutable_members
                },
            },
        )
        p._verify_anchor(transaction, label="authoritative-start transaction")
        p._verify_anchor(lane, label="authoritative-start lane")
        p._verify_anchor(store, label="authoritative-start store")
        return D7LoadedAuthoritativeStartTransaction(
            path=lane.path / start_leaf,
            store_root=store.path,
            lane_path=lane.path,
            manifest=manifest,
            launch_authority_source_envelope_binding=authority_source_binding,
            verification_evidence_binding=verification_binding,
            immutable_member_sources=MappingProxyType(dict(sources)),
            declaration=declaration,
            authorization_output_receipt=authorization_output,
            authorization_terminal_receipt=authorization_terminal,
            authorization=authorization,
            claim=claim,
            pre_start_output_receipt=pre_start_output,
            pre_start_terminal_receipt=pre_start_terminal,
            start=start,
            store_device=store.device,
            store_inode=store.inode,
            lane_device=lane.device,
            lane_inode=lane.inode,
            directory_device=transaction.device,
            directory_inode=transaction.inode,
            created_by_call=created_by_call,
            atomic_no_replace_performed_by_call=created_by_call,
            parent_directory_fsync_proved=parent_directory_fsync_proved,
        )
    finally:
        if transaction is not None:
            os.close(transaction.descriptor)
        if lane is not None:
            os.close(lane.descriptor)
        os.close(store.descriptor)


def load_d7_authoritative_start_transaction(
    store_directory: str | Path,
    *,
    attempt_key_sha256: str,
    expected_manifest_sha256: str,
) -> D7LoadedAuthoritativeStartTransaction:
    """Strictly reload one closed structural start transaction.

    Historical publication method and parent-directory fsync cannot be
    reconstructed by a later reader, so the returned call facts are false and
    ``None``.  The loader never mints post-start ownership.
    """

    return _load_transaction(
        store_directory,
        attempt_key_sha256=attempt_key_sha256,
        expected_manifest_sha256=expected_manifest_sha256,
        created_by_call=False,
        parent_directory_fsync_proved=None,
    )


def _fsync_published_parent(lane: p._DirectoryAnchor) -> bool:
    try:
        os.fsync(lane.descriptor)
        return True
    except OSError:
        return False


def persist_d7_authoritative_start_transaction_no_replace(
    store_directory: str | Path,
    *,
    launch_authority_source_envelope_source: bytes,
    launch_authority_source_envelope_binding: a.D7AuthorityArtifactBinding,
    verification_evidence_source: bytes,
    verification_evidence_binding: a.D7AuthorityArtifactBinding,
    declaration: r.D7AttemptDeclarationRecord,
    authorization_output_receipt: e.D7AuthorizationPathAbsenceReceipt,
    authorization_terminal_receipt: e.D7AuthorizationPathAbsenceReceipt,
    authorization: r.D7LaunchAuthorizationRecord,
    claim: r.D7AttemptClaimRecord,
    pre_start_output_receipt: e.D7PreStartPathAbsenceReceipt,
    pre_start_terminal_receipt: e.D7PreStartPathAbsenceReceipt,
    start: r.D7ExecutionStartRecord,
) -> D7LoadedAuthoritativeStartTransaction:
    """Publish one exact structural start directory without replacement.

    All inputs remain data.  The descriptor and verification evidence are
    strictly parsed and rejoined to the persisted attempt records; no
    signature, issuer, live re-observation, or launch authority is inferred.
    """

    _validate_attempt_values(
        declaration=declaration,
        authorization_output_receipt=authorization_output_receipt,
        authorization_terminal_receipt=authorization_terminal_receipt,
        authorization=authorization,
        claim=claim,
        pre_start_output_receipt=pre_start_output_receipt,
        pre_start_terminal_receipt=pre_start_terminal_receipt,
        start=start,
    )
    source_descriptor = _parse_launch_authority_source_envelope(
        launch_authority_source_envelope_source,
        launch_authority_source_envelope_binding,
    )
    verification_evidence = _parse_verification_evidence(
        verification_evidence_source,
        verification_evidence_binding,
    )
    _rejoin_persisted_verification_evidence(
        source_descriptor,
        verification_evidence,
        declaration=declaration,
        authorization=authorization,
        start=start,
    )
    sources = _record_sources(
        launch_authority_source_envelope_source=(
            launch_authority_source_envelope_source
        ),
        verification_evidence_source=verification_evidence_source,
        declaration=declaration,
        authorization_output_receipt=authorization_output_receipt,
        authorization_terminal_receipt=authorization_terminal_receipt,
        authorization=authorization,
        claim=claim,
        pre_start_output_receipt=pre_start_output_receipt,
        pre_start_terminal_receipt=pre_start_terminal_receipt,
        start=start,
    )
    bindings = _member_bindings(
        sources,
        launch_authority_source_envelope_binding=(
            launch_authority_source_envelope_binding
        ),
        verification_evidence_binding=verification_evidence_binding,
    )
    store = p._open_real_directory(store_directory, label="authoritative-start store")
    lane: p._DirectoryAnchor | None = None
    stage: p._DirectoryAnchor | None = None
    stage_leaf: str | None = None
    owned_files: dict[str, tuple[int, int]] = {}
    published = False
    parent_fsync_proved = False
    manifest: D7AuthoritativeStartManifest | None = None
    try:
        lane = _open_existing_child_directory(
            store,
            leaf=D7_AUTHORITATIVE_START_LANE_BASENAME,
            label="authoritative-start lane",
        )
        receipts = (
            authorization_output_receipt,
            authorization_terminal_receipt,
            pre_start_output_receipt,
            pre_start_terminal_receipt,
        )
        _validate_store_coordinates(
            store,
            lane,
            declaration=declaration,
            receipts=receipts,
        )
        key = start.attempt_key_sha256
        start_leaf = _start_leaf(key)
        _reject_staging_entries(lane, key)
        p._require_absent(
            lane,
            start_leaf,
            label="D7 authoritative-start transaction",
        )
        p._reobserve_absence(store.path, pre_start_output_receipt)
        p._reobserve_absence(store.path, pre_start_terminal_receipt)
        stage, stage_leaf = _create_stage(lane, key)
        manifest = D7AuthoritativeStartManifest(
            replay_target_sha256=start.replay_target_sha256,
            attempt_key_sha256=key,
            attempt_declaration_sha256=declaration.canonical_sha256,
            launch_authorization_sha256=authorization.canonical_sha256,
            attempt_claim_sha256=claim.canonical_sha256,
            execution_start_sha256=start.canonical_sha256,
            store_root_realpath=str(store.path),
            store_device=store.device,
            store_inode=store.inode,
            lane_realpath=str(lane.path),
            lane_device=lane.device,
            lane_inode=lane.inode,
            start_directory_device=stage.device,
            start_directory_inode=stage.inode,
            immutable_members=bindings,
        )
        member_by_filename = {
            member.filename: member for member in manifest.immutable_members
        }
        for filename in (name for _kind, name in _MEMBER_ORDER):
            member = member_by_filename[filename]
            owned_files[filename] = tp._write_stage_file(
                stage,
                filename,
                sources[filename],
                expected_sha256=member.member_canonical_sha256,
                maximum_bytes=_member_cap(filename),
                label=f"authoritative-start member {filename}",
            )
        owned_files[D7_AUTHORITATIVE_START_MANIFEST_FILENAME] = tp._write_stage_file(
            stage,
            D7_AUTHORITATIVE_START_MANIFEST_FILENAME,
            manifest.canonical_bytes,
            expected_sha256=manifest.canonical_sha256,
            maximum_bytes=_MAX_MANIFEST_BYTES,
            label="authoritative-start manifest",
        )
        try:
            os.fsync(stage.descriptor)
        except OSError as error:
            raise QualificationContractError(
                "authoritative-start staging-directory durability is unproved"
            ) from error
        _validate_store_coordinates(
            store,
            lane,
            declaration=declaration,
            receipts=receipts,
        )
        p._reobserve_absence(store.path, pre_start_output_receipt)
        p._reobserve_absence(store.path, pre_start_terminal_receipt)
        p._require_absent(
            lane,
            start_leaf,
            label="D7 authoritative-start transaction",
        )
        tp._revalidate_file_set(
            stage,
            {
                **{
                    filename: (
                        sources[filename],
                        owned_files[filename],
                        member_by_filename[filename].member_canonical_sha256,
                        _member_cap(filename),
                        f"authoritative-start member {filename}",
                    )
                    for _kind, filename in _MEMBER_ORDER
                },
                D7_AUTHORITATIVE_START_MANIFEST_FILENAME: (
                    manifest.canonical_bytes,
                    owned_files[D7_AUTHORITATIVE_START_MANIFEST_FILENAME],
                    manifest.canonical_sha256,
                    _MAX_MANIFEST_BYTES,
                    "authoritative-start manifest",
                ),
            },
        )
        p._verify_anchor(stage, label="authoritative-start staging directory")
        p._verify_anchor(lane, label="authoritative-start lane")
        stage_identity = (stage.device, stage.inode)
        try:
            p._rename_file_no_replace(lane, stage_leaf, start_leaf)
            published = True
        except OSError as error:
            if _published_stage_identity_matches(
                lane,
                stage_leaf=stage_leaf,
                start_leaf=start_leaf,
                stage_identity=stage_identity,
            ):
                published = True
            elif error.errno in (errno.EEXIST, errno.ENOTEMPTY):
                raise QualificationContractError(
                    "refusing to replace existing authoritative-start transaction: "
                    f"{lane.path / start_leaf}"
                ) from error
            else:
                raise QualificationContractError(
                    f"cannot atomically publish authoritative start: {error}"
                ) from error
        if not _published_stage_identity_matches(
            lane,
            stage_leaf=stage_leaf,
            start_leaf=start_leaf,
            stage_identity=stage_identity,
        ):
            raise QualificationContractError(
                "published authoritative-start directory identity differs"
            )
        parent_fsync_proved = _fsync_published_parent(lane)
    finally:
        cleanup_proved = published
        cleanup_error: BaseException | None = None
        try:
            if stage is not None:
                try:
                    if not published and stage_leaf is not None and lane is not None:
                        cleanup_proved = tp._cleanup_stage(
                            lane,
                            stage,
                            stage_leaf,
                            owned_files,
                        )
                except BaseException as error:
                    cleanup_error = error
                finally:
                    os.close(stage.descriptor)
        finally:
            if lane is not None:
                os.close(lane.descriptor)
            os.close(store.descriptor)
        if cleanup_error is not None or (stage is not None and not cleanup_proved):
            raise QualificationContractError(
                "authoritative-start staging cleanup is unproved; "
                "offline recovery is required"
            ) from cleanup_error

    if not published or manifest is None:
        raise QualificationContractError("authoritative start was not published")
    return _load_transaction(
        store_directory,
        attempt_key_sha256=start.attempt_key_sha256,
        expected_manifest_sha256=manifest.canonical_sha256,
        created_by_call=True,
        parent_directory_fsync_proved=parent_fsync_proved,
    )
