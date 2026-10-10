from dataclasses import dataclass

ADVISORY_NOTICE = (
    "No real AI capability is implemented; capabilities marked :mocked return "
    "deterministic fictional fixtures. Any AI output is advisory and requires "
    "review by an accountable human."
)


@dataclass(frozen=True)
class ServiceStatus:
    service: str
    version: str
    capabilities: tuple[str, ...]
    notice: str = ADVISORY_NOTICE
