"""Notification Service (HC-202 D2) composition root."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.inbound.http.clinician_alerts import create_clinician_alerts_router
from adapters.inbound.http.health import create_health_router
from adapters.inbound.http.router import create_router
from adapters.outbound.channel_providers import (
    EmailNotificationProvider,
    InAppDeliveryProvider,
    PushNotificationProvider,
    SmsNotificationProvider,
)
from adapters.outbound.in_memory_store import InMemoryNotificationStore
from application.use_cases import (
    GetNotificationEventStatusUseCase,
    IngestNotificationEventUseCase,
    ListClinicianAlertsUseCase,
    ListRecipientNotificationsUseCase,
)
from domain.models import Channel
from infrastructure.config import Settings

settings = Settings.from_environment()

store = InMemoryNotificationStore()
if settings.seed_demo_data and settings.fixtures_path:
    store.seed_from_fixtures(settings.fixtures_path)

providers = {
    Channel.IN_APP: InAppDeliveryProvider(),
    Channel.PUSH: PushNotificationProvider(),
    Channel.EMAIL: EmailNotificationProvider(),
    Channel.SMS: SmsNotificationProvider(),
}

ingest_use_case = IngestNotificationEventUseCase(
    store=store,
    preference_store=store,
    providers=providers,
)
get_status_use_case = GetNotificationEventStatusUseCase(store=store)
list_recipient_use_case = ListRecipientNotificationsUseCase(store=store)
list_clinician_alerts_use_case = ListClinicianAlertsUseCase(store=store)

app = FastAPI(
    title="Notification Service",
    version="0.2.0",
    description=(
        "HC-202 Notification Service (D2). Ingests asynchronous notification events "
        "conforming to contracts/events/notification-event.v1.yaml, manages recipient "
        "preferences, routes to delivery adapters, and tracks delivery status. "
        "Strictly decoupled from clinical database and autonomous AI authority."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_health_router())
app.include_router(
    create_router(
        ingest_use_case=ingest_use_case,
        get_status_use_case=get_status_use_case,
        list_recipient_use_case=list_recipient_use_case,
    )
)
app.include_router(
    create_clinician_alerts_router(
        list_alerts_use_case=list_clinician_alerts_use_case,
    )
)


def create_app() -> FastAPI:
    return app
