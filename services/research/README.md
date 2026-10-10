# Research Service

## Purpose and status

D3 company-managed orchestration capability for governed research projects and Compute-to-Data jobs. The Python + FastAPI runtime coordinates participating Hospital Nodes through the application-owned execution port and HTTP adapter; it does not access hospital storage or claim production readiness. The D1 Hospital Node execution contract is IMPLEMENTED in [`contracts/api/research/`](../../contracts/api/research/research-node-execution.v1.yaml).

## Responsibilities and owned concepts

Potential project/request lifecycle, research-job orchestration, experiment state, controlled results, provenance, and research audit.

## Communication boundaries

Uses Governance authorization, Federation, Hospital Node execution, and SciAgents Integration contracts. Code moves to authorized data environments; controlled results return.

## Non-responsibilities

It does not approve its own access, directly query hospital databases, download unrestricted raw datasets, or execute inside Hospital Nodes without an authorized agent.

## Expected contracts

The Hospital Node execution slice of the research-job contract is IMPLEMENTED at D1. HC-182 adds the D3 Research Service orchestrator: `POST /v1/research-jobs` accepts a bounded job request and `GET /v1/research-jobs/{job_ref}` coordinates each configured node through the HC-180 port, tracks per-node execution references, waits for terminal node responses, and aggregates controlled results. Node transport failures and denials remain explicit. Test doubles are confined to tests; the delivered runtime uses `HttpHospitalNodeExecutionAdapter`.

Run from this directory with `HOSPITAL_NODE_A_URL=http://localhost:8101 HOSPITAL_NODE_B_URL=http://localhost:8102 uvicorn main:app --port 8400`. The demo uses only fictional `job-001`, `proj-001`, `org-hospital-a`, and `org-hospital-b` references.
