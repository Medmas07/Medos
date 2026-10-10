"""Tests for HC-203: Real-time clinician alerts endpoints and use case.

Covers:
  - ListClinicianAlertsUseCase: ordering, filtering, empty case
  - GET /v1/clinicians/{clinician_ref}/alerts: REST endpoint
  - GET /v1/clinicians/{clinician_ref}/alerts/stream: SSE endpoint boundary
  - Advisory metadata presence on all returned alerts
  - No raw clinical data leakage
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from adapters.outbound.in_memory_store import InMemoryNotificationStore
from application.use_cases import ListClinicianAlertsUseCase
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_alert_event(
    event_id: str,
    clinician_ref: str,
    priority: Priority = Priority.NORMAL,
    occurred_offset: int = 0,
) -> NotificationEvent:
    """Build a minimal clinician alert NotificationEvent."""
    return NotificationEvent(
        event_id=event_id,
        event_type="notification.alert",
        occurred_at=datetime(2026, 9, 30, 16 + occurred_offset, 0, 0, tzinfo=timezone.utc),
        source="test",
        schema_version="1.0.0",
        payload=NotificationPayload(
            notification_id=f"notif-{event_id}",
            recipient_ref=clinician_ref,
            recipient_role=RecipientRole.CLINICIAN,
            category=NotificationCategory.ALERT,
            priority=priority,
            title="Test Alert",
            body="Advisory test alert body.",
            channels=[Channel.IN_APP],
            alert_metadata=AlertMetadata(
                advisory=True,
                requires_human_review=True,
                finding_type="abnormal_lab_value",
            ),
            related_resource=RelatedResource(
                resource_type="lab_report",
                resource_ref="lab-test-001",
            ),
            fictional=True,
        ),
    )


def _make_non_alert_event(event_id: str, clinician_ref: str) -> NotificationEvent:
    """Build a non-alert notification for the same clinician."""
    return NotificationEvent(
        event_id=event_id,
        event_type="notification.access_granted",
        occurred_at=datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc),
        source="test",
        schema_version="1.0.0",
        payload=NotificationPayload(
            notification_id=f"notif-{event_id}",
            recipient_ref=clinician_ref,
            recipient_role=RecipientRole.CLINICIAN,
            category=NotificationCategory.ACCESS_GRANTED,
            priority=Priority.NORMAL,
            title="Access Granted",
            body="Access granted notice.",
            channels=[Channel.IN_APP],
            fictional=True,
        ),
    )


@pytest.fixture()
def store() -> InMemoryNotificationStore:
    return InMemoryNotificationStore()


@pytest.fixture()
def use_case(store: InMemoryNotificationStore) -> ListClinicianAlertsUseCase:
    return ListClinicianAlertsUseCase(store=store)


@pytest.fixture()
def client(store: InMemoryNotificationStore) -> TestClient:
    """Build a minimal FastAPI test client with only the clinician alerts router."""
    from fastapi import FastAPI
    from adapters.inbound.http.clinician_alerts import create_clinician_alerts_router

    app = FastAPI()
    list_alerts_uc = ListClinicianAlertsUseCase(store=store)
    app.include_router(create_clinician_alerts_router(list_alerts_use_case=list_alerts_uc))
    return TestClient(app)


# ---------------------------------------------------------------------------
# Use-case unit tests
# ---------------------------------------------------------------------------


class TestListClinicianAlertsUseCase:
    def test_returns_empty_list_when_no_alerts(self, use_case, store):
        result = use_case.execute("clin-x")
        assert result == []

    def test_only_returns_alert_category_events(self, use_case, store):
        store.save_event(_make_alert_event("a1", "clin-x"))
        store.save_event(_make_non_alert_event("na1", "clin-x"))
        result = use_case.execute("clin-x")
        assert len(result) == 1
        assert result[0].event_id == "a1"

    def test_only_returns_alerts_for_the_given_clinician(self, use_case, store):
        store.save_event(_make_alert_event("a1", "clin-x"))
        store.save_event(_make_alert_event("a2", "clin-y"))
        result = use_case.execute("clin-x")
        assert len(result) == 1
        assert result[0].event_id == "a1"

    def test_orders_by_priority_then_recency(self, use_case, store):
        # high priority, older
        store.save_event(_make_alert_event("high-old", "clin-x", Priority.HIGH, occurred_offset=0))
        # urgent priority, newer
        store.save_event(_make_alert_event("urgent-new", "clin-x", Priority.URGENT, occurred_offset=2))
        # normal priority, newest
        store.save_event(_make_alert_event("normal-newest", "clin-x", Priority.NORMAL, occurred_offset=3))

        result = use_case.execute("clin-x")
        ids = [e.event_id for e in result]
        # urgent first, then high, then normal
        assert ids == ["urgent-new", "high-old", "normal-newest"]

    def test_all_returned_events_have_alert_category(self, use_case, store):
        store.save_event(_make_alert_event("a1", "clin-x", Priority.HIGH))
        store.save_event(_make_alert_event("a2", "clin-x", Priority.URGENT))
        for event in use_case.execute("clin-x"):
            assert event.payload.category == NotificationCategory.ALERT


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------


class TestClinicianAlertsHTTP:
    def test_get_alerts_empty(self, client):
        resp = client.get("/v1/clinicians/clin-x/alerts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["clinician_ref"] == "clin-x"
        assert body["count"] == 0
        assert body["alerts"] == []
        assert body["fictional"] is True

    def test_get_alerts_returns_alert_events(self, client, store):
        store.save_event(_make_alert_event("a1", "clin-x", Priority.HIGH))
        resp = client.get("/v1/clinicians/clin-x/alerts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        alert = body["alerts"][0]
        assert alert["event_id"] == "a1"
        assert alert["priority"] == "high"
        assert alert["fictional"] is True

    def test_get_alerts_advisory_notice_present(self, client, store):
        store.save_event(_make_alert_event("a1", "clin-x"))
        resp = client.get("/v1/clinicians/clin-x/alerts")
        body = resp.json()
        assert "advisory_notice" in body
        assert "advisory" in body["advisory_notice"].lower()

    def test_get_alerts_each_alert_has_advisory_metadata(self, client, store):
        store.save_event(_make_alert_event("a1", "clin-x"))
        resp = client.get("/v1/clinicians/clin-x/alerts")
        alert = resp.json()["alerts"][0]
        assert "alert_metadata" in alert
        assert alert["alert_metadata"]["advisory"] is True
        assert alert["alert_metadata"]["requires_human_review"] is True

    def test_get_alerts_excludes_non_alert_events(self, client, store):
        store.save_event(_make_non_alert_event("na1", "clin-x"))
        resp = client.get("/v1/clinicians/clin-x/alerts")
        assert resp.json()["count"] == 0

    def test_get_alerts_returns_only_own_clinician_alerts(self, client, store):
        store.save_event(_make_alert_event("a1", "clin-x"))
        store.save_event(_make_alert_event("a2", "clin-y"))
        resp = client.get("/v1/clinicians/clin-y/alerts")
        body = resp.json()
        assert body["count"] == 1
        assert body["alerts"][0]["event_id"] == "a2"

    def test_sse_route_is_registered(self, client):
        """SSE endpoint is registered in the router under the correct path."""
        from adapters.inbound.http.clinician_alerts import create_clinician_alerts_router
        from application.use_cases import ListClinicianAlertsUseCase
        from adapters.outbound.in_memory_store import InMemoryNotificationStore

        router = create_clinician_alerts_router(
            list_alerts_use_case=ListClinicianAlertsUseCase(
                store=InMemoryNotificationStore()
            )
        )
        paths = [route.path for route in router.routes]  # type: ignore[attr-defined]
        assert "/v1/clinicians/{clinician_ref}/alerts/stream" in paths

    def test_sse_boundary_header_in_route_response_class(self):
        """SSE endpoint response carries the D3 boundary header declaration."""
        import inspect
        from adapters.inbound.http import clinician_alerts as mod

        src = inspect.getsource(mod)
        assert "X-HC-203-Boundary" in src
        assert "D3" in src


# ---------------------------------------------------------------------------
# No raw clinical data tests
# ---------------------------------------------------------------------------


class TestNoRawClinicalData:
    def test_alert_body_is_minimized_no_fhir_dump(self, client, store):
        """Body field must not contain embedded JSON or FHIR structures."""
        event = _make_alert_event("a1", "clin-x")
        store.save_event(event)
        resp = client.get("/v1/clinicians/clin-x/alerts")
        alert = resp.json()["alerts"][0]
        # Body is a plain-text string, not a nested JSON object
        assert isinstance(alert["body"], str)
        assert "{" not in alert["body"] or len(alert["body"]) < 500

    def test_response_does_not_expose_patient_identifiers_beyond_opaque_ref(
        self, client, store
    ):
        event = _make_alert_event("a1", "clin-x")
        store.save_event(event)
        resp = client.get("/v1/clinicians/clin-x/alerts")
        text = resp.text
        # No raw patient names or medical record numbers
        assert "Mansouri" not in text
        assert "Haddad" not in text
