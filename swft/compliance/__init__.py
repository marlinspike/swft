"""
Compliance authoring engine package.

Subpackages:
    oscal:    OSCAL models and helpers (future work)
    importers:Catalog, baseline, Azure Policy ingest (future work)
    mapping: Control ownership and evidence linkage (future work)
    evidence:Evidence parsers for SBOM, Trivy, etc. (future work)
    exporters:OSCAL SSP/POA&M writers (future work)
    store:    Persistence layer utilities
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"

