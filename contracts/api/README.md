# API Contracts

Place validated, versioned cross-component API specifications here, one directory per providing component. File names carry the major version (`<name>.v<major>.yaml`); a breaking change creates a new file instead of editing the old one.

| Contract | Provider | Status |
|---|---|---|
| [`ai/clinical-extraction.v1.yaml`](ai/clinical-extraction.v1.yaml) | AI Services | IMPLEMENTED as OpenAPI 3.1; served only by a MOCKED fixture extractor (HC-152) |

The authentication convention for API contracts is OPEN.
