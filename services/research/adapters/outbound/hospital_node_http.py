"""HTTP adapter for the versioned HC-180 Hospital Node contract."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HospitalNodeUnavailable(RuntimeError):
    pass


class HttpHospitalNodeExecutionAdapter:
    def __init__(self, node_urls: dict[str, str], timeout: float = 5.0) -> None:
        self.node_urls = node_urls
        self.timeout = timeout

    def _call(
        self, node_ref: str, method: str, path: str, body: dict | None = None
    ) -> dict:
        base_url = self.node_urls.get(node_ref)
        if not base_url:
            raise HospitalNodeUnavailable(f"node_not_configured:{node_ref}")
        payload = None if body is None else json.dumps(body).encode()
        request = Request(
            f"{base_url.rstrip('/')}{path}",
            data=payload,
            method=method,
            headers={"content-type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise HospitalNodeUnavailable(f"node_unavailable:{node_ref}") from exc

    def submit(self, node_ref: str, request: dict) -> dict:
        return self._call(node_ref, "POST", "/v1/research-executions", request)

    def read(self, node_ref: str, execution_ref: str) -> dict:
        return self._call(node_ref, "GET", f"/v1/research-executions/{execution_ref}")
