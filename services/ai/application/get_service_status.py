from domain.service_status import ServiceStatus

SERVICE_NAME = "ai-services"
SERVICE_VERSION = "0.4.0"


def get_service_status(capabilities: tuple[str, ...]) -> ServiceStatus:
    return ServiceStatus(
        service=SERVICE_NAME, version=SERVICE_VERSION, capabilities=capabilities
    )
