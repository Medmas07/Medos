"""Application use cases implementing notification orchestration and routing."""

from datetime import datetime, timezone
import uuid

from application.ports import (
    DeliveryProviderPort,
    NotificationStorePort,
    PreferenceStorePort,
)
from domain.models import (
    Channel,
    ChannelDeliveryRecord,
    DeliveryStatus,
    NotificationEvent,
    NotificationEventReceipt,
    NotificationEventStatus,
    OverallEventStatus,
    ReceiptStatus,
)
from domain.validation import validate_notification_event


class IngestNotificationEventUseCase:
    """Orchestrates intake, validation, routing, and delivery of notification events."""

    def __init__(
        self,
        store: NotificationStorePort,
        preference_store: PreferenceStorePort,
        providers: dict[Channel, DeliveryProviderPort],
    ) -> None:
        self._store = store
        self._preference_store = preference_store
        self._providers = providers

    def execute(self, event: NotificationEvent) -> NotificationEventReceipt:
        # 1. Enforce domain invariants
        validate_notification_event(event)

        now = datetime.now(timezone.utc)
        receipt_id = f"rct-{uuid.uuid4().hex[:8]}"

        # 2. Check recipient preferences
        prefs = self._preference_store.get_preference(event.payload.recipient_ref)

        deliveries: list[ChannelDeliveryRecord] = []
        for channel in event.payload.channels:
            # Check if muted or disabled by preference
            is_muted = prefs and event.payload.category in prefs.muted_categories
            is_disabled = prefs and channel not in prefs.enabled_channels

            if is_muted or is_disabled:
                deliveries.append(
                    ChannelDeliveryRecord(
                        channel=channel,
                        status=DeliveryStatus.SUPPRESSED,
                        dispatched_at=now,
                        failure_reason="suppressed_by_recipient_preference"
                        if is_muted
                        else "channel_disabled_by_preference",
                    )
                )
                continue

            provider = self._providers.get(channel)
            if provider:
                record = provider.deliver(event.payload.recipient_ref, event.payload)
                deliveries.append(record)
            else:
                deliveries.append(
                    ChannelDeliveryRecord(
                        channel=channel,
                        status=DeliveryStatus.FAILED,
                        dispatched_at=now,
                        failure_reason=f"no_provider_for_channel_{channel.value}",
                    )
                )

        # 3. Persist state
        receipt = NotificationEventReceipt(
            receipt_id=receipt_id,
            event_id=event.event_id,
            status=ReceiptStatus.QUEUED,
            queued_at=now,
            recipient_ref=event.payload.recipient_ref,
            fictional=event.payload.fictional,
        )

        self._store.save_event(event)
        self._store.save_receipt(receipt)
        self._store.save_deliveries(event.event_id, deliveries)

        return receipt


class GetNotificationEventStatusUseCase:
    """Retrieves processing and delivery status for a published event."""

    def __init__(self, store: NotificationStorePort) -> None:
        self._store = store

    def execute(self, event_id: str) -> NotificationEventStatus | None:
        event = self._store.get_event(event_id)
        if not event:
            return None

        deliveries = self._store.get_deliveries(event_id)

        # Overall status calculation
        if not deliveries:
            status = OverallEventStatus.PENDING
        elif all(d.status == DeliveryStatus.FAILED for d in deliveries):
            status = OverallEventStatus.FAILED
        else:
            status = OverallEventStatus.PROCESSED

        return NotificationEventStatus(
            event_id=event.event_id,
            status=status,
            received_at=event.occurred_at,
            deliveries=deliveries,
            fictional=event.payload.fictional,
        )


class ListRecipientNotificationsUseCase:
    """Lists notifications received for a given recipient."""

    def __init__(self, store: NotificationStorePort) -> None:
        self._store = store

    def execute(self, recipient_ref: str) -> list[NotificationEvent]:
        events = self._store.list_events_for_recipient(recipient_ref)
        # Order newest first
        return sorted(events, key=lambda e: e.occurred_at, reverse=True)


class ListClinicianAlertsUseCase:
    """Lists advisory clinical alerts for a clinician recipient.

    HC-203: Real-time clinician alerts (D3).
    Returns alert-category notifications targeted at the given clinician,
    ordered by priority (urgent > high > normal > low) then newest first.
    All returned events carry advisory=True metadata — they are informational
    and must not be acted upon without human clinician review.
    """

    _PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

    def __init__(self, store: NotificationStorePort) -> None:
        self._store = store

    def execute(self, clinician_ref: str) -> list[NotificationEvent]:
        events = self._store.list_alerts_for_clinician(clinician_ref)
        return sorted(
            events,
            key=lambda e: (
                self._PRIORITY_ORDER.get(e.payload.priority.value, 99),
                # Negate timestamp for descending order
                -e.occurred_at.timestamp(),
            ),
        )
