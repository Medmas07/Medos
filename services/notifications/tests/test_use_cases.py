"""Application use cases tests."""

from datetime import datetime, timezone

from adapters.outbound.channel_providers import InAppDeliveryProvider, PushNotificationProvider
from adapters.outbound.in_memory_store import InMemoryNotificationStore
from application.use_cases import (
    GetNotificationEventStatusUseCase,
    IngestNotificationEventUseCase,
    ListRecipientNotificationsUseCase,
)
from domain.models import (
    Channel,
    DeliveryStatus,
    NotificationCategory,
    NotificationEvent,
    NotificationPayload,
    OverallEventStatus,
    Priority,
    ReceiptStatus,
    RecipientPreference,
    RecipientRole,
)


def make_event(
    event_id: str = "evt-01",
    recipient: str = "pat-a",
    category: NotificationCategory = NotificationCategory.ACCESS_GRANTED,
    channels: list[Channel] | None = None,
) -> NotificationEvent:
    payload = NotificationPayload(
        notification_id=f"notif-{event_id}",
        recipient_ref=recipient,
        recipient_role=RecipientRole.PATIENT,
        category=category,
        priority=Priority.NORMAL,
        title="Titre de test",
        body="Corps du message de notification.",
        channels=channels or [Channel.IN_APP, Channel.PUSH],
        fictional=True,
    )
    return NotificationEvent(
        event_id=event_id,
        event_type=f"notification.{category.value}",
        occurred_at=datetime.now(timezone.utc),
        source="hospital-node-a",
        schema_version="1.0.0",
        payload=payload,
    )


def test_ingest_event_success_creates_receipt_and_deliveries():
    store = InMemoryNotificationStore()
    providers = {
        Channel.IN_APP: InAppDeliveryProvider(),
        Channel.PUSH: PushNotificationProvider(),
    }
    use_case = IngestNotificationEventUseCase(
        store=store, preference_store=store, providers=providers
    )

    event = make_event(event_id="evt-100", recipient="pat-a")
    receipt = use_case.execute(event)

    assert receipt.event_id == "evt-100"
    assert receipt.status == ReceiptStatus.QUEUED
    assert receipt.recipient_ref == "pat-a"

    saved_event = store.get_event("evt-100")
    assert saved_event is not None
    assert saved_event.payload.title == "Titre de test"

    deliveries = store.get_deliveries("evt-100")
    assert len(deliveries) == 2
    assert all(d.status == DeliveryStatus.DELIVERED for d in deliveries)


def test_ingest_event_suppressed_by_recipient_preference():
    store = InMemoryNotificationStore()
    # Recipient mutes request_status notifications
    store.set_preference(
        RecipientPreference(
            recipient_ref="pat-b",
            enabled_channels=[Channel.IN_APP],
            muted_categories=[NotificationCategory.REQUEST_STATUS],
        )
    )
    providers = {Channel.IN_APP: InAppDeliveryProvider()}
    use_case = IngestNotificationEventUseCase(
        store=store, preference_store=store, providers=providers
    )

    event = make_event(
        event_id="evt-muted",
        recipient="pat-b",
        category=NotificationCategory.REQUEST_STATUS,
        channels=[Channel.IN_APP],
    )
    receipt = use_case.execute(event)
    assert receipt.event_id == "evt-muted"

    deliveries = store.get_deliveries("evt-muted")
    assert len(deliveries) == 1
    assert deliveries[0].status == DeliveryStatus.SUPPRESSED
    assert deliveries[0].failure_reason == "suppressed_by_recipient_preference"


def test_get_event_status_returns_processed():
    store = InMemoryNotificationStore()
    providers = {Channel.IN_APP: InAppDeliveryProvider()}
    ingest_use_case = IngestNotificationEventUseCase(
        store=store, preference_store=store, providers=providers
    )
    status_use_case = GetNotificationEventStatusUseCase(store=store)

    event = make_event(event_id="evt-status-test", channels=[Channel.IN_APP])
    ingest_use_case.execute(event)

    status_dto = status_use_case.execute("evt-status-test")
    assert status_dto is not None
    assert status_dto.event_id == "evt-status-test"
    assert status_dto.status == OverallEventStatus.PROCESSED
    assert len(status_dto.deliveries) == 1
    assert status_dto.deliveries[0].status == DeliveryStatus.DELIVERED


def test_get_event_status_nonexistent_returns_none():
    store = InMemoryNotificationStore()
    status_use_case = GetNotificationEventStatusUseCase(store=store)
    assert status_use_case.execute("nonexistent-evt") is None


def test_list_recipient_notifications_ordered_newest_first():
    store = InMemoryNotificationStore()
    providers = {Channel.IN_APP: InAppDeliveryProvider()}
    ingest_use_case = IngestNotificationEventUseCase(
        store=store, preference_store=store, providers=providers
    )
    list_use_case = ListRecipientNotificationsUseCase(store=store)

    e1 = make_event(event_id="evt-older", recipient="usr-target")
    e2 = make_event(event_id="evt-newer", recipient="usr-target")

    ingest_use_case.execute(e1)
    ingest_use_case.execute(e2)

    results = list_use_case.execute("usr-target")
    assert len(results) == 2
    assert results[0].occurred_at >= results[1].occurred_at
