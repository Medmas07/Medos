"""In-memory push subscription store (HC-204). Lost on restart; persistence is OPEN."""

import threading

from domain.push import PushSubscription


class InMemoryPushSubscriptionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_recipient: dict[str, dict[str, PushSubscription]] = {}

    def save(self, subscription: PushSubscription) -> PushSubscription:
        with self._lock:
            self._by_recipient.setdefault(subscription.recipient_ref, {})[
                subscription.subscription_id
            ] = subscription
        return subscription

    def list_for_recipient(self, recipient_ref: str) -> list[PushSubscription]:
        with self._lock:
            return list(self._by_recipient.get(recipient_ref, {}).values())

    def remove(self, recipient_ref: str, subscription_id: str) -> bool:
        with self._lock:
            return (
                self._by_recipient.get(recipient_ref, {}).pop(subscription_id, None)
                is not None
            )
