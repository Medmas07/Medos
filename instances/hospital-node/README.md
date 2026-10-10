# Hospital Node

## Purpose and status

CONFIRMED autonomous hospital-controlled boundary; its runtime is PLANNED and not implemented. Its stack (Python + FastAPI, one process per hospital from one codebase, flat layer layout that keeps `adapters/dmi/`) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md); HC-110 creates the runtime. It is expected to become a separately packaged/containerized instance; container choices remain OPEN.

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

Each Hospital Node must provide [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml) (HC-140): a node descriptor and authorized, scoped patient queries that the node enforces itself. The contract is defined; no Node implements it yet.

The D1 [research execution contract](../../contracts/api/research/research-node-execution.v1.yaml) is IMPLEMENTED for Research Service-to-Node Compute-to-Data communication. No Node agent implements it; authorization verification, sandboxing, package policy, disclosure review, and audit remain PLANNED or OPEN. Local clinical API, DMI port, consent/authorization, audit-event, and health contracts are PLANNED.
