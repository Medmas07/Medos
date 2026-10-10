# Communication Contracts

This is the canonical home for significant, versionable definitions exchanged across bounded contexts. It contains definitions, not business implementations or executable infrastructure.

- `api/`: future OpenAPI definitions, endpoint conventions, request/response shapes, errors, authentication conventions, and versioning.
- `events/`: future cross-component event definitions. Possible names such as `hospital.approved`, `consent.updated`, or `research.requested` are illustrative only.
- `schemas/`: future shared wire schemas for organization, patient references, consent, authorization, research requests, audit events, and notifications. Domain models remain locally owned.
- `federation/`: Hospital Node communication definitions for node identity, capability discovery, authorization tokens, synchronization, scope, expiration, signatures, result envelopes, and errors.

Do not invent APIs, final schemas, event infrastructure, or cryptography here. Components must not bypass contracts through direct database access or shared persistence models.
