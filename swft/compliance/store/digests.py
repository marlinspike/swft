"""File hashing helpers."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

BUFFER_SIZE = 1024 * 1024


def compute_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(BUFFER_SIZE):
            digest.update(chunk)
    return digest.hexdigest()

