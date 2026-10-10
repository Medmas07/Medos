# API Contracts

Place validated, versioned cross-component API specifications here, one directory per capability or providing component. A contract may exist before the component that provides it is decided; the table says so. File names carry the major version (`<name>.v<major>.yaml`); a breaking change creates a new file instead of editing the old one.

| Contract | Provider | Status |
|---|---|---|
| [`ai/clinical-extraction.v1.yaml`](ai/clinical-extraction.v1.yaml) | AI Services | IMPLEMENTED as OpenAPI 3.1; served only by a MOCKED fixture extractor (HC-152) |
| [`medication-safety/medication-safety-check.v1.yaml`](medication-safety/medication-safety-check.v1.yaml) | OPEN | IMPLEMENTED as OpenAPI 3.1 with fictional examples; no provider or implementation (HC-160) |
| [`sciagents/scientific-investigation.v1.yaml`](sciagents/scientific-investigation.v1.yaml) | SciAgents Integration adapter | IMPLEMENTED as OpenAPI 3.1 with fictional examples; adapter PLANNED (HC-170, HC-171) |

Every contract is checked by the repository [contract tests](../../tests/contracts/): it must be valid OpenAPI, and each embedded example must match its schema. The authentication convention for API contracts is OPEN.
