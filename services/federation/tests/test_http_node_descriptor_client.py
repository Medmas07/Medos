import copy

import httpx
import pytest

from adapters.outbound.http_node_descriptor_client import HttpNodeDescriptorClient
from application.discover_capabilities import (
    InvalidDescriptor,
    NodeUnreachable,
    NoFederationInterface,
)
from domain.federated_query import ScopeItem
from tests.conftest import contract

NODE_CONTRACT = contract("hospital-node-federation.v1.yaml")
HOSPITAL_B = NODE_CONTRACT["paths"]["/v1/federation/node"]["get"]["responses"]["200"][
    "content"
]["application/json"]["examples"]["hospitalB"]["value"]


def client(handler) -> HttpNodeDescriptorClient:
    return HttpNodeDescriptorClient(transport=httpx.MockTransport(handler))


def answering(status=200, **kwargs):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(status, **kwargs)

    return handler, seen


def test_parses_the_contract_example_from_the_descriptor_path():
    handler, seen = answering(json=HOSPITAL_B)
    descriptor = client(handler).describe("http://localhost:8102/")
    assert seen == ["http://localhost:8102/v1/federation/node"]
    assert descriptor.node_ref == "node-hospital-b"
    assert descriptor.supported_scopes == set(ScopeItem)
    assert descriptor.mocked is True


@pytest.mark.parametrize("status", [404, 405])
def test_missing_endpoint_means_no_federation_interface(status):
    with pytest.raises(NoFederationInterface):
        client(answering(status)[0]).describe("http://localhost:8101")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(302, headers={"location": "http://elsewhere"}),
        httpx.Response(200, text="<html>"),
        httpx.Response(200, json=HOSPITAL_B | {"patients": 12}),
        httpx.Response(200, json=HOSPITAL_B | {"supported_scopes": ["full_record"]}),
        httpx.Response(200, json=HOSPITAL_B | {"status": "unknown"}),
        httpx.Response(200, json=HOSPITAL_B | {"contract_versions": []}),
        httpx.Response(200, json=HOSPITAL_B | {"mocked": "yes"}),
        httpx.Response(200, json=HOSPITAL_B | {"node_ref": "Hôpital B"}),
        httpx.Response(200, json=[HOSPITAL_B]),
    ],
    ids=[
        "server_error",
        "redirect",
        "not_json",
        "extra_field",
        "unknown_scope",
        "unknown_status",
        "no_versions",
        "mocked_not_bool",
        "name_as_ref",
        "not_an_object",
    ],
)
def test_anything_outside_the_contract_is_invalid(response):
    with pytest.raises(InvalidDescriptor):
        client(lambda request: copy.deepcopy(response)).describe(
            "http://localhost:8102"
        )


@pytest.mark.parametrize(
    "error",
    [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")],
    ids=["connect", "timeout"],
)
def test_transport_failures_are_unreachable(error):
    def handler(request):
        raise error

    with pytest.raises(NodeUnreachable):
        client(handler).describe("http://localhost:8104")
