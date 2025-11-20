from swft.compliance.azure.policy_source import AzurePolicySetSource, PolicyDownloadError


def test_policy_source_url_construction() -> None:
    source = AzurePolicySetSource(base_url_template="https://example.com/{filename}", fetcher=lambda url: b"{}")
    assert source.url_for("policy.json") == "https://example.com/policy.json"
    assert source.fetch("policy.json") == b"{}"


def test_policy_source_requires_placeholder() -> None:
    try:
        AzurePolicySetSource(base_url_template="invalid", fetcher=lambda url: b"")
    except ValueError as exc:
        assert "{filename}" in str(exc)
    else:  # pragma: no cover - should not happen
        raise AssertionError("ValueError not raised for invalid template")
