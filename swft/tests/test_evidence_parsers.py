from pathlib import Path

from swft.compliance.evidence.parsers import parse_cyclonedx, parse_trivy_report

DATA_DIR = Path(__file__).parent / "data"


def test_parse_cyclonedx_components():
    components = parse_cyclonedx(DATA_DIR / "sbom_sample.json")
    assert len(components) == 2
    assert components[0].name == "app"
    assert components[0].licenses == ["MIT"]


def test_parse_trivy_report():
    findings = parse_trivy_report(DATA_DIR / "trivy_sample.json")
    assert len(findings) == 2
    high = [f for f in findings if f.severity == "HIGH"][0]
    assert high.cve_id == "CVE-123"
    assert high.pkg == "openssl"
    assert high.artifact == "my-image:latest"
