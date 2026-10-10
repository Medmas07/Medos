"""Environment-owned configuration for external trust boundaries."""

import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    governance_url: str | None
    node_urls: dict[str, str]
    request_timeout_seconds: float = 5.0

    @classmethod
    def from_environment(cls) -> "Settings":
        raw_nodes = os.getenv("RESEARCH_NODE_ENDPOINTS", "{}")
        try:
            node_urls = json.loads(raw_nodes)
        except json.JSONDecodeError as error:
            raise ValueError("RESEARCH_NODE_ENDPOINTS must be a JSON object") from error
        if not isinstance(node_urls, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in node_urls.items()
        ):
            raise ValueError(
                "RESEARCH_NODE_ENDPOINTS must map organization refs to URLs"
            )
        timeout = float(os.getenv("RESEARCH_HTTP_TIMEOUT_SECONDS", "5"))
        if timeout <= 0:
            raise ValueError("RESEARCH_HTTP_TIMEOUT_SECONDS must be positive")
        return cls(
            governance_url=os.getenv("RESEARCH_GOVERNANCE_URL"),
            node_urls=node_urls,
            request_timeout_seconds=timeout,
        )
