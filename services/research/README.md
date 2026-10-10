# Research Service

## Purpose and status

MOCKED D2 company-managed orchestration capability for governed research projects and Compute-to-Data jobs. A small Python + FastAPI runtime coordinates deterministic fictional node responses; it does not execute code, access hospital storage, or claim production readiness. The D1 Hospital Node execution contract is IMPLEMENTED in [`contracts/api/research/`](../../contracts/api/research/research-node-execution.v1.yaml).

## Responsibilities and owned concepts

Potential project/request lifecycle, research-job orchestration, experiment state, controlled results, provenance, and research audit.

## Communication boundaries

Uses Governance authorization, Federation, Hospital Node execution, and SciAgents Integration contracts. Code moves to authorized data environments; controlled results return.

## Non-responsibilities

It does not approve its own access, directly query hospital databases, download unrestricted raw datasets, or execute inside Hospital Nodes without an authorized agent.

## Expected contracts

The Hospital Node execution slice of the research-job contract is IMPLEMENTED at D1. HC-181 adds a MOCKED D2 Research Service endpoint: `POST /v1/research-jobs` accepts a bounded job request and `GET /v1/research-jobs/{job_ref}` advances deterministic stages for Governance authorization, Hospital A/B execution, aggregation, and output validation. It exposes explicit queued, running, completed, denied, empty, failed, and not-found behavior. Real execution, Governance verification, sandboxing, persistence, and portal contracts remain PLANNED/OPEN.

Run from this directory with `uvicorn main:app --port 8400`. The demo uses only fictional `job-001`, `proj-001`, `org-hospital-a`, and `org-hospital-b` references.
