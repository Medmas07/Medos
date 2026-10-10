# Governance Node

## Purpose and status

CONFIRMED Governance / Ethics Authority boundary; its runtime is PLANNED and not implemented. Its stack (Python + FastAPI) is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md); HC-130 creates the runtime.

## Responsibilities and owned concepts

- Hospital approval and registry. The Federation Service's node registry ([`node-registry.v1.yaml`](../../contracts/federation/node-registry.v1.yaml), HC-142) is only a routing directory: each registration cites a Governance approval decision, which the Federation Service cannot verify until this Node exposes an approval API (HC-131).
- Synchronization and research authorization. The Federation Service already calls [`sync-authorization-check.v1.yaml`](../../contracts/federation/sync-authorization-check.v1.yaml) on this Node before every synchronization-decision query (HC-144); until this Node implements it, those queries are refused with `503`.
- Policy evaluation, consent governance, and governance audit.
- OPTIONAL Blockchain Adapter behind an application-owned `AuditLedgerPort`.

## Communication boundaries

The Node receives versioned requests and issues explicit decisions/authorization artifacts. Ledger access is an outbound adapter and contains minimized proofs only.

## Non-responsibilities

It does not own raw hospital clinical databases, clinician workflows, patient medical-record editing, company self-approval, or research notebook execution.

## Expected contracts

The consumer-side [`research-authorization-check.v1.yaml`](../../contracts/api/research/research-authorization-check.v1.yaml) contract is IMPLEMENTED for HC-182, but this Node does not provide it yet. Hospital-registry, review/decision, other policy and authorization, audit-event, Federation, and immutable-proof contracts remain PLANNED.
