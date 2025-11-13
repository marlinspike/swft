"""
Helpers for downloading OSCAL content from authoritative sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, ClassVar
from urllib import request, error


class OscalDownloadError(RuntimeError):
    """Raised when an OSCAL artifact cannot be downloaded."""


FetchFunc = Callable[[str], bytes]


def _default_fetch(url: str) -> bytes:
    try:
        with request.urlopen(url) as resp:  # type: ignore[call-arg]
            if resp.status != 200:  # pragma: no cover - urllib only sets on HTTP errors
                raise OscalDownloadError(f"Unexpected status code {resp.status} for {url}")
            return resp.read()
    except error.HTTPError as exc:  # pragma: no cover - network errors
        raise OscalDownloadError(f"Failed to download {url}: {exc}") from exc
    except error.URLError as exc:  # pragma: no cover - network errors
        raise OscalDownloadError(f"Failed to reach {url}: {exc}") from exc


DEFAULT_BASE_URL: Final[str] = (
    "https://raw.githubusercontent.com/usnistgov/oscal-content/{version}/nist.gov/SP800-53/rev5/{fmt}/{filename}"
)


@dataclass(slots=True)
class NistSp80053Source:
    """
    Downloads SP 800-53 Rev5 OSCAL artifacts from the public NIST repository.
    """

    version: str = "v1.3.0"
    file_format: str = "json"
    fetcher: FetchFunc = _default_fetch
    base_url_template: str = DEFAULT_BASE_URL

    FORMAT_SUFFIXES: ClassVar[dict[str, str]] = {"json": ".json", "yaml": ".yaml", "xml": ".xml"}
    BASELINE_VARIANTS: ClassVar[dict[str, str]] = {
        "low": "LOW",
        "moderate": "MODERATE",
        "high": "HIGH",
        "privacy": "PRIVACY",
    }

    def __post_init__(self) -> None:
        fmt = self.file_format.lower()
        if fmt not in self.FORMAT_SUFFIXES:
            raise ValueError(f"Unsupported OSCAL format '{self.file_format}'. Choose from {', '.join(self.FORMAT_SUFFIXES)}.")
        self.file_format = fmt

    def download_catalog(self, destination_dir: Path) -> Path:
        """Download the SP 800-53 Rev5 catalog."""
        filename = "NIST_SP-800-53_rev5_catalog"
        return self._download(filename, destination_dir)

    def download_baseline(self, level: str, destination_dir: Path) -> Path:
        """Download a baseline profile (LOW/MODERATE/HIGH/PRIVACY)."""
        key = level.lower()
        if key not in self.BASELINE_VARIANTS:
            raise ValueError(f"Unknown baseline '{level}'. Supported values: {', '.join(sorted(self.BASELINE_VARIANTS))}.")
        variant = self.BASELINE_VARIANTS[key]
        filename = f"NIST_SP-800-53_rev5_{variant}-baseline_profile"
        return self._download(filename, destination_dir)

    def catalog_url(self) -> str:
        return self._build_url("NIST_SP-800-53_rev5_catalog")

    def baseline_url(self, level: str) -> str:
        key = level.lower()
        if key not in self.BASELINE_VARIANTS:
            raise ValueError(f"Unknown baseline '{level}'. Supported values: {', '.join(sorted(self.BASELINE_VARIANTS))}.")
        variant = self.BASELINE_VARIANTS[key]
        return self._build_url(f"NIST_SP-800-53_rev5_{variant}-baseline_profile")

    def _download(self, filename: str, destination_dir: Path) -> Path:
        url = self._build_url(filename)
        destination_dir.mkdir(parents=True, exist_ok=True)
        target = destination_dir / f"{filename}{self.FORMAT_SUFFIXES[self.file_format]}"
        data = self.fetcher(url)
        target.write_bytes(data)
        return target

    def _build_url(self, filename: str) -> str:
        return self.base_url_template.format(
            version=self.version,
            fmt=self.file_format,
            filename=f"{filename}{self.FORMAT_SUFFIXES[self.file_format]}",
        )
