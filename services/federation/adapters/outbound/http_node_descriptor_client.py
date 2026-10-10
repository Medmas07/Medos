import httpx

from adapters.outbound.hospital_node_contract import descriptor_from_wire
from application.discover_capabilities import (
    InvalidDescriptor,
    NodeUnreachable,
    NoFederationInterface,
)
from domain.node_capabilities import NodeDescriptor

DESCRIPTOR_PATH = "/v1/federation/node"


class HttpNodeDescriptorClient:
    """NodeDescriptorClient over HTTP. Calls only the node's own base URL from the registry."""

    def __init__(self, timeout_seconds: float = 2.0, transport=None) -> None:
        self._timeout = timeout_seconds
        self._transport = transport

    def describe(self, base_url: str) -> NodeDescriptor:
        url = base_url.rstrip("/") + DESCRIPTOR_PATH
        try:
            with httpx.Client(
                timeout=self._timeout, follow_redirects=False, transport=self._transport
            ) as client:
                response = client.get(url, headers={"accept": "application/json"})
        except httpx.TimeoutException as error:
            raise NodeUnreachable(f"No answer from {url} in time.") from error
        except httpx.TransportError as error:
            raise NodeUnreachable(f"Cannot connect to {url}.") from error
        if response.status_code in (404, 405):
            raise NoFederationInterface(
                f"{url} answered {response.status_code}: the node does not serve the "
                "Federation interface."
            )
        if response.status_code != 200:
            raise InvalidDescriptor(f"{url} answered HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as error:
            raise InvalidDescriptor(f"{url} did not answer JSON.") from error
        return descriptor_from_wire(payload)
