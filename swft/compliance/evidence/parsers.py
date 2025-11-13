"""Pure parsers for evidence documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..utils import json


@dataclass(slots=True)
class SbomComponent:
    name: str
    version: str | None
    purl: str | None
    licenses: list[str]


@dataclass(slots=True)
class TrivyFinding:
    cve_id: str
    severity: str
    pkg: str | None
    installed_version: str | None
    fixed_version: str | None
    artifact: str | None
    path: str | None


def parse_cyclonedx(path: Path) -> list[SbomComponent]:
    data = json.loads(path.read_bytes())
    components: list[SbomComponent] = []
    for component in data.get("components", []):
        components.append(
            SbomComponent(
                name=component.get("name", ""),
                version=component.get("version"),
                purl=component.get("purl"),
                licenses=_extract_licenses(component),
            )
        )
    return components


def parse_trivy_report(path: Path) -> list[TrivyFinding]:
    data = json.loads(path.read_bytes())
    results = data.get("Results", [])
    findings: list[TrivyFinding] = []
    for result in results:
        artifact = result.get("Target")
        for vuln in result.get("Vulnerabilities", []) or []:
            findings.append(
                TrivyFinding(
                    cve_id=vuln.get("VulnerabilityID", ""),
                    severity=vuln.get("Severity", ""),
                    pkg=vuln.get("PkgName"),
                    installed_version=vuln.get("InstalledVersion"),
                    fixed_version=vuln.get("FixedVersion"),
                    artifact=artifact,
                    path=vuln.get("PkgPath") or vuln.get("PrimaryURL"),
                )
            )
    return findings


def _extract_licenses(component: dict[str, Any]) -> list[str]:
    licenses: list[str] = []
    for entry in component.get("licenses", []):
        if isinstance(entry, dict):
            lic = entry.get("license") or entry
            if isinstance(lic, dict):
                value = lic.get("id") or lic.get("name") or lic.get("text")
                if value:
                    licenses.append(value)
            elif isinstance(lic, str):
                licenses.append(lic)
    return licenses

