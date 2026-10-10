# Federation Service

## Purpose and status

PLANNED coordination capability for authorized communication among autonomous Nodes. Its first contracts are defined (HC-140, see Expected contracts); no runtime exists. When its first runtime ticket needs one, it is a separate Python + FastAPI project per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md).

## Responsibilities and owned concepts

Potential node discovery/capabilities, temporary authorization handling, cross-node query coordination, synchronization, aggregation, failures, and audit-event emission.

## Communication boundaries

All communication uses versioned Federation contracts and Node-owned interfaces.

## Non-responsibilities

It is not a centralized clinical database, does not access Hospital Node tables directly, and does not connect directly to hospital DMI/HIS systems.

## Expected contracts

- [`federated-patient-query.v1.yaml`](../../contracts/federation/federated-patient-query.v1.yaml): IMPLEMENTED contract this service provides. It sends a query to each node, merges the results into a transient timeline, and reports a status for each node. No provider yet; HC-141 is the first mock.
- [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml): IMPLEMENTED contract this service calls on each Hospital Node.
- PLANNED: node registry (HC-142), Governance verification of authorizations (HC-144), and audit event contracts.
