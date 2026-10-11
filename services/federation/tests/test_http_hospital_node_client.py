import json
from dataclasses import replace

import httpx
import pytest

from adapters.outbound.http_hospital_node_client import HttpHospitalNodeClient
from adapters.outbound.in_memory_registration_store import InMemoryRegistrationStore
from application.federate_patient_query import (
    NodeDenied,
    NodeTemporarilyUnavailable,
    NodeTimeout,
    NodeUnavailable,
)
from application.node_registry import NodeRegistry
from infrastructure.registry_seed import load_seed
from tests.conftest import DEMO_NOW, DEMO_SEED, contract, validator
from tests.test_node_answer_parsing import B, FOUND, QUERY

request_schema = validator(
    contract("hospital-node-federation.v1.yaml"), "NodeQueryRequest"
)


def client(handler, registry=None):
    if registry is None:
        registry = NodeRegistry(InMemoryRegistrationStore(), clock=lambda: DEMO_NOW)
        load_seed(registry, DEMO_SEED)
    return HttpHospitalNodeClient(registry, transport=httpx.MockTransport(handler))


def test_posts_the_contract_request_to_the_registered_url():
    seen = []

    def handler(request):
        seen.append((request.method, str(request.url), json.loads(request.content)))
        return httpx.Response(200, json=FOUND)

    answer = client(handler).query(B, QUERY)

    method, url, body = seen[0]
    assert (method, url) == ("POST", "http://localhost:8102/v1/federation/queries")
    assert request_schema.is_valid(body)
    assert body["query_id"] == QUERY.query_id
    assert [e.entry_ref for e in answer.entries] == ["med-b-leila-coagulix"]
    assert "signed_authorization" not in body


def test_passes_the_signed_authorization_on_unchanged():
    # HC-214: the token of the Governance Node's 1.2.0 example, as received.
    token = contract("sync-authorization-check.v1.yaml")["paths"][
        "/v1/synchronization-authorizations/{decision_ref}/checks"
    ]["post"]["responses"]["200"]["content"]["application/json"]["examples"][
        "authorizedSigned"
    ]["value"]["signed_authorization"]
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=FOUND)

    client(handler).query(B, replace(QUERY, signed_authorization=token))

    assert seen[0]["signed_authorization"] == token
    assert request_schema.is_valid(seen[0])


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(403, json={"code": "authorization_denied"}), NodeDenied),
        (httpx.Response(404), NodeUnavailable),
        (httpx.Response(503, json={"code": "node_unavailable"}), NodeUnavailable),
        (httpx.Response(500), NodeUnavailable),
        (
            httpx.Response(302, headers={"location": "http://elsewhere"}),
            NodeUnavailable,
        ),
        (httpx.Response(200, text="<html>"), NodeUnavailable),
    ],
    ids=[
        "denied",
        "no_endpoint",
        "node_unavailable",
        "server_error",
        "redirect",
        "not_json",
    ],
)
def test_status_codes_map_to_node_statuses(response, error):
    with pytest.raises(error):
        client(lambda request: response).query(B, QUERY)


@pytest.mark.parametrize(
    ("raised", "error"),
    [
        (httpx.ReadTimeout("slow"), NodeTimeout),
        (httpx.ConnectError("refused"), NodeUnavailable),
    ],
    ids=["timeout", "connect"],
)
def test_transport_failures(raised, error):
    def handler(request):
        raise raised

    with pytest.raises(error):
        client(handler).query(B, QUERY)


def test_a_deregistered_node_is_unavailable():
    empty = NodeRegistry(InMemoryRegistrationStore(), clock=lambda: DEMO_NOW)
    with pytest.raises(NodeUnavailable):
        client(lambda request: pytest.fail("must not be called"), empty).query(B, QUERY)


@pytest.mark.parametrize(
    ("respond", "transient"),
    [
        (lambda request: httpx.Response(503), True),
        (lambda request: (_ for _ in ()).throw(httpx.ConnectError("refused")), True),
        (lambda request: httpx.Response(404), False),
        (lambda request: httpx.Response(500), False),
    ],
    ids=["503", "connect", "404", "500"],
)
def test_only_passing_failures_are_marked_temporary(respond, transient):
    with pytest.raises(NodeUnavailable) as error:
        client(respond).query(B, QUERY)
    assert isinstance(error.value, NodeTemporarilyUnavailable) is transient
