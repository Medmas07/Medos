from domain.node_registration import NodeRegistration


class InMemoryRegistrationStore:
    """RegistrationStore kept in this process. Registrations are lost on restart.

    Persistent storage is OPEN; until it is decided, nodes are re-registered at startup
    from a seed file (infrastructure/registry_seed.py) or through the registry API.
    """

    def __init__(self) -> None:
        self._registrations: dict[str, NodeRegistration] = {}

    def get(self, node_ref: str) -> NodeRegistration | None:
        return self._registrations.get(node_ref)

    def all(self) -> tuple[NodeRegistration, ...]:
        return tuple(self._registrations.values())

    def save(self, registration: NodeRegistration) -> None:
        self._registrations[registration.node_ref] = registration

    def remove(self, node_ref: str) -> None:
        self._registrations.pop(node_ref, None)
