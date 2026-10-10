"""Application ports defining boundaries for storage, delivery, and preferences."""

from typing import Protocol

from domain.models import (
    Channel,
    ChannelDeliveryRecord,
    NotificationEvent,
    NotificationEventReceipt,
    NotificationPayload,
    RecipientPreference,
)


class NotificationStorePort(Protocol):
    """Port for persisting and querying notification events and delivery status."""

    def save_event(self, event: NotificationEvent) -> None: ...

    def get_event(self, event_id: str) -> NotificationEvent | None: ...

    def save_receipt(self, receipt: NotificationEventReceipt) -> None: ...

    def get_receipt(self, receipt_id: str) -> NotificationEventReceipt | None: ...

    def save_deliveries(
        self, event_id: str, deliveries: list[ChannelDeliveryRecord]
    ) -> None: ...

    def get_deliveries(self, event_id: str) -> list[ChannelDeliveryRecord]: ...

    def list_events_for_recipient(
        self, recipient_ref: str
    ) -> list[NotificationEvent]: ...


class DeliveryProviderPort(Protocol):
    """Port for delivering notifications to concrete channels."""

    @property
    def channel(self) -> Channel: ...

    def deliver(
        self, recipient_ref: str, payload: NotificationPayload
    ) -> ChannelDeliveryRecord: ...


class PreferenceStorePort(Protocol):
    """Port for retrieving recipient routing and channel preferences."""

    def get_preference(self, recipient_ref: str) -> RecipientPreference | None: ...
