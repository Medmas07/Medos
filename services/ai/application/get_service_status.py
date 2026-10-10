from domain.service_status import ServiceStatus

SERVICE_NAME = "ai-services"
SERVICE_VERSION = "0.1.0"


def get_service_status() -> ServiceStatus:
    # No capability exists yet; HC-153 to HC-157 add them behind provider-neutral ports.
    return ServiceStatus(service=SERVICE_NAME, version=SERVICE_VERSION, capabilities=())
