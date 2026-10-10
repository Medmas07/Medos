# Hospital Node

## Purpose and status

CONFIRMED autonomous hospital-controlled boundary; its runtime is PLANNED and not implemented. It is expected to become a separately packaged/containerized instance after runtime decisions.

## Responsibilities and owned concepts

- Local clinical integration and canonical/FHIR representation.
- Hospital-specific DMI Adapter boundary at `adapters/dmi/`.
- Local storage and clinical source-data control.
- Consent/authorization enforcement at the local boundary.
- Local audit generation and Federation interface.
- Future local API, identity/RBAC, events, and health checks.

## Communication boundaries

The Node communicates through versioned API, event, and Federation contracts. `contracts/` is reserved for Node-owned local ports; repository-level cross-component contracts live at `/contracts`. Each hospital owns its DMI implementation and configuration.

## Non-responsibilities

The Hospital Node does not own ethics approval, global research approval, company billing, or central blockchain authority. Central services must not access its database or DMI/HIS directly.

## Expected contracts

PLANNED local clinical API, DMI port, consent/authorization, audit-event, synchronization, Federation, research-execution, and health contracts.
