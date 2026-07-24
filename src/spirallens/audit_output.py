"""Descriptor-relative, single-shot output reservation for subject audits."""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import stat


_RESERVATION_TOKEN = object()
_MARKER_VERSION = "spirallens-neighbor-audit-reservation-v0.3"


class AuditOutputReservation:
    """Held directory/file descriptors for one exclusive final pathname."""

    __slots__ = (
        "_closed",
        "_file_descriptor",
        "_identity",
        "_name",
        "_parent_descriptor",
        "_parent_identity",
        "_path",
        "_persisted",
        "_recovery_name",
        "_token",
    )

    def __init__(
        self,
        *,
        token: object,
        path: Path,
        parent_descriptor: int,
        file_descriptor: int,
        identity: tuple[int, int],
        recovery_name: str,
    ) -> None:
        if token is not _RESERVATION_TOKEN:
            raise TypeError(
                "AuditOutputReservation cannot be constructed directly"
            )
        self._token = token
        self._path = path
        self._name = path.name
        self._parent_descriptor = parent_descriptor
        parent_metadata = os.fstat(parent_descriptor)
        self._parent_identity = (
            parent_metadata.st_dev,
            parent_metadata.st_ino,
        )
        self._file_descriptor = file_descriptor
        self._identity = identity
        self._recovery_name = recovery_name
        self._closed = False
        self._persisted = False

    @property
    def path(self) -> Path:
        return self._path

    def _validate_entry(self) -> None:
        if self._closed or self._token is not _RESERVATION_TOKEN:
            raise ValueError("audit output reservation is closed or invalid")
        current = os.stat(
            self._name,
            dir_fd=self._parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != self._identity
        ):
            raise ValueError("audit output reservation identity changed")

    def _validate_parent_path(self) -> None:
        current_descriptor = _open_directory_chain(self._path.parent)
        try:
            current = os.fstat(current_descriptor)
            if (
                current.st_dev,
                current.st_ino,
            ) != self._parent_identity:
                raise ValueError(
                    "audit output parent directory identity changed"
                )
        finally:
            os.close(current_descriptor)

    def _validate_recovery_entry(
        self,
        identity: tuple[int, int],
    ) -> None:
        current = os.stat(
            self._recovery_name,
            dir_fd=self._parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != identity
        ):
            raise ValueError(
                "audit output recovery identity changed"
            )

    def persist(self, payload: bytes) -> None:
        """Stage a recovery copy before replacing the held marker bytes."""

        if (
            not isinstance(payload, bytes)
            or not payload
            or self._persisted
        ):
            raise ValueError("audit output payload or state is invalid")
        self._validate_parent_path()
        self._validate_entry()
        recovery_flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
        if hasattr(os, "O_CLOEXEC"):
            recovery_flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            recovery_flags |= os.O_NOFOLLOW
        recovery_descriptor = os.open(
            self._recovery_name,
            recovery_flags,
            0o600,
            dir_fd=self._parent_descriptor,
        )
        try:
            _write_all(recovery_descriptor, payload)
            os.fsync(recovery_descriptor)
            recovery_metadata = os.fstat(recovery_descriptor)
            recovery_identity = (
                recovery_metadata.st_dev,
                recovery_metadata.st_ino,
            )
            self._validate_recovery_entry(recovery_identity)
            os.fsync(self._parent_descriptor)
            self._validate_parent_path()
            self._validate_entry()

            os.lseek(self._file_descriptor, 0, os.SEEK_SET)
            os.ftruncate(self._file_descriptor, 0)
            _write_all(self._file_descriptor, payload)
            os.fsync(self._file_descriptor)
            self._validate_entry()
            os.lseek(self._file_descriptor, 0, os.SEEK_SET)
            persisted = bytearray()
            while chunk := os.read(
                self._file_descriptor,
                8 * 1024 * 1024,
            ):
                persisted.extend(chunk)
            if bytes(persisted) != payload:
                raise OSError(
                    "audit output readback differs from staged payload"
                )
            self._validate_entry()
            self._validate_recovery_entry(recovery_identity)
            os.fsync(self._parent_descriptor)
            self._validate_parent_path()
            os.unlink(
                self._recovery_name,
                dir_fd=self._parent_descriptor,
            )
            os.fsync(self._parent_descriptor)
            self._validate_entry()
            self._validate_parent_path()
            self._persisted = True
        finally:
            os.close(recovery_descriptor)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            os.close(self._file_descriptor)
        finally:
            os.close(self._parent_descriptor)


def _open_directory_chain(directory: Path) -> int:
    if not directory.is_absolute():
        raise ValueError("audit output parent must be absolute")
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open("/", flags)
    try:
        for component in directory.parts[1:]:
            component_flags = flags
            if hasattr(os, "O_NOFOLLOW"):
                component_flags |= os.O_NOFOLLOW
            next_descriptor = os.open(
                component,
                component_flags,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    written = 0
    while written < len(view):
        count = os.write(descriptor, view[written:])
        if count <= 0:
            raise OSError("audit output write made no progress")
        written += count


def reserve_audit_output(path: Path) -> AuditOutputReservation:
    """Create and fsync one final-path marker with O_EXCL and held dirfds."""

    destination = Path(os.path.abspath(path))
    if not destination.name:
        raise ValueError("audit output filename must be non-empty")
    parent_descriptor = _open_directory_chain(destination.parent)
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        recovery_name = (
            f".{destination.name}.recovery-"
            f"{secrets.token_hex(16)}"
        )
        marker = (
            f"{_MARKER_VERSION}\n"
            f"recovery={recovery_name}\n"
        ).encode("utf-8")
        file_descriptor = os.open(
            destination.name,
            flags,
            0o600,
            dir_fd=parent_descriptor,
        )
    except FileExistsError as error:
        os.close(parent_descriptor)
        raise FileExistsError(
            "frozen neighbor audit output is already reserved or exists: "
            f"{destination}"
        ) from error
    except BaseException:
        os.close(parent_descriptor)
        raise
    try:
        _write_all(file_descriptor, marker)
        os.fsync(file_descriptor)
        os.fsync(parent_descriptor)
        metadata = os.fstat(file_descriptor)
    except BaseException:
        os.close(file_descriptor)
        os.close(parent_descriptor)
        raise
    return AuditOutputReservation(
        token=_RESERVATION_TOKEN,
        path=destination,
        parent_descriptor=parent_descriptor,
        file_descriptor=file_descriptor,
        identity=(metadata.st_dev, metadata.st_ino),
        recovery_name=recovery_name,
    )


def persist_reserved_audit_output(
    reservation: object,
    *,
    destination: Path,
    payload: bytes,
) -> Path:
    """Persist only through a genuine live reservation capability."""

    if (
        not isinstance(reservation, AuditOutputReservation)
        or reservation._token is not _RESERVATION_TOKEN
        or reservation.path != destination
    ):
        raise TypeError("audit output reservation capability is invalid")
    reservation.persist(payload)
    return destination
