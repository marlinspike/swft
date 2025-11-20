"""Helpers for pinning authoritative source files."""

from __future__ import annotations

import shutil
from pathlib import Path

from .digests import compute_sha256


def pin_source_file(source: Path, dest_dir: Path, stem: str) -> tuple[Path, str]:
    """
    Copy `source` into `dest_dir` with a hash-stamped filename.

    Returns (pinned_path, sha256).
    """
    digest = compute_sha256(source)
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = "".join(source.suffixes) or ".json"
    filename = f"{stem}-{digest[:12]}{ext}"
    dest = dest_dir / filename
    if not dest.exists():
        shutil.copy2(source, dest)
    return dest, digest

