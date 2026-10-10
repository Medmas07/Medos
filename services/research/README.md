# Research Service

## Purpose and status

PLANNED company-managed orchestration capability for governed research projects and Compute-to-Data jobs. No runtime or execution code exists. The D1 Hospital Node execution contract is IMPLEMENTED in [`contracts/api/research/`](../../contracts/api/research/research-node-execution.v1.yaml), but no component serves or consumes it. When its first runtime ticket needs one, it is a separate Python + FastAPI project per [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md).

## Responsibilities and owned concepts

Potential project/request lifecycle, research-job orchestration, experiment state, controlled results, provenance, and research audit.

## Communication boundaries

Uses Governance authorization, Federation, Hospital Node execution, and SciAgents Integration contracts. Code moves to authorized data environments; controlled results return.

## Non-responsibilities

It does not approve its own access, directly query hospital databases, download unrestricted raw datasets, or execute inside Hospital Nodes without an authorized agent.

## Expected contracts

The Hospital Node execution slice of the research-job contract is IMPLEMENTED at D1: authorization context, bounded data scope, algorithm identity, aggregate-only output policy, execution states, controlled result, errors, and provenance. Research Service orchestration, Governance verification, cross-node aggregation, and portal-facing contracts remain PLANNED.
