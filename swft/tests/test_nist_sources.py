from pathlib import Path

from swft.compliance.oscal.sources import NistSp80053Source


def test_sp80053_urls() -> None:
    source = NistSp80053Source(version="v1.3.0", file_format="json", fetcher=lambda url: b"{}")
    assert (
        source.catalog_url()
        == "https://raw.githubusercontent.com/usnistgov/oscal-content/v1.3.0/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json"
    )
    assert (
        source.baseline_url("high")
        == "https://raw.githubusercontent.com/usnistgov/oscal-content/v1.3.0/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_HIGH-baseline_profile.json"
    )


def test_download_writes_file(tmp_path: Path) -> None:
    captured: list[str] = []

    def fake_fetch(url: str) -> bytes:
        captured.append(url)
        return b"{}"

    source = NistSp80053Source(fetcher=fake_fetch)
    dest = source.download_catalog(tmp_path)
    assert dest.exists()
    assert dest.read_text() == "{}"
    assert captured and captured[0].endswith("NIST_SP-800-53_rev5_catalog.json")


def test_custom_base_url() -> None:
    source = NistSp80053Source(
        base_url_template="https://example.com/{version}/{fmt}/{filename}",
        fetcher=lambda url: b"",
    )
    url = source.catalog_url()
    assert url == "https://example.com/v1.3.0/json/NIST_SP-800-53_rev5_catalog.json"
