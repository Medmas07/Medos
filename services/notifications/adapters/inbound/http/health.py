"""Health endpoint for Notification Service."""

from fastapi import APIRouter


def create_health_router(service_name: str = "notification-service") -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict:
        return {
            "status": "ready",
            "service": service_name,
            "depth": "D2",
            "mocked": False,
            "capabilities": [
                "notification_event_intake",
                "recipient_routing",
                "in_app_delivery",
                "delivery_tracking",
            ],
            "channels": ["in_app", "push", "email", "sms"],
            "boundaries": {
                "clinical_data_access": "denied_by_design",
                "sql_access": "forbidden",
                "autonomous_ai_authority": "denied_by_design",
            },
        }

    return router
