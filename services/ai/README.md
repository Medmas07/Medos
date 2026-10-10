# AI Services

## Purpose and status

Python + FastAPI is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-150). **Real clinical extraction is IMPLEMENTED (HC-153, D3):** `POST /v1/clinical-extractions` implements the [clinical extraction contract](../../contracts/api/ai/clinical-extraction.v1.yaml) with Claude (through the Claude Agent SDK) as the primary provider and a local Ollama model as the fallback, as decided by [ADR-0006](../../docs/decisions/ADR-0006-ai-provider-strategy.md). The deterministic fixture extractor (HC-152) remains available as an explicit MOCKED mode. Extraction quality is **not clinically validated**; drafts are advisory and always pending clinician review. Summarization, explanation, and the other AI capabilities are PLANNED.

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
| Live provider tests (opt-in) | `AI_LIVE_TESTS=1 pytest tests/test_live_providers.py` |

### Providers and configuration

Model mode (the default) needs at least one working provider:

- **Claude:** the [Claude Code CLI](https://code.claude.com/docs) installed and logged in (`claude`). The Claude Agent SDK uses that login; **no API key is configured or stored**.
- **Ollama:** `ollama serve` running and the model pulled: `ollama pull qwen2.5:3b`.

Configuration comes from environment variables; [`.env.example`](.env.example) lists them with their defaults. None is a secret.

| Variable | Default | Meaning |
|---|---|---|
| `AI_EXTRACTION_MODE` | `model` | `model` calls real providers; `fixture` returns the deterministic demo fixture (MOCKED) |
| `AI_PROVIDERS` | `claude,ollama` | Provider order; the next one is tried only if one is unavailable or times out |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Claude model |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Local fallback model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `AI_PROVIDER_TIMEOUT_SECONDS` | `120` | Per-provider timeout |

For an offline, deterministic demo: `AI_EXTRACTION_MODE=fixture fastapi dev main.py --port 8600`.

`GET http://localhost:8600/health` returns:

```json
{
  "status": "ok",
  "service": "ai-services",
  "version": "0.3.0",
  "capabilities": ["clinical-extraction:model"],
  "notice": "Capabilities marked :model call a language model; capabilities marked :mocked return deterministic fictional fixtures. Any AI output is advisory and requires review by an accountable human."
}
```

In fixture mode the capability is `clinical-extraction:mocked`. The suffix and the `notice` field make the boundary visible. FastAPI's generated OpenAPI document is served at `/openapi.json`; the versioned contract under `contracts/` remains the source of truth.

## Clinical extraction (HC-152 contract, HC-153 real extraction)

`POST /v1/clinical-extractions` takes clinical source text (`transcript`, `physician_note`, or `lab_report`) and opaque references, and returns a **draft** of extracted items: symptoms, observations, measurements, medications, mentioned diagnoses, follow-up actions, and missing information. Each item quotes its evidence span in the source text.

Every draft has `review_status: pending_clinician_review` and `advisory: true`. AI Services never confirms clinical data; confirmation belongs to the clinician workflow that consumes the draft.

### Model mode (default, HC-153)

`ModelClinicalExtractor` ([`application/model_clinical_extractor.py`](application/model_clinical_extractor.py)) sends the source text, instructions, and a JSON Schema to the provider chain, then checks the answer:

- items must have a known category and an `evidence_quote` found in the source text (exactly, or ignoring case only); **items whose quote is not found are dropped**, so the draft never shows a claim the clinician cannot check;
- `value`, `unit`, and `abnormal` are kept only when well-typed; `abnormal` is a suggestion for review;
- `confidence` is always `null`, because self-reported model confidence is not calibrated;
- `provenance.extractor` names the provider and model that actually answered (`kind: model`, `mocked: false`);
- if no provider answers, or the output is not valid JSON, the API returns `503` with `code: extraction_unavailable`.

The model output is not deterministic and not clinically validated.

### Fixture mode (MOCKED, HC-152)

With `AI_EXTRACTION_MODE=fixture`, `FixtureClinicalExtractor` (`provenance.mocked: true`) returns 7 items and 2 missing-information prompts for the fictional demo transcript in [`adapters/outbound/fixture_extractor.py`](adapters/outbound/fixture_extractor.py) (Patient A, seen by Dr. X), and an empty draft for any other text.

To try either mode, start the server and send the demo transcript:

```bash
T=$(python -c "from adapters.outbound.fixture_extractor import DEMO_TRANSCRIPT as t; import json; print(json.dumps(t))")
curl -s -X POST localhost:8600/v1/clinical-extractions -H 'content-type: application/json' \
  -d "{\"patient_ref\":\"patient-a\",\"requested_by\":\"dr-x\",\"source\":{\"type\":\"transcript\",\"text\":$T}}"
```

Invalid requests return `400` with `application/problem+json` and `code: invalid_request`. Requests and responses are validated against the contract file in `tests/test_clinical_extraction_http.py` and `tests/test_model_extraction_http.py`.

## AI provider port and adapters (HC-151, HC-153)

Use cases reach a model only through the `AiProvider` port in [`application/ai_provider.py`](application/ai_provider.py). It sits below task-level ports such as `ClinicalExtractor`: a future model-backed extractor calls `AiProvider` and turns its output into extraction items. The port is a `typing.Protocol`, so adapters do not import or subclass anything from the application layer:

| Member | Meaning |
|---|---|
| `describe() -> ProviderDescriptor` | Provider ID, model ID, `is_mock`, and supported `AiTask`s (`extraction`, `summarization`, `explanation`). |
| `generate(AiRequest) -> AdvisoryOutput` | Request ID, task, instructions, input text, and an optional `output_schema` (JSON Schema) in; advisory output out. Adapters use native structured output when a schema is given. |
| `AiProviderError(kind, message)` | The only error an adapter may raise. Kinds: `invalid_request`, `unsupported_task`, `unavailable`, `timeout`. Adapters translate SDK and transport errors into these. |

[`domain/advisory_output.py`](domain/advisory_output.py) defines what every output carries:

- **Provenance:** provider ID, model ID, `is_mock`, and generation time.
- **Uncertainty notes:** limitations the consumer must show next to the output.
- **Review state:** always `pending_human_review`. The port has no way to mark output as confirmed.

Adapters, all in `adapters/outbound/` and all passing [`tests/test_ai_provider_contract.py`](tests/test_ai_provider_contract.py):

| Adapter | Provider | Notes |
|---|---|---|
| `ClaudeAgentSdkProvider` | Claude via the Claude Agent SDK | Uses the local Claude Code login. Runs with no tools (`tools=[]`), no user or project settings (`setting_sources=[]`), and the request's schema as `output_format`. Source text is sent to Anthropic. |
| `OllamaAiProvider` | Local Ollama server | `POST /api/chat` with the schema as `format` and temperature 0. Text stays on the machine. |
| `DeterministicMockAiProvider` | none (MOCKED) | Fixed `[MOCK]` template, used in fixture mode. Not AI. |

`FallbackAiProvider` ([`application/fallback_ai_provider.py`](application/fallback_ai_provider.py)) implements the same port over an ordered list. It moves on only for `unavailable` or `timeout`, never for an invalid request, and adds an uncertainty note naming the providers that failed.

`GET http://localhost:8600/ai-provider` reports the configured chain, for example:

```json
{
  "provider_id": "claude-agent-sdk > ollama",
  "model_id": "claude-opus-5-5 > qwen2.5:3b",
  "is_mock": false,
  "supported_tasks": ["explanation", "extraction", "summarization"],
  "notice": "Configured AI provider chain (ADR-0006). A mock provider is not validated intelligence, and any AI output is advisory and requires human review."
}
```

The port is internal to AI Services and is not a cross-component contract, so nothing is added under `contracts/`.

## Layout

```text
services/ai/
├── main.py                     # composition root: create_app(settings) wires providers and routes
├── domain/                     # ServiceStatus, extraction draft rules, AdvisoryOutput — stdlib only
├── application/                # use cases, ports, ModelClinicalExtractor, FallbackAiProvider — imports only domain
├── adapters/inbound/http/      # FastAPI routers and Pydantic models
├── adapters/outbound/          # Claude, Ollama, and mock providers; FixtureClinicalExtractor (MOCKED)
├── infrastructure/settings.py  # environment configuration (no secrets)
└── tests/                      # unit, HTTP/contract, provider-contract, layer-boundary, and opt-in live tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library. FastAPI, Pydantic, `httpx`, and `claude_agent_sdk` belong in `adapters/`, `infrastructure/`, and `main.py` only.

## Responsibilities and owned concepts

Potential extraction, summarization, document review, lab interpretation assistance, priority explanation, medication explanation, and LLM orchestration behind explicit ports. Clinical extraction is IMPLEMENTED with real providers (HC-153); the other capabilities are PLANNED.

## Communication boundaries

Provider SDKs stay in outbound adapters and outside Domain. Consumers use versioned request/result contracts with provenance and review state.

## Non-responsibilities

No AI output automatically becomes clinical truth. AI does not autonomously diagnose, prescribe, triage critical cases, approve institutions/research, or serve as the sole medication-safety source.

## Expected contracts

PLANNED provider-neutral extraction, explanation, review, provenance, error, and model-capability contracts.
