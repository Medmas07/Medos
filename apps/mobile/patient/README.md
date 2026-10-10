# Patient App

## Purpose and status

PLANNED mobile product for authorized patient views and access-management experiences. Flutter + Dart and an Android-first development path are CONFIRMED by [ADR-0002](../../../docs/decisions/ADR-0002-mobile-technology.md). No dependencies, generated platform project, or application code exists.

## Responsibilities and owned concepts

- Longitudinal views across organizations, event details, medications, labs, and notifications.
- User interactions for physician access, revocation, family delegation, consent, and restriction/erasure requests.

## Communication boundaries

The Patient App consumes authorized views through explicit Federation/Hospital Node-facing API contracts. It does not directly access or own hospital databases.

## Non-responsibilities

It is not the clinical source of record, a Governance decision maker, or a guarantee of unconditional medical-record deletion.

## Expected contracts

PLANNED patient-view, timeline, medication, consent/access-grant, request-status, and notification contracts.
