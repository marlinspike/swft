from pathlib import Path

from swft.compliance.oscal.catalog import load_catalog
from swft.compliance.oscal.profile import load_profile

DATA_DIR = Path(__file__).parent / "data"


def test_load_catalog_controls():
    doc = load_catalog(DATA_DIR / "catalog_sample.json")
    assert doc.metadata.title == "Sample Catalog"
    assert doc.metadata.version == "1.0.0"
    assert len(doc.controls) == 2
    ac1 = doc.controls[0]
    assert ac1.control_id == "AC-1"
    assert ac1.family == "Access Control"
    assert len(ac1.parameters) == 1
    assert len(ac1.assessment_objectives) == 1


def test_load_profile_control_ids():
    profile = load_profile(DATA_DIR / "profile_sample.json")
    assert profile.metadata.title == "Sample Baseline"
    assert profile.control_ids == ["AC-1", "AC-2"]

