"""HTTP endpoints integration tests using TestClient."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["depth"] == "D2"
    assert "notification_event_intake" in data["capabilities"]
    assert "in_app_delivery" in data["capabilities"]
    assert data["boundaries"]["clinical_data_access"] == "denied_by_design"


def test_publish_notification_event_returns_202_accepted():
    payload = {
        "event_id": "evt-http-001",
        "event_type": "notification.access_granted",
        "occurred_at": "2026-10-10T09:00:00+01:00",
        "source": "hospital-node-a",
        "schema_version": "1.0.0",
        "correlation_id": "corr-grant-a-drx",
        "payload": {
            "notification_id": "notif-http-001",
            "recipient_ref": "pat-a",
            "recipient_role": "patient",
            "category": "access_granted",
            "priority": "normal",
            "title": "Accès accordé",
            "body": "Dr Youssef Gharbi peut consulter votre historique.",
            "channels": ["in_app", "push"],
            "related_resource": {
                "resource_type": "access_grant",
                "resource_ref": "grant-a-drx",
            },
            "fictional": True,
        },
    }
    response = client.post("/v1/events/notifications", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["event_id"] == "evt-http-001"
    assert data["status"] == "queued"
    assert data["recipient_ref"] == "pat-a"
    assert "receipt_id" in data


def test_publish_clinical_alert_with_advisory_metadata():
    payload = {
        "event_id": "evt-http-alert-001",
        "event_type": "notification.alert",
        "occurred_at": "2026-09-30T16:00:00+01:00",
        "source": "hospital-node-b",
        "schema_version": "1.0.0",
        "payload": {
            "notification_id": "notif-http-alert-001",
            "recipient_ref": "clin-x",
            "recipient_role": "clinician",
            "category": "alert",
            "priority": "high",
            "title": "Résultat anormal",
            "body": "HbA1c au-dessus de la plage de référence pour Karim Haddad.",
            "channels": ["in_app"],
            "alert_metadata": {
                "advisory": True,
                "requires_human_review": True,
                "finding_type": "abnormal_lab_value",
            },
            "fictional": True,
        },
    }
    response = client.post("/v1/events/notifications", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["event_id"] == "evt-http-alert-001"


def test_publish_clinical_alert_non_advisory_returns_400_problem():
    # Invariant: AI/automated clinical alerts cannot claim non-advisory clinical authority
    payload = {
        "event_id": "evt-http-bad-alert",
        "event_type": "notification.alert",
        "occurred_at": "2026-09-30T16:00:00+01:00",
        "source": "hospital-node-b",
        "schema_version": "1.0.0",
        "payload": {
            "notification_id": "notif-http-bad-alert",
            "recipient_ref": "clin-x",
            "recipient_role": "clinician",
            "category": "alert",
            "priority": "high",
            "title": "Résultat anormal",
            "body": "HbA1c au-dessus de la plage.",
            "channels": ["in_app"],
            "alert_metadata": {
                "advisory": False,
                "requires_human_review": True,
            },
            "fictional": True,
        },
    }
    response = client.post("/v1/events/notifications", json=payload)
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["status"] == 400
    assert "advisory" in data["detail"]


def test_get_event_status_returns_200_and_deliveries():
    # Publish first
    event_id = "evt-http-status-test"
    payload = {
        "event_id": event_id,
        "event_type": "notification.new_record",
        "occurred_at": "2026-10-10T09:00:00+01:00",
        "source": "hospital-node-a",
        "schema_version": "1.0.0",
        "payload": {
            "notification_id": "notif-status-test",
            "recipient_ref": "pat-a",
            "recipient_role": "patient",
            "category": "new_record",
            "priority": "normal",
            "title": "Nouveau bilan disponible",
            "body": "Un bilan biologique a été ajouté.",
            "channels": ["in_app"],
            "fictional": True,
        },
    }
    post_res = client.post("/v1/events/notifications", json=payload)
    assert post_res.status_code == 202

    # Query status
    status_res = client.get(f"/v1/events/notifications/{event_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["event_id"] == event_id
    assert status_data["status"] == "processed"
    assert len(status_data["deliveries"]) == 1
    assert status_data["deliveries"][0]["channel"] == "in_app"
    assert status_data["deliveries"][0]["status"] == "delivered"


def test_get_event_status_not_found_returns_404_problem():
    response = client.get("/v1/events/notifications/unknown-event-id")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["status"] == 404
    assert "No notification event found" in data["detail"]


def test_list_recipient_notifications():
    # Query recipient pat-a
    response = client.get("/v1/recipients/pat-a/notifications")
    assert response.status_code == 200
    data = response.json()
    assert data["recipient_ref"] == "pat-a"
    assert isinstance(data["notifications"], list)
