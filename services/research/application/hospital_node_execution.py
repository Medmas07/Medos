"""Application-owned port for the Hospital Node execution boundary."""

from typing import Protocol


class HospitalNodeExecutionPort(Protocol):
    def submit(self, node_ref: str, request: dict) -> dict: ...

    def read(self, node_ref: str, execution_ref: str) -> dict: ...
