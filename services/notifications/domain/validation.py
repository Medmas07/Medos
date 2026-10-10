"""Domain invariants and validation rules."""

import re
from domain.models import NotificationCategory, NotificationEvent


class DomainValidationError(Exception):
    """Raised when a notification violates core domain invariants."""


EVENT_TYPE_PATTERN = re.compile(r"^notification\.[a-z_]+$")


def validate_notification_event(event: NotificationEvent) -> None:
    """Enforces ecosystem boundaries and domain invariants on a notification event."""
    if not event.event_id or not event.event_id.strip():
        raise DomainValidationError("event_id must not be empty.")

    if not EVENT_TYPE_PATTERN.match(event.event_type):
        raise DomainValidationError(
            f"event_type '{event.event_type}' must follow pattern '^notification\\.[a-z_]+$'."
        )

    if not event.source or not event.source.strip():
        raise DomainValidationError("source must not be empty.")

    payload = event.payload
    if not payload.notification_id or not payload.notification_id.strip():
        raise DomainValidationError("payload.notification_id must not be empty.")

    if not payload.recipient_ref or not payload.recipient_ref.strip():
        raise DomainValidationError("payload.recipient_ref must not be empty.")

    if not payload.title or not payload.title.strip():
        raise DomainValidationError("payload.title must not be empty.")
    if len(payload.title) > 120:
        raise DomainValidationError("payload.title must not exceed 120 characters.")

    if not payload.body or not payload.body.strip():
        raise DomainValidationError("payload.body must not be empty.")
    if len(payload.body) > 500:
        raise DomainValidationError("payload.body must not exceed 500 characters.")

    if not payload.channels:
        raise DomainValidationError("payload.channels must contain at least one channel.")

    # Clinical safety invariant:
    # Clinical alerts cannot claim autonomous or definitive diagnostic authority.
    if payload.category == NotificationCategory.ALERT:
        if not payload.alert_metadata:
            raise DomainValidationError(
                "Clinical alert notifications require alert_metadata."
            )
        if not payload.alert_metadata.advisory:
            raise DomainValidationError(
                "Clinical alerts must be strictly advisory (advisory=True)."
            )
        if not payload.alert_metadata.requires_human_review:
            raise DomainValidationError(
                "Clinical alerts must require human review (requires_human_review=True)."
            )
