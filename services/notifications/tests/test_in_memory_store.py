"""Tests for InMemoryNotificationStore adapter."""

from datetime import datetime, timezone
from pathlib import Path

from adapters.outbound.in_memory_store import InMemoryNotificationStore
from domain.models import (
    Channel,
    NotificationCategory,
    NotificationEvent,
    NotificationPayload,
    Priority,
    RecipientRole,
)


def test_in_memory_store_save_and_retrieve():
    store = InMemoryNotificationStore()
    payload = NotificationPayload(
        notification_id="notif-1",
        recipient_ref="pat-a",
        recipient_role=RecipientRole.PATIENT,
        category=NotificationCategory.ACCESS_GRANTED,
        priority=Priority.NORMAL,
        title="Titre",
        body="Corps",
        channels=[Channel.IN_APP],
    )
    event = NotificationEvent(
        event_id="evt-1",
        event_type="notification.access_granted",
        occurred_at=datetime.now(timezone.utc),
        source="hospital-node-a",
        schema_version="1.0.0",
        payload=payload,
    )
    store.save_event(event)

    fetched = store.get_event("evt-1")
    assert fetched is not None
    assert fetched.payload.recipient_ref == "pat-a"

    user_events = store.list_events_for_recipient("pat-a")
    assert len(user_events) == 1


def test_seed_from_canonical_fixtures():
    store = InMemoryNotificationStore()
    repo_root = Path(__file__).resolve().parents[3]
    fixtures_path = repo_root / "demo-data" / "notifications.json"

    count = store.seed_from_fixtures(fixtures_path)
    assert count > 0

    # usr-olfa has notifications in demo-data/notifications.json (notif-006, notif-007)
    olfa_events = store.list_events_for_recipient("usr-olfa")
    assert len(olfa_events) >= 2
