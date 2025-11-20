from swft.compliance.utils.parsing import parse_csv_list, parse_bool
from swft.compliance.controls.models import normalize_parameter, ControlParameter


def test_parse_csv_list_basic():
    assert parse_csv_list("a, b , ,c") == ["a", "b", "c"]
    assert parse_csv_list("") == []
    assert parse_csv_list(None) == []


def test_parse_bool_values():
    assert parse_bool("true")
    assert parse_bool("YES")
    assert parse_bool("0") is False
    assert parse_bool("No") is False
    try:
        parse_bool("maybe")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for invalid bool")


def test_normalize_parameter_requires_id():
    data = {"id": "ac-2_prm_1", "label": "Frequency", "values": ["30 days"]}
    param = normalize_parameter("AC-2", data)
    assert isinstance(param, ControlParameter)
    assert param.param_id == "ac-2_prm_1"
    try:
        normalize_parameter("AC-2", {"label": "bad"})
    except ValueError as exc:
        assert "parameter without an id" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for missing param id")
