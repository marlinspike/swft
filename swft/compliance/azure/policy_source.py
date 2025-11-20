"""Helpers for downloading Azure Policy set definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib import request, error
import os


DEFAULT_POLICY_BASE_URL = (
    "https://raw.githubusercontent.com/Azure/azure-policy/master/"
    "built-in-policies/policySetDefinitions/Regulatory%20Compliance/{filename}"
)


class PolicyDownloadError(RuntimeError):
    """Raised when an Azure Policy definition cannot be retrieved."""


FetchFunc = Callable[[str], bytes]


def _default_fetch(url: str) -> bytes:
    try:
        with request.urlopen(url) as resp:  # type: ignore[arg-type]
            if resp.status != 200:
                raise PolicyDownloadError(f"Unexpected status code {resp.status} for {url}")
            return resp.read()
    except error.HTTPError as exc:  # pragma: no cover - triggered only during real fetches
        raise PolicyDownloadError(f"Failed to download {url}: {exc}") from exc
    except error.URLError as exc:  # pragma: no cover - triggered only during real fetches
        raise PolicyDownloadError(f"Failed to reach {url}: {exc}") from exc


@dataclass(slots=True)
class AzurePolicySetSource:
    base_url_template: str | None = None
    fetcher: FetchFunc = _default_fetch

    def __post_init__(self) -> None:
        if not self.base_url_template:
            self.base_url_template = os.environ.get("SWFT_AZURE_POLICY_BASE_URL", DEFAULT_POLICY_BASE_URL)
        if "{filename}" not in (self.base_url_template or ""):
            raise ValueError("Policy base URL template must include '{filename}'.")

    def url_for(self, filename: str) -> str:
        assert self.base_url_template  # appease type checkers
        return self.base_url_template.format(filename=filename)

    def fetch(self, filename: str) -> bytes:
        url = self.url_for(filename)
        return self.fetcher(url)
