from dataclasses import dataclass

ADVISORY_NOTICE = (
    "AI Services runtime skeleton. No AI capability is implemented. "
    "Any future AI output is advisory and requires review by an accountable human."
)


@dataclass(frozen=True)
class ServiceStatus:
    service: str
    version: str
    capabilities: tuple[str, ...]
    notice: str = ADVISORY_NOTICE
