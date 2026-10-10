"""Thread-safe in-memory notification and preference store."""

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock

from application.ports import NotificationStorePort, PreferenceStorePort
from domain.models import (
    Channel,
    ChannelDeliveryRecord,
    DeliveryStatus,
    NotificationCategory,
    NotificationEvent,
    NotificationEventReceipt,
    NotificationPayload,
    Priority,
    RecipientPreference,
    RecipientRole,
    RelatedResource,
)


class InMemoryNotificationStore(NotificationStorePort, PreferenceStorePort):
    """Stores events, deliveries, receipts, and preferences in memory."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: dict[str, NotificationEvent] = {}
        self._receipts: dict[str, NotificationEventReceipt] = {}
        self._deliveries: dict[str, list[ChannelDeliveryRecord]] = {}
        self._preferences: dict[str, RecipientPreference] = {}

    def save_event(self, event: NotificationEvent) -> None:
        with self._lock:
            self._events[event.event_id] = event

    def get_event(self, event_id: str) -> NotificationEvent | None:
        with self._lock:
            return self._events.get(event_id)

    def save_receipt(self, receipt: NotificationEventReceipt) -> None:
        with self._lock:
            self._receipts[receipt.receipt_id] = receipt

    def get_receipt(self, receipt_id: str) -> NotificationEventReceipt | None:
        with self._lock:
            return self._receipts.get(receipt_id)

    def save_deliveries(
        self, event_id: str, deliveries: list[ChannelDeliveryRecord]
    ) -> None:
        with self._lock:
            self._deliveries[event_id] = list(deliveries)

    def get_deliveries(self, event_id: str) -> list[ChannelDeliveryRecord]:
        with self._lock:
            return list(self._deliveries.get(event_id, []))

    def list_events_for_recipient(
        self, recipient_ref: str
    ) -> list[NotificationEvent]:
        with self._lock:
            return [
                e
                for e in self._events.values()
                if e.payload.recipient_ref == recipient_ref
            ]

    def set_preference(self, preference: RecipientPreference) -> None:
        with self._lock:
            self._preferences[preference.recipient_ref] = preference

    def get_preference(self, recipient_ref: str) -> RecipientPreference | None:
        with self._lock:
            return self._preferences.get(recipient_ref)

    def seed_from_fixtures(self, fixtures_path: Path) -> int:
        """Seeds the in-memory store with canonical demo notifications."""
        if not fixtures_path.exists():
            return 0

        with fixtures_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        now = datetime.now(timezone.utc)
        for item in data.get("notifications", []):
            try:
                # Map demo-data/notifications.json item to NotificationEvent
                category = NotificationCategory(item["type"])
                payload = NotificationPayload(
                    notification_id=item["id"],
                    recipient_ref=item["recipientId"],
                    recipient_role=RecipientRole.PATIENT
                    if item["recipientId"].startswith("pat-")
                    else RecipientRole.CLINICIAN
                    if item["recipientId"].startswith("clin-")
                    else RecipientRole.RELATIVE
                    if item["recipientId"].startswith("rel-")
                    else RecipientRole.GOVERNANCE_REVIEWER
                    if item["recipientId"] == "usr-olfa"
                    else RecipientRole.RESEARCHER
                    if item["recipientId"] == "usr-aymen"
                    else RecipientRole.HOSPITAL_ADMIN,
                    category=category,
                    priority=Priority.HIGH
                    if category == NotificationCategory.ALERT
                    else Priority.NORMAL,
                    title=item["title"],
                    body=item["body"],
                    channels=[Channel.IN_APP],
                    related_resource=RelatedResource(
                        resource_type="domain_ref",
                        resource_ref=item.get("relatedId", ""),
                    )
                    if item.get("relatedId")
                    else None,
                    fictional=True,
                )
                event = NotificationEvent(
                    event_id=f"evt-{item['id']}",
                    event_type=f"notification.{category.value}",
                    occurred_at=datetime.fromisoformat(item["createdAt"]),
                    source="canonical-fixtures",
                    schema_version="1.0.0",
                    payload=payload,
                )
                self.save_event(event)
                self.save_deliveries(
                    event.event_id,
                    [
                        ChannelDeliveryRecord(
                            channel=Channel.IN_APP,
                            status=DeliveryStatus.DELIVERED,
                            dispatched_at=now,
                        )
                    ],
                )
                count += 1
            except Exception:
                continue

        return count
