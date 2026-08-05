"""Internal marker for one explicitly supplied repository root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True, slots=True)
class RepositoryContext:
    """Carry an absolute caller-supplied root without granting authority.

    Construction performs no I/O. The narrow import-origin comparison proves
    only same-file identity for one declared repository path; it proves no Git,
    cleanliness, chronology, claim, authority, or publication fact. Each
    consumer retains its own validation and error vocabulary.
    """

    root: Path

    def __post_init__(self) -> None:
        if not isinstance(self.root, Path):
            raise TypeError("RepositoryContext.root must be a Path")
        if not self.root.is_absolute():
            raise ValueError("RepositoryContext.root must be absolute")
        if ".." in self.root.parts:
            raise ValueError("RepositoryContext.root must be lexically normalized")

    def matches_imported_file(
        self,
        *,
        imported_file: str | Path | None,
        repository_path: str,
    ) -> bool:
        """Compare one imported file with its declared checkout location."""

        if not isinstance(repository_path, str):
            raise ValueError("repository_path must be a repository-relative path")
        relative = PurePosixPath(repository_path)
        if (
            not relative.parts
            or relative.is_absolute()
            or ".." in relative.parts
        ):
            raise ValueError("repository_path must be a repository-relative path")
        try:
            return (self.root.joinpath(*relative.parts)).samefile(imported_file)
        except (OSError, TypeError, ValueError):
            return False
