"""Mobile push delivery (HC-204): subscriptions, and push as a delivery channel.

A device registers the endpoint its UnifiedPush distributor gave it. On a notification
with the push channel, each of the recipient's subscriptions gets the minimal push
message of domain/push.py, encrypted to its keys by the PushGatewayPort.

An accepted push is `sent`, not `delivered`: the push server took it, and nothing here
confirms that the device received it. A push server saying the endpoint no longer
exists (404) removes the subscription.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol
from urllib.parse import urlsplit

from domain.models import (
    Channel,
    ChannelDeliveryRecord,
    DeliveryStatus,
    NotificationPayload,
)
from domain.push import URGENCY, PushSubscription, push_message
from domain.validation import DomainValidationError


class PushOutcome(Enum):
    ACCEPTED = "accepted"
    GONE = "gone"  # 404: the endpoint no longer exists
    RATE_LIMITED = "rate_limited"  # 429
    REJECTED = "rejected"  # any other answer, or no answer


@dataclass(frozen=True)
class PushResult:
    outcome: PushOutcome
    detail: str = ""


class PushSubscriptionStorePort(Protocol):
    def save(self, subscription: PushSubscription) -> PushSubscription: ...

    def list_for_recipient(self, recipient_ref: str) -> list[PushSubscription]: ...

    def remove(self, recipient_ref: str, subscription_id: str) -> bool: ...


class PushGatewayPort(Protocol):
    def send(
        self, subscription: PushSubscription, message: bytes, urgency: str
    ) -> PushResult: ...


class PushEndpointNotAllowed(DomainValidationError):
    """The endpoint's host is not a configured push server."""


class RegisterPushSubscription:
    """Records a device's subscription; the same endpoint again replaces its keys."""

    def __init__(
        self,
        store: PushSubscriptionStorePort,
        allowed_hosts: frozenset[str],
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        new_id: Callable[[], str] = lambda: f"psub-{uuid.uuid4().hex[:12]}",
    ) -> None:
        self._store = store
        self._allowed_hosts = allowed_hosts
        self._clock = clock
        self._new_id = new_id

    def execute(
        self, recipient_ref: str, endpoint: str, p256dh: bytes, auth: bytes
    ) -> PushSubscription:
        # The service will POST to this URL: only configured push servers (no SSRF).
        host = (urlsplit(endpoint).hostname or "").lower()
        if host not in self._allowed_hosts:
            raise PushEndpointNotAllowed(
                f"endpoint host {host!r} is not an allowed push server."
            )
        existing = next(
            (
                s
                for s in self._store.list_for_recipient(recipient_ref)
                if s.endpoint == endpoint
            ),
            None,
        )
        subscription = PushSubscription(
            subscription_id=existing.subscription_id if existing else self._new_id(),
            recipient_ref=recipient_ref,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            registered_at=self._clock(),
        )
        return self._store.save(subscription)


class UnregisterPushSubscription:
    def __init__(self, store: PushSubscriptionStorePort) -> None:
        self._store = store

    def execute(self, recipient_ref: str, subscription_id: str) -> bool:
        return self._store.remove(recipient_ref, subscription_id)


class ListPushSubscriptions:
    def __init__(self, store: PushSubscriptionStorePort) -> None:
        self._store = store

    def execute(self, recipient_ref: str) -> list[PushSubscription]:
        return self._store.list_for_recipient(recipient_ref)


class PushDeliveryProvider:
    """The push channel's DeliveryProviderPort: real Web Push to registered devices."""

    def __init__(
        self,
        store: PushSubscriptionStorePort,
        gateway: PushGatewayPort,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._store = store
        self._gateway = gateway
        self._clock = clock

    @property
    def channel(self) -> Channel:
        return Channel.PUSH

    def deliver(
        self, recipient_ref: str, payload: NotificationPayload
    ) -> ChannelDeliveryRecord:
        now = self._clock()
        subscriptions = self._store.list_for_recipient(recipient_ref)
        if not subscriptions:
            return ChannelDeliveryRecord(
                channel=Channel.PUSH,
                status=DeliveryStatus.FAILED,
                dispatched_at=now,
                failure_reason="push_subscription_not_registered",
            )
        message = push_message(payload)
        outcomes = []
        for subscription in subscriptions:
            result = self._gateway.send(
                subscription, message, URGENCY[payload.priority]
            )
            if result.outcome is PushOutcome.GONE:
                self._store.remove(recipient_ref, subscription.subscription_id)
            outcomes.append(result.outcome)
        if PushOutcome.ACCEPTED in outcomes:
            return ChannelDeliveryRecord(
                channel=Channel.PUSH, status=DeliveryStatus.SENT, dispatched_at=now
            )
        reason = {
            PushOutcome.GONE: "push_endpoint_gone",
            PushOutcome.RATE_LIMITED: "push_rate_limited",
            PushOutcome.REJECTED: "push_server_rejected",
        }
        return ChannelDeliveryRecord(
            channel=Channel.PUSH,
            status=DeliveryStatus.FAILED,
            dispatched_at=now,
            failure_reason="+".join(sorted({reason[o] for o in outcomes})),
        )
