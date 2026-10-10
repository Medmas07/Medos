"""Boundary rules and schema validation of contracts/events/notification-event.v1.yaml."""

import copy
import pytest
from conftest import EVENTS, load, validator

CONTRACT = load("notification-event.v1.yaml", root=EVENTS)

POST_OP = CONTRACT["paths"]["/v1/events/notifications"]["post"]
EXAMPLES = POST_OP["requestBody"]["content"]["application/json"]["examples"]

envelope_schema = validator(CONTRACT, "#/components/schemas/NotificationEventEnvelope")
payload_schema = validator(CONTRACT, "#/components/schemas/NotificationPayload")
receipt_schema = validator(CONTRACT, "#/components/schemas/NotificationEventReceipt")
status_schema = validator(CONTRACT, "#/components/schemas/NotificationEventStatus")
alert_metadata_schema = validator(CONTRACT, "#/components/schemas/AlertMetadata")


def mutate_copy(document: dict, mutator) -> dict:
    copied = copy.deepcopy(document)
    mutator(copied)
    return copied


@pytest.mark.parametrize(
    "example_name",
    ["accessGranted", "clinicalAlert", "reviewRequested", "jobCompleted"],
)
def test_canonical_examples_are_valid(example_name):
    example = EXAMPLES[example_name]["value"]
    assert envelope_schema.is_valid(example)


def test_payload_minimization_rejects_raw_clinical_data():
    base = EXAMPLES["accessGranted"]["value"]
    # Invariant: events must never carry raw medical records or SQL dumps
    with_clinical_data = mutate_copy(
        base,
        lambda d: d["payload"].update(clinical_records={"diagnosis": "ICD-10-E11"}),
    )
    assert not envelope_schema.is_valid(with_clinical_data)

    with_sql = mutate_copy(
        base,
        lambda d: d["payload"].update(query="SELECT * FROM patients WHERE id = 'pat-a'"),
    )
    assert not envelope_schema.is_valid(with_sql)


def test_clinical_alerts_must_be_strictly_advisory():
    alert_example = EXAMPLES["clinicalAlert"]["value"]
    assert envelope_schema.is_valid(alert_example)

    # Invariant: AI/automated clinical alert cannot claim autonomous or non-advisory authority
    not_advisory = mutate_copy(
        alert_example,
        lambda d: d["payload"]["alert_metadata"].update(advisory=False),
    )
    assert not envelope_schema.is_valid(not_advisory)

    no_human_review = mutate_copy(
        alert_example,
        lambda d: d["payload"]["alert_metadata"].update(requires_human_review=False),
    )
    assert not envelope_schema.is_valid(no_human_review)


def test_recipient_roles_must_be_authorized_ecosystem_roles():
    base = EXAMPLES["accessGranted"]["value"]
    valid_roles = [
        "patient",
        "relative",
        "clinician",
        "governance_reviewer",
        "hospital_admin",
        "researcher",
    ]
    for role in valid_roles:
        doc = mutate_copy(base, lambda d: d["payload"].update(recipient_role=role))
        assert envelope_schema.is_valid(doc)

    invalid_role = mutate_copy(
        base, lambda d: d["payload"].update(recipient_role="superadmin")
    )
    assert not envelope_schema.is_valid(invalid_role)


def test_categories_match_canonical_types():
    base = EXAMPLES["accessGranted"]["value"]
    canonical_categories = [
        "access_granted",
        "new_record",
        "delegation_granted",
        "request_status",
        "alert",
        "review_requested",
        "job_completed",
    ]
    for cat in canonical_categories:
        doc = mutate_copy(base, lambda d: d["payload"].update(category=cat))
        assert envelope_schema.is_valid(doc)

    unknown_cat = mutate_copy(
        base, lambda d: d["payload"].update(category="unauthorized_broadcast")
    )
    assert not envelope_schema.is_valid(unknown_cat)


def test_event_type_naming_convention():
    base = EXAMPLES["accessGranted"]["value"]
    invalid_event_type = mutate_copy(
        base, lambda d: d.update(event_type="INVALID_NAME_WITHOUT_PREFIX")
    )
    assert not envelope_schema.is_valid(invalid_event_type)


def test_receipt_and_status_schema_validation():
    receipt = {
        "receipt_id": "rct-test-01",
        "event_id": "evt-notif-001",
        "status": "queued",
        "queued_at": "2026-10-10T09:00:01+01:00",
        "recipient_ref": "pat-a",
        "fictional": True,
    }
    assert receipt_schema.is_valid(receipt)

    invalid_receipt = mutate_copy(receipt, lambda r: r.update(status="unknown_status"))
    assert not receipt_schema.is_valid(invalid_receipt)

    status_doc = {
        "event_id": "evt-notif-001",
        "status": "processed",
        "received_at": "2026-10-10T09:00:00+01:00",
        "deliveries": [
            {
                "channel": "in_app",
                "status": "delivered",
                "dispatched_at": "2026-10-10T09:00:02+01:00",
            },
            {
                "channel": "push",
                "status": "failed",
                "failure_reason": "device_token_expired",
            },
        ],
        "fictional": True,
    }
    assert status_schema.is_valid(status_doc)
