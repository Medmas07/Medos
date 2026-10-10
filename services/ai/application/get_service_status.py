from domain.service_status import ServiceStatus

SERVICE_NAME = "ai-services"
SERVICE_VERSION = "0.2.0"


def get_service_status() -> ServiceStatus:
    # Real capabilities arrive with HC-153 to HC-157 behind provider-neutral ports.
    return ServiceStatus(
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        capabilities=("clinical-extraction:mocked",),
    )
