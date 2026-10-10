"""HttpPatientGrantDirectory against patient-access-grants.v1.yaml, with no network.

The Hospital Node answers are the contract's own example, through httpx.MockTransport.
"""

import json

import httpx
import pytest

from adapters.outbound.http_patient_grants import (
    HttpPatientGrantDirectory,
    load_hospital_nodes,
)
from adapters.outbound.in_memory_hospital_applications import SeedError
from application.synchronization import GrantsUnavailable
from domain.synchronization import ScopeItem
from main import DEFAULT_HOSPITAL_NODES
from tests.test_synchronization_http import load

GRANTS = load("api/patient-access/patient-access-grants.v1.yaml")
# Patient A's grants as Hospital A lists them; re-labelled for Hospital B below.
PATIENT_A = GRANTS["paths"]["/v1/patients/{patient_ref}/access-grants"]["get"][
    "responses"
]["200"]["content"]["application/json"]["examples"]["patientA"]["value"]
ON_B = {
    **PATIENT_A,
    "node_ref": "node-hospital-b",
    "organization_ref": "org-hospital-b",
}
NODES = {"org-hospital-b": "http://hospital-b.test"}


def directory(answer) -> tuple[HttpPatientGrantDirectory, list[httpx.Request]]:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answer(request)

    return HttpPatientGrantDirectory(
        NODES, transport=httpx.MockTransport(handler)
    ), seen


def test_reads_the_grant_from_the_holders_node():
    grants, seen = directory(lambda r: httpx.Response(200, json=ON_B))

    grant = grants.grant("org-hospital-b", "pat-a", "grant-a-drx")

    assert str(seen[0].url) == "http://hospital-b.test/v1/patients/pat-a/access-grants"
    assert seen[0].method == "GET"
    assert grant.scope == set(ScopeItem)
    assert not grant.revoked
    assert grants.grant("org-hospital-b", "pat-a", "grant-unknown") is None
    assert (grants.mode, grants.mocked) == ("http", False)


def test_a_revocation_recorded_by_the_node_is_seen():
    revoked = json.loads(json.dumps(ON_B))
    revoked["grants"][0].update(
        status="revoked", revoked_at="2026-10-10T10:00:00+01:00"
    )
    grants, _ = directory(lambda r: httpx.Response(200, json=revoked))

    assert grants.grant("org-hospital-b", "pat-a", "grant-a-drx").revoked


def wrong(**changes):
    return lambda r: httpx.Response(200, json={**ON_B, **changes})


def foreign_grant(r):
    body = json.loads(json.dumps(ON_B))
    body["grants"][0]["patient_ref"] = "pat-b"
    return httpx.Response(200, json=body)


def naive_expiry(r):
    body = json.loads(json.dumps(ON_B))
    body["grants"][0]["expires_at"] = "2026-10-24T09:00:00"
    return httpx.Response(200, json=body)


def refused(r):
    raise httpx.ConnectError("connection refused", request=r)


@pytest.mark.parametrize(
    "answer, reason",
    [
        (refused, "could not be reached"),
        (lambda r: httpx.Response(503), "answered HTTP 503"),
        (lambda r: httpx.Response(200, text="not json"), "outside the access grants"),
        (wrong(organization_ref="org-hospital-a"), "outside the access grants"),
        (wrong(patient_ref="pat-b"), "outside the access grants"),
        (wrong(grants=None), "outside the access grants"),
        (foreign_grant, "outside the access grants"),
        (naive_expiry, "outside the access grants"),
    ],
)
def test_a_node_that_cannot_answer_within_the_contract_is_unavailable(answer, reason):
    grants, _ = directory(answer)

    with pytest.raises(GrantsUnavailable, match=reason):
        grants.grant("org-hospital-b", "pat-a", "grant-a-drx")


def test_an_organization_without_a_configured_node_is_unavailable():
    grants, seen = directory(lambda r: httpx.Response(200, json=ON_B))

    with pytest.raises(GrantsUnavailable, match="no Hospital Node is configured"):
        grants.grant("org-hospital-c", "pat-a", "grant-a-drx")
    assert seen == []


def test_loads_the_demo_node_directory():
    assert load_hospital_nodes(DEFAULT_HOSPITAL_NODES) == {
        "org-hospital-a": "http://127.0.0.1:8101",
        "org-hospital-b": "http://127.0.0.1:8102",
        "org-private-practice": "http://127.0.0.1:8104",
    }


@pytest.mark.parametrize(
    "content",
    [
        {"nodes": []},  # not marked fictional
        {"fictional": True},
        {
            "fictional": True,
            "nodes": [{"organization_ref": "org a", "base_url": "http://x"}],
        },
        {
            "fictional": True,
            "nodes": [{"organization_ref": "org-a", "base_url": "ftp://x"}],
        },
        {
            "fictional": True,
            "nodes": [
                {"organization_ref": "org-a", "base_url": "http://x"},
                {"organization_ref": "org-a", "base_url": "http://y"},
            ],
        },
    ],
)
def test_refuses_an_invalid_node_directory(tmp_path, content):
    path = tmp_path / "nodes.json"
    path.write_text(json.dumps(content), encoding="utf-8")

    with pytest.raises(SeedError):
        load_hospital_nodes(path)
