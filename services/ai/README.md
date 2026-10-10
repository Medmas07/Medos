# AI Services

## Purpose and status

Python + FastAPI is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-150). Clinical extraction is MOCKED (HC-152): `POST /v1/clinical-extractions` implements the [clinical extraction contract](../../contracts/api/ai/clinical-extraction.v1.yaml) with a deterministic fixture extractor. **No real AI capability is implemented.** AI libraries, providers, models, hosting, and API contracts are OPEN. All AI capabilities are PLANNED.

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
  "version": "0.2.0",
  "capabilities": ["clinical-extraction:mocked"],
  "notice": "No real AI capability is implemented; capabilities marked :mocked return deterministic fictional fixtures. Any AI output is advisory and requires review by an accountable human."
}
```

The `:mocked` suffix and the `notice` field make the boundary visible. FastAPI's generated OpenAPI document is served at `/openapi.json`; the versioned contract under `contracts/` remains the source of truth.

## Clinical extraction (MOCKED, D1)

`POST /v1/clinical-extractions` takes clinical source text (`transcript`, `physician_note`, or `lab_report`) and opaque references, and returns a **draft** of extracted items: symptoms, observations, measurements, medications, mentioned diagnoses, follow-up actions, and missing information. Each item quotes its evidence span in the source text.

Every draft has `review_status: pending_clinician_review` and `advisory: true`. AI Services never confirms clinical data; confirmation belongs to the clinician workflow that consumes the draft.

At D1 the only extractor is `FixtureClinicalExtractor` (`provenance.mocked: true`):

- the fictional demo transcript in [`adapters/outbound/fixture_extractor.py`](adapters/outbound/fixture_extractor.py) (Patient A, seen by Dr. X) returns 7 items and 2 missing-information prompts;
- any other text returns an empty draft (`items: []`), which the contract defines as "nothing extracted", not "clinically unremarkable";
- invalid requests return `400` with `application/problem+json` and `code: invalid_request`.

To try it, start the dev server and send the demo transcript:

```bash
T=$(python -c "from adapters.outbound.fixture_extractor import DEMO_TRANSCRIPT as t; import json; print(json.dumps(t))")
curl -s -X POST localhost:8600/v1/clinical-extractions -H 'content-type: application/json' \
  -d "{\"patient_ref\":\"patient-a\",\"requested_by\":\"dr-x\",\"source\":{\"type\":\"transcript\",\"text\":$T}}"
```

`tests/test_clinical_extraction_http.py` validates requests and responses against the contract file with JSON Schema.

The `ClinicalExtractor` port in `application/extract_clinical_information.py` is what HC-153 implements with a real extractor, using the provider port from HC-151.

## Layout

```text
services/ai/
├── main.py                     # composition root: builds the FastAPI app
├── domain/                     # ServiceStatus, extraction draft rules — stdlib only
├── application/                # use cases and the ClinicalExtractor port — imports only domain
├── adapters/inbound/http/      # FastAPI routers and Pydantic models
├── adapters/outbound/          # FixtureClinicalExtractor (MOCKED)
└── tests/                      # domain, use-case, HTTP/contract, and layer-boundary tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library. FastAPI and Pydantic belong in `adapters/` and `main.py` only.

## Responsibilities and owned concepts

Potential extraction, summarization, document review, lab interpretation assistance, priority explanation, medication explanation, and LLM orchestration behind explicit ports. The provider-neutral port (HC-151) and real extraction (HC-153) are PLANNED.

## Communication boundaries

Provider SDKs stay in outbound adapters and outside Domain. Consumers use versioned request/result contracts with provenance and review state.

## Non-responsibilities

No AI output automatically becomes clinical truth. AI does not autonomously diagnose, prescribe, triage critical cases, approve institutions/research, or serve as the sole medication-safety source.

## Expected contracts

PLANNED provider-neutral extraction, explanation, review, provenance, error, and model-capability contracts.
