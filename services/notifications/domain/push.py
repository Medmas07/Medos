"""Mobile push subscriptions and push messages (HC-204, UnifiedPush / Web Push).

A device registers a push subscription: the endpoint its push distributor gave it
(a capability URL on a push server) and the keys the message must be encrypted to
(RFC 8291). The push message itself is minimal: it never carries the notification's
title or body, which may hold clinical wording and could show on a lock screen. It says
only that something new is waiting, by category, and which notification to open in the
app.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from domain.models import NotificationCategory, NotificationPayload, Priority
from domain.validation import DomainValidationError

# RFC 8291 bounds: the encrypted body is at most 4096 bytes; its header and tag take
# 86 + 16 bytes, and the record delimiter one more.
MAX_PUSH_PLAINTEXT = 4096 - 86 - 16 - 1

GENERIC_TITLES = {
    NotificationCategory.ALERT: "Nouvelle alerte à consulter",
    NotificationCategory.ACCESS_GRANTED: "Mise à jour de vos accès",
    NotificationCategory.DELEGATION_GRANTED: "Mise à jour de vos accès",
    NotificationCategory.NEW_RECORD: "Nouvel élément dans votre dossier",
    NotificationCategory.REQUEST_STATUS: "Mise à jour d'une demande",
    NotificationCategory.REVIEW_REQUESTED: "Nouvelle revue demandée",
    NotificationCategory.JOB_COMPLETED: "Traitement terminé",
}
DEFAULT_TITLE = "Nouvelle notification"


@dataclass(frozen=True)
class PushSubscription:
    subscription_id: str
    recipient_ref: str
    endpoint: str
    # RFC 8291 user agent keys: an uncompressed P-256 point and a 16-byte secret.
    p256dh: bytes
    auth: bytes
    registered_at: datetime

    def __post_init__(self) -> None:
        parts = urlsplit(self.endpoint)
        if parts.scheme != "https" or not parts.hostname:
            raise DomainValidationError("endpoint must be an https URL.")
        if parts.username or parts.password:
            raise DomainValidationError("endpoint must not carry credentials.")
        if len(self.p256dh) != 65 or self.p256dh[0] != 0x04:
            raise DomainValidationError(
                "keys.p256dh must be an uncompressed P-256 public key (65 bytes)."
            )
        if len(self.auth) != 16:
            raise DomainValidationError("keys.auth must be 16 bytes.")
        if not self.recipient_ref.strip():
            raise DomainValidationError("recipient_ref must not be empty.")

    @property
    def endpoint_host(self) -> str:
        return urlsplit(self.endpoint).hostname or ""


def push_message(payload: NotificationPayload) -> bytes:
    """The plaintext of a push message: no clinical text, only what to open."""
    message = json.dumps(
        {
            "v": 1,
            "notification_id": payload.notification_id,
            "category": payload.category.value,
            "priority": payload.priority.value,
            "title": GENERIC_TITLES.get(payload.category, DEFAULT_TITLE),
            "fictional": payload.fictional,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(message) > MAX_PUSH_PLAINTEXT:
        raise DomainValidationError("push message exceeds the Web Push size limit.")
    return message


# RFC 8030 Urgency header values; urgent maps to the highest one.
URGENCY = {
    Priority.LOW: "low",
    Priority.NORMAL: "normal",
    Priority.HIGH: "high",
    Priority.URGENT: "high",
}
