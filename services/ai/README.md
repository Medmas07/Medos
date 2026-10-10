# AI Services

## Purpose and status

Python + FastAPI is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-150). Clinical extraction is MOCKED (HC-152): `POST /v1/clinical-extractions` implements the [clinical extraction contract](../../contracts/api/ai/clinical-extraction.v1.yaml) with a deterministic fixture extractor. The provider-neutral `AiProvider` port is IMPLEMENTED (HC-151) with one MOCKED adapter. **No real AI capability is implemented.** AI libraries, providers, models, hosting, and API contracts are OPEN. All AI capabilities are PLANNED.

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

## AI provider port (HC-151, D1)

Use cases reach a model only through the `AiProvider` port in [`application/ai_provider.py`](application/ai_provider.py). It sits below task-level ports such as `ClinicalExtractor`: a future model-backed extractor calls `AiProvider` and turns its output into extraction items. The port is a `typing.Protocol`, so adapters do not import or subclass anything from the application layer:

| Member | Meaning |
|---|---|
| `describe() -> ProviderDescriptor` | Provider ID, model ID, `is_mock`, and supported `AiTask`s (`extraction`, `summarization`, `explanation`). |
| `generate(AiRequest) -> AdvisoryOutput` | Request ID, task, instructions, and input text in; advisory output out. |
| `AiProviderError(kind, message)` | The only error an adapter may raise. Kinds: `invalid_request`, `unsupported_task`, `unavailable`, `timeout`. Adapters translate SDK and transport errors into these. |

[`domain/advisory_output.py`](domain/advisory_output.py) defines what every output carries:

- **Provenance:** provider ID, model ID, `is_mock`, and generation time.
- **Uncertainty notes:** limitations the consumer must show next to the output.
- **Review state:** always `pending_human_review`. The port has no way to mark output as confirmed.

The only adapter is `DeterministicMockAiProvider` in [`adapters/outbound/mock_ai_provider.py`](adapters/outbound/mock_ai_provider.py). It is MOCKED. It returns a fixed `[MOCK]` template, never echoes the input text, and marks its provenance `is_mock: true`. It is not AI and not validated intelligence. A real provider adapter needs an ADR that selects the provider and model (HC-153). Its SDK then belongs in `adapters/outbound/` only, and the adapter must pass [`tests/test_ai_provider_contract.py`](tests/test_ai_provider_contract.py).

`GET http://localhost:8600/ai-provider` reports the configured provider, which is always the mock for now:

```json
{
  "provider_id": "deterministic-mock",
  "model_id": "none",
  "is_mock": true,
  "supported_tasks": ["explanation", "extraction", "summarization"],
  "notice": "Provider port only (HC-151). No AI capability is exposed. A mock provider is not validated intelligence, and any AI output is advisory and requires human review."
}
```

The port is internal to AI Services and is not a cross-component contract, so nothing is added under `contracts/`.

## Layout

```text
services/ai/
├── main.py                     # composition root: builds the FastAPI app
├── domain/                     # ServiceStatus, extraction draft rules, AdvisoryOutput — stdlib only
├── application/                # use cases, ClinicalExtractor and AiProvider ports — imports only domain
├── adapters/inbound/http/      # FastAPI routers and Pydantic models
├── adapters/outbound/          # FixtureClinicalExtractor, DeterministicMockAiProvider (MOCKED)
└── tests/                      # domain, use-case, HTTP/contract, and layer-boundary tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library. FastAPI and Pydantic belong in `adapters/` and `main.py` only.

## Responsibilities and owned concepts

Potential extraction, summarization, document review, lab interpretation assistance, priority explanation, medication explanation, and LLM orchestration behind explicit ports. The provider-neutral port is IMPLEMENTED with a mock adapter (HC-151). Real extraction (HC-153) is PLANNED.

## Communication boundaries

Provider SDKs stay in outbound adapters and outside Domain. Consumers use versioned request/result contracts with provenance and review state.

## Non-responsibilities

No AI output automatically becomes clinical truth. AI does not autonomously diagnose, prescribe, triage critical cases, approve institutions/research, or serve as the sole medication-safety source.

## Expected contracts

PLANNED provider-neutral extraction, explanation, review, provenance, error, and model-capability contracts.
