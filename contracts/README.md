# Communication Contracts

## Purpose and status

This is the canonical location for significant, versionable cross-component communication definitions. The directory structure is IMPLEMENTED. API contracts exist under [`api/`](api/README.md), Federation contracts under [`federation/`](federation/README.md), and Event contracts under [`events/`](events/README.md), all OpenAPI 3.1 files checked by the [contract tests](../tests/contracts/); shared-schema contracts remain PLANNED.

## Responsibilities and owned concepts

- `api/`: API specifications such as OpenAPI, request/response formats, errors, authentication conventions, and versioning.
- `events/`: asynchronous cross-component event definitions and envelopes.
- `federation/`: Hospital Node/Governance/Federation communication, identity, authorization, scope, synchronization, results, and errors.
- `schemas/`: technology-neutral shared message schemas.

## Communication boundaries

Contracts describe stable communication across bounded contexts. They must be versionable and owned by the communicating boundary.

## Non-responsibilities

Contracts do not describe internal persistence, share database tables, centralize domain models, implement brokers/APIs, or bypass application-owned ports.

## Expected contracts

Add only validated definitions required by an implemented ticket. Examples in planning or architecture are not final schemas.
