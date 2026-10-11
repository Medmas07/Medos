# ADR-0012: Mobile push — UnifiedPush with encrypted Web Push, no clinical text

## Status

Accepted — 2026-10-11, chosen by the HC-204 assignee during HC-204 ([#162](https://github.com/Medmas07/Hackcure_hackathon/issues/162)); subject to pull-request review.

## Context

The Notification Service (HC-202) routes events to channels, but its push channel only simulated delivery and reported every push as `delivered`. HC-204 requires real mobile push. [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md) and [ADR-0004](ADR-0004-mobile-technology.md) left notification providers OPEN.

Forces:

- **Health data:** a push crosses a third-party push server and can show on a lock screen.
- **No secrets in the repository**, and nothing a contributor must create an account for.
- **Federated, multi-organization product:** depending on one vendor's push platform is a lasting coupling.
- **SSRF:** a push service sends HTTP requests to URLs that devices supply.

## Decision

1. **Protocol: UnifiedPush**, which delivers standard Web Push (RFC 8030) to a device's push distributor. The demo push server is ntfy; a self-hosted ntfy (by the platform or a hospital) is the recommended deployment, so even push metadata stays in-house.
2. **Every message is encrypted to the device** (RFC 8291, aes128gcm), as the UnifiedPush specification requires. The implementation is checked against the RFC's test vector.
3. **No clinical text in a push.** The message carries a generic French title per category and the notification id to open in the app, never the notification's title or body.
4. **Honest status:** a push accepted by the push server is `sent`, a new delivery status of the event contract (1.1.0); `delivered` stays for confirmed delivery. A 404 from the push server removes the subscription.
5. **Allowlist of push servers** (`NOTIFICATION_PUSH_ALLOWED_HOSTS`, default `ntfy.sh`): only https endpoints on those hosts can be registered, and redirects are not followed.
6. Devices register through [`push-subscriptions.v1.yaml`](../../contracts/api/notifications/push-subscriptions.v1.yaml), in the W3C PushSubscription JSON shape.

## Alternatives considered

- **Firebase Cloud Messaging:** the Android default and the most reliable delivery, but it requires a Google project and a service-account secret, and couples the product to one vendor. It is the likely addition if store-distributed apps need it; a Web Push gateway is already behind the same port.
- **APNs:** needed for iOS later; out of scope for the Android-first apps (ADR-0004).
- **Keeping the simulation:** rejected; it reported deliveries that never happened.

## Consequences

### Positive

- Real, standard push with no secrets, no vendor account, and end-to-end encryption: the push server relays bytes it cannot read.
- Lock screens show no clinical wording.

### Negative

- A user needs a UnifiedPush distributor app (for example ntfy) on the phone.
- The public ntfy.sh server refuses pushes to UnifiedPush topics without a previously active device subscriber (HTTP 507). Live delivery was therefore not validated from a development machine; it needs a real device or a self-hosted server.
- Subscriptions are in memory and the registration API is unauthenticated (demo depth): anyone could register a device for a recipient. Messages carry no clinical text, but this must be closed before real use.
- No VAPID: push servers that require it are not supported yet.

## Follow-up

- Validate delivery to a real device, and on a self-hosted ntfy.
- Patient and Clinician App receivers (Flutter UnifiedPush connector).
- Authenticated registration and durable subscription storage.
