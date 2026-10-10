# Federation Service

## Purpose and status

PLANNED coordination capability for authorized communication among autonomous Nodes. No runtime or contract implementation exists. When its first runtime ticket needs one, it is a separate Python + FastAPI project per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md).

## Responsibilities and owned concepts

Potential node discovery/capabilities, temporary authorization handling, cross-node query coordination, synchronization, aggregation, failures, and audit-event emission.

## Communication boundaries

All communication uses versioned Federation contracts and Node-owned interfaces.

## Non-responsibilities

It is not a centralized clinical database, does not access Hospital Node tables directly, and does not connect directly to hospital DMI/HIS systems.

## Expected contracts

PLANNED node identity/capabilities, authorization, query, synchronization, result-envelope, failure, and audit contracts.
