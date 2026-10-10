from dataclasses import dataclass

ADVISORY_NOTICE = (
    "Capabilities marked :model call a language model; capabilities marked "
    ":mocked return deterministic fictional fixtures. Any AI output is advisory "
    "and requires review by an accountable human."
)


@dataclass(frozen=True)
class ServiceStatus:
    service: str
    version: str
    capabilities: tuple[str, ...]
    notice: str = ADVISORY_NOTICE
