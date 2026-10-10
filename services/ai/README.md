# AI Services

## Purpose and status

Python + FastAPI is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-150): a runnable FastAPI service with a `GET /health` endpoint, framework-free Domain/Application layers, and tests. **No AI capability is implemented.** AI libraries, providers, models, hosting, and API contracts are OPEN. All AI capabilities are PLANNED.

## Running locally

From this directory (POSIX shell; on Windows activate with `.venv\Scripts\activate`):

| Purpose | Command |
|---|---|
| Create environment | `python3 -m venv .venv && . .venv/bin/activate` |
| Install (dev) | `pip install -r requirements-dev.txt` |
| Dev server with reload | `fastapi dev main.py --port 8600` |
| Tests | `pytest` |
| Lint / format check | `ruff check . && ruff format --check .` |
| Production-mode server (preview) | `fastapi run main.py --port 8600` |

`GET http://localhost:8600/health` returns:

```json
{
  "status": "ok",
  "service": "ai-services",
  "version": "0.1.0",
  "capabilities": [],
  "notice": "AI Services runtime skeleton. No AI capability is implemented. Any future AI output is advisory and requires review by an accountable human."
}
```

The empty `capabilities` list and the `notice` field make the D2 boundary visible: the service runs, but it has no intelligence. The OpenAPI document is served at `/openapi.json`.

## Layout

```text
services/ai/
├── main.py                     # composition root: builds the FastAPI app
├── domain/                     # ServiceStatus and the advisory notice — stdlib only
├── application/                # get_service_status use case — imports only domain
├── adapters/inbound/http/      # FastAPI router and Pydantic response model
└── tests/                      # use-case, HTTP, and layer-boundary tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library. FastAPI and Pydantic belong in `adapters/` and `main.py` only.

## Responsibilities and owned concepts

Potential extraction, summarization, document review, lab interpretation assistance, priority explanation, medication explanation, and LLM orchestration behind explicit ports. The provider-neutral port (HC-151) and the extraction contract (HC-152) are PLANNED and not part of this skeleton.

## Communication boundaries

Provider SDKs stay in outbound adapters and outside Domain. Consumers use versioned request/result contracts with provenance and review state.

## Non-responsibilities

No AI output automatically becomes clinical truth. AI does not autonomously diagnose, prescribe, triage critical cases, approve institutions/research, or serve as the sole medication-safety source.

## Expected contracts

PLANNED provider-neutral extraction, explanation, review, provenance, error, and model-capability contracts.
