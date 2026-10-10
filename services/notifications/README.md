# Notification Service

## Purpose and status

PLANNED capability for authorized notifications to patients, clinicians, researchers, hospital administrators, and governance reviewers. No provider, protocol, runtime, or delivery code exists. When HC-202 creates the runtime, it is a separate Python + FastAPI project per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md).

## Responsibilities and owned concepts

Potential notification-event intake, preference/routing coordination, delivery status, and provider adaptation.

## Communication boundaries

Consumes explicit event contracts ([`contracts/events/notification-event.v1.yaml`](../../contracts/events/notification-event.v1.yaml)) and delivers through future provider adapters; sensitive payloads must be minimized.

## Non-responsibilities

It does not own clinical decisions, patient records, authorization policy, or source business events.

## Expected contracts

- [`contracts/events/notification-event.v1.yaml`](../../contracts/events/notification-event.v1.yaml): IMPLEMENTED at depth D1 (HC-201).
- Recipient preference, delivery request/status, and provider-error contracts remain PLANNED for HC-202.
