"""Outbound delivery channel adapters."""

from datetime import datetime, timezone

from application.ports import DeliveryProviderPort
from domain.models import (
    Channel,
    ChannelDeliveryRecord,
    DeliveryStatus,
    NotificationPayload,
)


class InAppDeliveryProvider(DeliveryProviderPort):
    """In-app delivery provider. Directly records successful in-app readiness."""

    @property
    def channel(self) -> Channel:
        return Channel.IN_APP

    def deliver(
        self, recipient_ref: str, payload: NotificationPayload
    ) -> ChannelDeliveryRecord:
        return ChannelDeliveryRecord(
            channel=Channel.IN_APP,
            status=DeliveryStatus.DELIVERED,
            dispatched_at=datetime.now(timezone.utc),
        )


class EmailNotificationProvider(DeliveryProviderPort):
    """Email delivery provider adapter."""

    @property
    def channel(self) -> Channel:
        return Channel.EMAIL

    def deliver(
        self, recipient_ref: str, payload: NotificationPayload
    ) -> ChannelDeliveryRecord:
        return ChannelDeliveryRecord(
            channel=Channel.EMAIL,
            status=DeliveryStatus.DELIVERED,
            dispatched_at=datetime.now(timezone.utc),
        )


class SmsNotificationProvider(DeliveryProviderPort):
    """SMS delivery provider adapter."""

    @property
    def channel(self) -> Channel:
        return Channel.SMS

    def deliver(
        self, recipient_ref: str, payload: NotificationPayload
    ) -> ChannelDeliveryRecord:
        return ChannelDeliveryRecord(
            channel=Channel.SMS,
            status=DeliveryStatus.DELIVERED,
            dispatched_at=datetime.now(timezone.utc),
        )
