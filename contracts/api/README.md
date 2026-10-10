# API Contracts

Place validated, versioned cross-component API specifications here, one directory per capability or providing component. A contract may exist before the component that provides it is decided; the table says so. File names carry the major version (`<name>.v<major>.yaml`); a breaking change creates a new file instead of editing the old one.

| Contract | Provider | Status |
|---|---|---|
| [`ai/clinical-extraction.v1.yaml`](ai/clinical-extraction.v1.yaml) | AI Services | IMPLEMENTED as OpenAPI 3.1; served only by a MOCKED fixture extractor (HC-152) |
| [`medication-safety/medication-safety-check.v1.yaml`](medication-safety/medication-safety-check.v1.yaml) | OPEN | IMPLEMENTED as OpenAPI 3.1 with fictional examples; no provider or implementation (HC-160) |
| [`hospital-audit/hospital-audit-events.v1.yaml`](hospital-audit/hospital-audit-events.v1.yaml) | Every Hospital Node, for its own trail | IMPLEMENTED as OpenAPI 3.1 with fictional examples; served by the [Hospital Node runtime](../../instances/hospital-node/README.md#audit-event-api-hc-116) with events kept in memory and readers not authenticated (HC-116) |
| [`patient-access/patient-access-grants.v1.yaml`](patient-access/patient-access-grants.v1.yaml) | Every Hospital Node, for the grants it enforces | IMPLEMENTED as OpenAPI 3.1 with fictional examples; served by the [Hospital Node runtime](../../instances/hospital-node/README.md#access-grants-api-hc-115) over a MOCKED in-memory grant store, callers not authenticated (HC-115) |
| [`sciagents/scientific-investigation.v1.yaml`](sciagents/scientific-investigation.v1.yaml) | SciAgents Integration adapter | IMPLEMENTED as OpenAPI 3.1 with fictional examples; adapter PLANNED (HC-170, HC-171) |
| [`research/research-node-execution.v1.yaml`](research/research-node-execution.v1.yaml) | Every Hospital Node | IMPLEMENTED as OpenAPI 3.1 and consumed by the HC-182 Research Service HTTP adapter; no Hospital-side provider exists until HC-183 |
| [`research/research-job-orchestration.v1.yaml`](research/research-job-orchestration.v1.yaml) | Research Service | IMPLEMENTED by HC-182; process-local job state and separate controlled node outcomes |
| [`research/research-authorization-check.v1.yaml`](research/research-authorization-check.v1.yaml) | Governance Node | Consumer contract IMPLEMENTED for HC-182; provider remains PLANNED, so the orchestrator fails closed |

Every contract is checked by the repository [contract tests](../../tests/contracts/): it must be valid OpenAPI, and each embedded example must match its schema. The authentication convention for API contracts is OPEN.
