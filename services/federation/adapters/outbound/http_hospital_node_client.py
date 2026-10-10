"""HospitalNodeClient over HTTP: POST /v1/federation/queries of hospital-node-federation.v1.

Each node is reached only at the base URL it has in the node registry (HC-142).
"""

import httpx

from adapters.outbound.hospital_node_contract import answer_from_wire, query_to_wire
from application.federate_patient_query import (
    NodeAnswer,
    NodeDenied,
    NodeTemporarilyUnavailable,
    NodeTimeout,
    NodeUnavailable,
)
from application.node_registry import NodeNotFound, NodeRegistry
from domain.federated_query import NodeQuery, NodeRef

QUERY_PATH = "/v1/federation/queries"


class HttpHospitalNodeClient:
    mocked = False

    def __init__(
        self, registry: NodeRegistry, timeout_seconds: float = 2.0, transport=None
    ) -> None:
        self._registry = registry
        self._timeout = timeout_seconds
        self._transport = transport

    def query(self, node: NodeRef, query: NodeQuery) -> NodeAnswer:
        try:
            registration = self._registry.get(node.node_ref)
        except NodeNotFound as error:
            raise NodeUnavailable(
                f"{node.node_ref} is no longer registered."
            ) from error
        url = registration.base_url.rstrip("/") + QUERY_PATH
        try:
            with httpx.Client(
                timeout=self._timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = client.post(url, json=query_to_wire(query))
        except httpx.TimeoutException as error:
            raise NodeTimeout(f"No answer from {url} in time.") from error
        except httpx.HTTPError as error:
            raise NodeTemporarilyUnavailable(f"Cannot connect to {url}.") from error
        if response.status_code == 403:
            raise NodeDenied(f"{node.node_ref} refused the authorization.")
        if response.status_code == 503:
            raise NodeTemporarilyUnavailable(f"{url} answered 503.")
        if response.status_code != 200:
            raise NodeUnavailable(f"{url} answered HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as error:
            raise NodeUnavailable(f"{url} did not answer JSON.") from error
        return answer_from_wire(node, query, payload)
