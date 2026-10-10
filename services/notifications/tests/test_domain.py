"""Domain layer unit tests."""

from datetime import datetime, timezone
import pytest

from domain.models import (
    AlertMetadata,
    Channel,
    NotificationCategory,
    NotificationEvent,
    NotificationPayload,
    Priority,
    RecipientRole,
    RelatedResource,
)
from domain.validation import DomainValidationError, validate_notification_event


def make_valid_event() -> NotificationEvent:
    payload = NotificationPayload(
        notification_id="notif-test-01",
        recipient_ref="pat-a",
        recipient_role=RecipientRole.PATIENT,
        category=NotificationCategory.ACCESS_GRANTED,
        priority=Priority.NORMAL,
        title="Accès accordé",
        body="Dr Youssef Gharbi peut consulter votre historique.",
        channels=[Channel.IN_APP, Channel.PUSH],
        related_resource=RelatedResource("access_grant", "grant-a-drx"),
        fictional=True,
    )
    return NotificationEvent(
        event_id="evt-test-01",
        event_type="notification.access_granted",
        occurred_at=datetime.now(timezone.utc),
        source="hospital-node-a",
        schema_version="1.0.0",
        payload=payload,
    )


def test_valid_event_passes_validation():
    event = make_valid_event()
    validate_notification_event(event)


def test_empty_event_id_raises_validation_error():
    base = make_valid_event()
    invalid_event = NotificationEvent(
        event_id="",
        event_type=base.event_type,
        occurred_at=base.occurred_at,
        source=base.source,
        schema_version=base.schema_version,
        payload=base.payload,
    )
    with pytest.raises(DomainValidationError, match="event_id must not be empty"):
        validate_notification_event(invalid_event)


def test_invalid_event_type_pattern_raises_validation_error():
    base = make_valid_event()
    invalid_event = NotificationEvent(
        event_id=base.event_id,
        event_type="INVALID_TYPE",
        occurred_at=base.occurred_at,
        source=base.source,
        schema_version=base.schema_version,
        payload=base.payload,
    )
    with pytest.raises(DomainValidationError, match="event_type.*must follow pattern"):
        validate_notification_event(invalid_event)


def test_clinical_alert_must_have_advisory_metadata():
    alert_payload = NotificationPayload(
        notification_id="notif-alert-01",
        recipient_ref="clin-x",
        recipient_role=RecipientRole.CLINICIAN,
        category=NotificationCategory.ALERT,
        priority=Priority.HIGH,
        title="Résultat anormal",
        body="HbA1c au-dessus de la valeur seuil.",
        channels=[Channel.IN_APP],
        alert_metadata=None,
    )
    event = NotificationEvent(
        event_id="evt-alert-01",
        event_type="notification.alert",
        occurred_at=datetime.now(timezone.utc),
        source="hospital-node-b",
        schema_version="1.0.0",
        payload=alert_payload,
    )
    with pytest.raises(
        DomainValidationError, match="require alert_metadata"
    ):
        validate_notification_event(event)


def test_clinical_alert_with_non_advisory_metadata_raises_error():
    # Invariant: Clinical alerts cannot claim autonomous clinical authority
    alert_payload = NotificationPayload(
        notification_id="notif-alert-01",
        recipient_ref="clin-x",
        recipient_role=RecipientRole.CLINICIAN,
        category=NotificationCategory.ALERT,
        priority=Priority.HIGH,
        title="Résultat anormal",
        body="HbA1c au-dessus de la valeur seuil.",
        channels=[Channel.IN_APP],
        alert_metadata=AlertMetadata(advisory=False, requires_human_review=True),
    )
    event = NotificationEvent(
        event_id="evt-alert-01",
        event_type="notification.alert",
        occurred_at=datetime.now(timezone.utc),
        source="hospital-node-b",
        schema_version="1.0.0",
        payload=alert_payload,
    )
    with pytest.raises(
        DomainValidationError, match="strictly advisory"
    ):
        validate_notification_event(event)


def test_clinical_alert_without_human_review_raises_error():
    alert_payload = NotificationPayload(
        notification_id="notif-alert-01",
        recipient_ref="clin-x",
        recipient_role=RecipientRole.CLINICIAN,
        category=NotificationCategory.ALERT,
        priority=Priority.HIGH,
        title="Résultat anormal",
        body="HbA1c au-dessus de la valeur seuil.",
        channels=[Channel.IN_APP],
        alert_metadata=AlertMetadata(advisory=True, requires_human_review=False),
    )
    event = NotificationEvent(
        event_id="evt-alert-01",
        event_type="notification.alert",
        occurred_at=datetime.now(timezone.utc),
        source="hospital-node-b",
        schema_version="1.0.0",
        payload=alert_payload,
    )
    with pytest.raises(
        DomainValidationError, match="require human review"
    ):
        validate_notification_event(event)


def test_empty_channels_raises_validation_error():
    payload = NotificationPayload(
        notification_id="notif-test-01",
        recipient_ref="pat-a",
        recipient_role=RecipientRole.PATIENT,
        category=NotificationCategory.ACCESS_GRANTED,
        priority=Priority.NORMAL,
        title="Titre",
        body="Corps du message",
        channels=[],
    )
    event = NotificationEvent(
        event_id="evt-test-01",
        event_type="notification.access_granted",
        occurred_at=datetime.now(timezone.utc),
        source="hospital-node-a",
        schema_version="1.0.0",
        payload=payload,
    )
    with pytest.raises(DomainValidationError, match="at least one channel"):
        validate_notification_event(event)
