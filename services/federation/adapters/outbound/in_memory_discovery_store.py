from domain.node_capabilities import DiscoveryResult


class InMemoryDiscoveryStore:
    """Latest discovery result per node, kept in this process and lost on restart."""

    def __init__(self) -> None:
        self._results: dict[str, DiscoveryResult] = {}

    def get(self, node_ref: str) -> DiscoveryResult | None:
        return self._results.get(node_ref)

    def save(self, result: DiscoveryResult) -> None:
        self._results[result.node_ref] = result
