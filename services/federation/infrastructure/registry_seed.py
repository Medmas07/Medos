"""Startup registrations, read from the JSON file named by FEDERATION_REGISTRY_SEED.

Each entry goes through the same NodeRegistry use case and validation as the registry
API. A seed that cannot be read or is invalid stops startup instead of being skipped.
"""

import json
import os
from pathlib import Path

from application.node_registry import NodeRegistry, RegistrationRequest

SEED_ENV = "FEDERATION_REGISTRY_SEED"


def seed_path_from_env() -> Path | None:
    value = os.environ.get(SEED_ENV)
    return Path(value) if value else None


def load_seed(registry: NodeRegistry, path: Path) -> int:
    for entry in json.loads(path.read_text())["nodes"]:
        registry.register(
            RegistrationRequest(
                node_ref=entry["node_ref"],
                organization_ref=entry["organization_ref"],
                base_url=entry["base_url"],
                contract_versions=frozenset(entry["contract_versions"]),
                approval_decision_ref=entry["approval_decision_ref"],
            )
        )
    return len(registry.list())
