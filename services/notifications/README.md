# Notification Service

## Purpose and status

**IMPLEMENTED (D2)** capability for authorized notifications to patients, relatives, clinicians, researchers, hospital administrators, and governance reviewers per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md) (HC-202).

It runs as a standalone Python + FastAPI service on port 8700, adhering strictly to Clean / Hexagonal Architecture.

## Architecture and layers

Following repository architecture invariants:

```text
infrastructure (config) -> adapters (HTTP, in-memory store, channel providers) -> application (use cases, ports) -> domain (models, validation)
```

- **Domain (`domain/`)**: Pure Python domain models, value objects, and invariant validation rules. Zero framework, database, or external library dependencies.
- **Application (`application/`)**: Use cases (`IngestNotificationEventUseCase`, `GetNotificationEventStatusUseCase`, `ListRecipientNotificationsUseCase`) and ports (`NotificationStorePort`, `DeliveryProviderPort`, `PreferenceStorePort`).
- **Adapters (`adapters/`)**:
  - `inbound/http/`: FastAPI route handlers for contract endpoints and `/health`.
  - `outbound/`: Thread-safe `InMemoryNotificationStore` (seeded from canonical `demo-data/notifications.json`) and delivery channel adapters (`in_app`, `push`, `email`, `sms`).
- **Infrastructure (`infrastructure/`)**: Environment settings (`Settings`).

## Responsibilities and owned concepts

- Notification event intake conforming to [`contracts/events/notification-event.v1.yaml`](../../contracts/events/notification-event.v1.yaml).
- Recipient routing and preference evaluation (suppressing muted categories or disabled channels).
- Multi-channel delivery coordination (`in_app`, `push`, `email`, `sms`).
- Delivery status tracking (`pending`, `delivered`, `failed`, `suppressed`).
- Ingestion receipts and delivery history query.

## Communication boundaries and invariants

- **Payload minimization**: Events carry human-readable summaries, localized titles, and opaque domain references (`grant-a-drx`, `sync-001`, `job-001`). Raw clinical records, consultation notes, lab values, or SQL queries are forbidden.
- **No autonomous clinical authority**: Any clinical alert is strictly advisory (`advisory: true`, `requires_human_review: true`). The service never claims autonomous diagnostic authority.
- **Explicit recipient roles**: Targets opaque recipient identifiers with authorized functional roles (`patient`, `relative`, `clinician`, `governance_reviewer`, `hospital_admin`, `researcher`).
- **Delivery isolation**: Provider retries or channel failures do not impact emitting transaction sources. Emitting components are completely decoupled from delivery provider infrastructure.

## Non-responsibilities

- Does NOT own clinical records, diagnoses, or prescriptions.
- Does NOT own authorization policies (governed by the Governance Node).
- Does NOT store patient records or connect to hospital databases.

## HTTP Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/events/notifications` | Ingest an event; returns `202 Accepted` with receipt or `400` Problem details. |
| `GET` | `/v1/events/notifications/{event_id}` | Check processing and per-channel delivery status. |
| `GET` | `/v1/recipients/{recipient_ref}/notifications` | List notifications for an authorized recipient (newest first). |
| `GET` | `/health` | Liveness and capability discovery endpoint (depth D2). |

## Integration depth D2 limitations

- **In-memory persistence**: Events, deliveries, and preferences are stored in process memory (lost on restart), optionally seeded from canonical demo fixtures.
- **Simulated push/email channels**: Channel adapters simulate delivery dispatch; real mobile push (APNs/FCM) is sequenced under HC-204.
- **Unauthenticated callers**: Callers declare recipient and source identities without JWT / OAuth verification (auth foundation is sequenced under HC-210/HC-211).

## Development and testing

Run unit and integration tests:

```bash
cd services/notifications
pytest
```
