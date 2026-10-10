# Architecture Decision Records

Copy [the template](template.md) to `ADR-NNNN-short-title.md`. Keep records immutable after acceptance; add a superseding ADR when a decision changes.

Use an ADR for consequential choices including the frontend framework, mobile framework, backend/runtime strategy, persistence and ORM, FHIR strategy/profiles, authentication, API/transport style, Federation security, blockchain implementation, AI provider/model strategy, container runtime, deployment topology, hosting, and monolith/service boundaries.

An ADR records a real proposed or accepted decision; it must not be created merely to make an OPEN choice look settled. Use the shared [status vocabulary](../README.md#status-vocabulary) in surrounding documentation and link the evidence that supports the decision.

Clean/Hexagonal principles are an initial project constraint and do not require a new decision record.

## Index

| ADR | Title | Status |
|---|---|---|
| [ADR-0001](ADR-0001-web-frontend-technology.md) | Web frontend technology for the three web portals | Accepted |
| [ADR-0002](ADR-0002-mobile-technology.md) | Mobile technology for Patient App and Clinician App | Accepted |
| [ADR-0003](ADR-0003-backend-runtime-strategy.md) | Backend runtime strategy for Nodes and company services | Accepted |
