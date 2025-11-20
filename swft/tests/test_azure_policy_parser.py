from pathlib import Path

from swft.compliance.importers.azure.parser import load_initiative, load_policy_states

DATA_DIR = Path(__file__).parent / "data"


def test_load_initiative_controls():
    doc = load_initiative(DATA_DIR / "azure_initiative_sample.json")
    assert doc.version == "1.0.0"
    assert len(doc.policies) == 2
    first = doc.policies[0]
    assert first.policy_definition_id.endswith("require-tags")
    assert first.control_ids == ["AC-2", "CM-2"]


def test_load_policy_states_entries():
    states = load_policy_states(DATA_DIR / "azure_policy_states_sample.json")
    assert len(states) == 2
    assert states[0].compliance_state == "NonCompliant"
    assert states[0].policy_assignment_id.endswith("require-tags")
