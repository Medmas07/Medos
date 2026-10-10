# AI Services

## Purpose and status

Python + FastAPI is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-150): a runnable FastAPI service with a `GET /health` endpoint, framework-free Domain/Application layers, and tests. The provider-neutral `AiProvider` port is IMPLEMENTED (HC-151) with one MOCKED adapter. **No AI capability is implemented.** AI libraries, providers, models, hosting, and API contracts are OPEN. All AI capabilities are PLANNED.

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

`GET http://localhost:8600/ai-provider` reports the configured provider. It is always the mock for now:

```json
{
  "provider_id": "deterministic-mock",
  "model_id": "none",
  "is_mock": true,
  "supported_tasks": ["explanation", "extraction", "summarization"],
  "notice": "Provider port only (HC-151). No AI capability is exposed. A mock provider is not validated intelligence, and any AI output is advisory and requires human review."
}
```

## AI provider port (HC-151, D1)

Use cases reach a model only through the `AiProvider` port in [`application/ai_provider.py`](application/ai_provider.py). The port is a `typing.Protocol`, so adapters do not import or subclass anything from the application layer:

| Member | Meaning |
|---|---|
| `describe() -> ProviderDescriptor` | Provider ID, model ID, `is_mock`, and supported `AiTask`s (`extraction`, `summarization`, `explanation`). |
| `generate(AiRequest) -> AdvisoryOutput` | Request ID, task, instructions, and input text in; advisory output out. |
| `AiProviderError(kind, message)` | The only error an adapter may raise. Kinds: `invalid_request`, `unsupported_task`, `unavailable`, `timeout`. Adapters translate SDK and transport errors into these. |

[`domain/advisory_output.py`](domain/advisory_output.py) defines what every output carries:

- **Provenance:** provider ID, model ID, `is_mock`, and generation time.
- **Uncertainty notes:** limitations the consumer must show next to the output.
- **Review state:** always `pending_human_review`. The port has no way to mark output as confirmed. Review outcomes belong to the review workflow (HC-152+).

The only adapter is `DeterministicMockAiProvider` in [`adapters/outbound/mock_ai_provider.py`](adapters/outbound/mock_ai_provider.py). It is MOCKED. It returns a fixed `[MOCK]` template, never echoes the input text, and marks its provenance `is_mock: true`. It is not AI and not validated intelligence. `main.py` wires it in. A real provider adapter needs an ADR that selects the provider and model (HC-153). Its SDK then belongs in `adapters/outbound/` only, and the adapter must pass [`tests/test_ai_provider_contract.py`](tests/test_ai_provider_contract.py).

The port is internal to AI Services. It is not a cross-component contract, so nothing is added under `contracts/`. The external extraction contract is HC-152.

## Layout

```text
services/ai/
├── main.py                     # composition root: builds the FastAPI app
├── domain/                     # ServiceStatus, AdvisoryOutput, Provenance — stdlib only
├── application/                # get_service_status use case and AiProvider port — imports only domain
├── adapters/inbound/http/      # FastAPI routers and Pydantic response models
├── adapters/outbound/          # DeterministicMockAiProvider (MOCKED)
└── tests/                      # use-case, port-contract, HTTP, and layer-boundary tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library. FastAPI and Pydantic belong in `adapters/` and `main.py` only.

## Responsibilities and owned concepts

Potential extraction, summarization, document review, lab interpretation assistance, priority explanation, medication explanation, and LLM orchestration behind explicit ports. The provider-neutral port is IMPLEMENTED with a mock adapter (HC-151). The extraction contract (HC-152) is PLANNED.

## Communication boundaries

Provider SDKs stay in outbound adapters and outside Domain. Consumers use versioned request/result contracts with provenance and review state.

## Non-responsibilities

No AI output automatically becomes clinical truth. AI does not autonomously diagnose, prescribe, triage critical cases, approve institutions/research, or serve as the sole medication-safety source.

## Expected contracts

PLANNED provider-neutral extraction, explanation, review, provenance, error, and model-capability contracts.
