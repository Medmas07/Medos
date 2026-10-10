from datetime import datetime

import pytest

from domain.node_registration import InvalidRegistration, NodeRegistration

NOW = datetime.fromisoformat("2026-10-10T08:00:00+01:00")


def registration(**changes) -> NodeRegistration:
    values = {
        "node_ref": "node-hospital-b",
        "organization_ref": "org-hospital-b",
        "base_url": "http://localhost:8102",
        "contract_versions": frozenset({"1.0"}),
        "approval_decision_ref": "dec-hospital-b",
        "registered_at": NOW,
        "updated_at": NOW,
    }
    return NodeRegistration(**(values | changes))


@pytest.mark.parametrize(
    "base_url",
    ["http://localhost:8102", "https://node-b.example.org/federation"],
)
def test_accepts_absolute_http_urls(base_url):
    assert registration(base_url=base_url).node.node_ref == "node-hospital-b"


@pytest.mark.parametrize(
    "base_url",
    [
        "localhost:8102",
        "ftp://localhost",
        "http://user:secret@localhost:8102",
        "http://localhost:8102?token=x",
        "http://localhost:8102#x",
        "http:///path",
    ],
    ids=["no_scheme", "ftp", "credentials", "query", "fragment", "no_host"],
)
def test_rejects_unusable_or_leaky_urls(base_url):
    with pytest.raises(InvalidRegistration):
        registration(base_url=base_url)


def test_requires_a_supported_node_contract_version():
    assert registration(contract_versions=frozenset({"1.0", "2.0"}))
    with pytest.raises(InvalidRegistration, match="supported: 1.0"):
        registration(contract_versions=frozenset({"2.0"}))
