# Notification Service

## Purpose and status

**IMPLEMENTED (D2/D3)** capability for authorized notifications to patients, relatives, clinicians, researchers, hospital administrators, and governance reviewers per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md) (HC-202, HC-203).

HC-203 (D3) adds real-time clinician alert queries and a polling-based SSE stream, plus a `ClinicianAlertsView` in the Hospital Portal.

HC-204 (D3) replaces the simulated push channel with **real mobile push**: UnifiedPush / encrypted Web Push, as decided by [ADR-0012](../../docs/decisions/ADR-0012-mobile-push-provider.md). See [Mobile push](#mobile-push-hc-204). Live delivery to a device is **NOT VALIDATED**.

It runs as a standalone Python + FastAPI service on port 8700, adhering strictly to Clean / Hexagonal Architecture.

## Architecture and layers

Following repository architecture invariants:

```text
infrastructure (config) -> adapters (HTTP, in-memory store, channel providers) -> application (use cases, ports) -> domain (models, validation)
```

- **Domain (`domain/`)**: Pure Python domain models, value objects, and invariant validation rules. Zero framework, database, or external library dependencies.
- **Application (`application/`)**: Use cases (`IngestNotificationEventUseCase`, `GetNotificationEventStatusUseCase`, `ListRecipientNotificationsUseCase`, `ListClinicianAlertsUseCase`) and ports (`NotificationStorePort`, `DeliveryProviderPort`, `PreferenceStorePort`).
- **Adapters (`adapters/`)**:
  - `inbound/http/`: FastAPI route handlers for contract endpoints and `/health`.
  - `outbound/`: Thread-safe `InMemoryNotificationStore` (seeded from canonical `demo-data/notifications.json`) and delivery channel adapters (`in_app`, `push`, `email`, `sms`).
- **Infrastructure (`infrastructure/`)**: Environment settings (`Settings`).

## Responsibilities and owned concepts

- Notification event intake conforming to [`contracts/events/notification-event.v1.yaml`](../../contracts/events/notification-event.v1.yaml).
- Recipient routing and preference evaluation (suppressing muted categories or disabled channels).
- Multi-channel delivery coordination (`in_app`, `push`, `email`, `sms`).
- Delivery status tracking (`pending`, `sent`, `delivered`, `failed`, `suppressed`).
- Mobile push subscriptions and encrypted Web Push delivery (HC-204).
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
| `GET` | `/v1/clinicians/{clinician_ref}/alerts` | **HC-203** List advisory alert-category notifications for a clinician, ordered by priority then recency. |
| `GET` | `/v1/clinicians/{clinician_ref}/alerts/stream` | **HC-203** SSE stream of clinician alerts (polling-based, D3, not broker-backed). |
| `POST` | `/v1/recipients/{recipient_ref}/push-subscriptions` | **HC-204** Register a device's UnifiedPush subscription ([contract](../../contracts/api/notifications/push-subscriptions.v1.yaml)). |
| `GET` | `/v1/recipients/{recipient_ref}/push-subscriptions` | **HC-204** List a recipient's devices, without their endpoints. |
| `DELETE` | `/v1/recipients/{recipient_ref}/push-subscriptions/{subscription_id}` | **HC-204** Remove a device. |
| `GET` | `/health` | Liveness and capability discovery endpoint (depth D3). |

## Integration depth D2/D3 limitations

- **In-memory persistence**: Events, deliveries, and preferences are stored in process memory (lost on restart), optionally seeded from canonical demo fixtures.
- **Simulated email/SMS channels**: those adapters still simulate dispatch. Push is real since HC-204, but live delivery to a device is not validated.
- **Unauthenticated callers**: Callers declare recipient and source identities without JWT / OAuth verification (auth foundation is sequenced under HC-210/HC-211).
- **SSE is polling-based (D3)**: `/alerts/stream` polls the in-memory store at a configurable interval; it is not backed by a real message broker, WebSocket, or push server. This is explicitly labelled in response headers (`X-HC-203-Boundary: D3-SSE-simulation-polling-based`). Real-time broker delivery is out of scope for D3.

## Mobile push (HC-204)

IMPLEMENTED at D3; provider decided by [ADR-0012](../../docs/decisions/ADR-0012-mobile-push-provider.md). A notification event with the `push` channel becomes a real Web Push message to every device the recipient registered.

- **Registration** ([`push-subscriptions.v1.yaml`](../../contracts/api/notifications/push-subscriptions.v1.yaml)): a device sends the endpoint its UnifiedPush distributor gave it and its RFC 8291 keys, in the W3C PushSubscription JSON shape.
  - Only `https` endpoints on an allowed push server are accepted (`NOTIFICATION_PUSH_ALLOWED_HOSTS`, default `ntfy.sh`): the service POSTs to these URLs, so the allowlist prevents server-side request forgery.
  - The endpoint is a secret capability URL; answers give only its host. Registering the same endpoint again replaces its keys.
- **Message** ([`domain/push.py`](domain/push.py)): a generic French title per category ("Nouvelle alerte à consulter", …), the notification id to open in the app, and the priority. **Never the notification's title or body**, which may hold clinical wording and could show on a lock screen.
- **Encryption** ([`adapters/outbound/webpush_encryption.py`](adapters/outbound/webpush_encryption.py)): RFC 8291 with aes128gcm, so the push server relays bytes it cannot read. A test reproduces the RFC 8291 Appendix A test vector byte for byte.
- **Sending** ([`adapters/outbound/unifiedpush_gateway.py`](adapters/outbound/unifiedpush_gateway.py)): POST with `TTL` (24 h) and `Urgency` from the priority; redirects are not followed; no VAPID.
- **Status**, per event:
  - `sent` when at least one push server accepted the push. This is a contract 1.1.0 status; device receipt is unconfirmed, so it is never `delivered`.
  - `failed` otherwise, with `push_subscription_not_registered`, `push_endpoint_gone` (a 404 also removes the subscription), `push_rate_limited`, or `push_server_rejected`.
- The former simulated push provider, which reported every push as `delivered`, is removed.

**Validation:** 31 tests cover the encryption (including a test-only receiver that decrypts what a device would get), the message, registration, delivery outcomes, the HTTP gateway against a mock push server, and the API against its contract.

**Live delivery is NOT VALIDATED.** On 2026-10-11, a correctly encrypted push to ntfy.sh got HTTP 507 ("cannot publish to UnifiedPush topic without previously active subscriber"), even with a live subscription from the same machine. The service recorded it honestly as `failed: push_server_rejected`. ntfy.sh only accepts these pushes for a real, previously active device; a phone with a UnifiedPush distributor, or a self-hosted ntfy, is needed to validate it.

Not done:
- No mobile app registers yet: the Flutter Patient App has no HTTP client, and its UnifiedPush receiver is the next step.
- Subscriptions are in memory.
- Registration is unauthenticated (demo depth): anyone can register a device for a recipient.
- No VAPID; no FCM or APNs.

## Development and testing

Run unit and integration tests:

```bash
cd services/notifications
pytest
```
