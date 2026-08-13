"""Private held-file reading mechanics shared by bounded loaders."""

from __future__ import annotations

import os
from pathlib import Path
import stat


__all__: tuple[str, ...] = ()

_ReadMessages = tuple[str, str, str, str, str, str]


def _open_directory_chain(directory: Path) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open("/", flags)
    try:
        for component in directory.parts[1:]:
            next_flags = flags | getattr(os, "O_NOFOLLOW", 0)
            next_descriptor = os.open(component, next_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        metadata.st_nlink,
    )


def _read_bounded_regular_file(
    path: Path,
    *,
    maximum_bytes: int,
    error_type: type[Exception],
    messages: _ReadMessages,
) -> bytes:
    """Read one held, single-link regular file under a strict byte bound."""

    parent, read, regular, link, size, drift = messages
    try:
        parent_descriptor = _open_directory_chain(path.parent)
    except OSError as error:
        raise error_type(parent) from error
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_descriptor = -1
    try:
        file_descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise error_type(regular)
        if before.st_nlink != 1:
            raise error_type(link)
        if before.st_size > maximum_bytes:
            raise error_type(size)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(file_descriptor, 64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > maximum_bytes:
                raise error_type(size)
            chunks.append(chunk)
        after = os.fstat(file_descriptor)
        if _identity(before) != _identity(after) or total != after.st_size:
            raise error_type(drift)
        return b"".join(chunks)
    except OSError as error:
        raise error_type(read) from error
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        os.close(parent_descriptor)
