# AI Services

## Purpose and status

Python + FastAPI is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-150). **Real clinical extraction is IMPLEMENTED (HC-153, D3):** `POST /v1/clinical-extractions` implements the [clinical extraction contract](../../contracts/api/ai/clinical-extraction.v1.yaml) with Claude (through the Claude Agent SDK) as the primary provider and a local Ollama model as the fallback, as decided by [ADR-0006](../../docs/decisions/ADR-0006-ai-provider-strategy.md). The deterministic fixture extractor (HC-152) remains available as an explicit MOCKED mode. Extraction quality is **not clinically validated**; drafts are advisory and always pending clinician review. **LLM-assisted hospital document review is IMPLEMENTED (HC-154, D3):** `POST /v1/hospital-document-reviews` implements the [hospital document review contract](../../contracts/api/ai/hospital-document-review.v1.yaml) with the same providers; its findings are advisory and must cite the dossier. Summarization, explanation, and the other AI capabilities are PLANNED.

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
| `AI_REVIEW_MODE` | `model` | Hospital document review (HC-154): `model` calls real providers; `fixture` applies deterministic rules (MOCKED) |
| `AI_PROVIDERS` | `claude,ollama` | Provider order; the next one is tried only if one is unavailable or times out |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Claude model |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Local fallback model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `AI_PROVIDER_TIMEOUT_SECONDS` | `120` | Per-provider timeout |

For an offline, deterministic demo: `AI_EXTRACTION_MODE=fixture AI_REVIEW_MODE=fixture fastapi dev main.py --port 8600`.

`GET http://localhost:8600/health` returns:

```json
{
  "status": "ok",
  "service": "ai-services",
  "version": "0.4.0",
  "capabilities": ["clinical-extraction:model", "hospital-document-review:model"],
  "notice": "Capabilities marked :model call a language model; capabilities marked :mocked return deterministic fictional fixtures. Any AI output is advisory and requires review by an accountable human."
}
```

In fixture mode the capabilities are `clinical-extraction:mocked` and `hospital-document-review:mocked`; each follows its own mode. The suffix and the `notice` field make the boundary visible. FastAPI's generated OpenAPI document is served at `/openapi.json`; the versioned contract under `contracts/` remains the source of truth.

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

## Hospital document review (HC-154)

The optional review step of hospital onboarding (product vision §4): after the deterministic completeness check, before human review by the Governance / Ethics Authority. `POST /v1/hospital-document-reviews` takes the onboarding dossier and returns **advisory findings** for the human reviewer: `inconsistency`, `missing_information`, or `clarification_needed`. It never approves, rejects, scores, or ranks an application; the response has no field that could, and `advisory: true` and `review_status: pending_human_review` are fixed.

**Input.** The dossier is generic so AI Services does not depend on a portal's data model: up to 200 `fields` (a lower-case dotted `path`, for example `administrative_profile.security_contact`, and a string, number, boolean, or `null` value) and up to 10 `documents` (reference, type, title, status, and optional extracted `text`). It is administrative and technical, never clinical: callers must not send patient data. Missing documents and agreements are the completeness check's (Hospital Portal, HC-057); the review only looks across the answers.

**Every finding cites the dossier.** `ModelDocumentReviewer` ([`application/model_document_reviewer.py`](application/model_document_reviewer.py)) sends the dossier, instructions, and a JSON Schema to the provider chain with the `review` task. The instructions forbid deciding or recommending and ask for exact field paths and verbatim quotes. `ReviewHospitalDocuments` ([`application/review_hospital_documents.py`](application/review_hospital_documents.py)) then checks every proposed finding, whatever the reviewer: a field path must exist in the request, and a quote must be found in that document's text (exactly, or ignoring case only). Citations that do not hold are removed; a finding left with none is **dropped** and counted in `unverified_findings_dropped`, never shown. Provenance names the provider and model that answered.

**Fixture mode (MOCKED).** With `AI_REVIEW_MODE=fixture`, `FixtureDocumentReviewer` ([`adapters/outbound/fixture_document_reviewer.py`](adapters/outbound/fixture_document_reviewer.py)) applies fixed rules like the portal's simulated review (no security contact, no DMI test environment, outbound HTTPS refused), labelled `deterministic_fixture`, `mocked: true`, with a note that no model was called.

Errors: `400 invalid_request` for a request outside the contract (parsed by the route itself, so the extraction route keeps its own validation answers); `503 review_unavailable` when no provider answers or the output is not valid JSON. The review runs in the threadpool, because the Claude adapter starts its own event loop.

Demo, with the service running in model mode, on Hospital C's fictional dossier (the contract's `hospitalC` request example: its seed fields, plus a fictional architecture document giving another database version):

```bash
python - <<'PY' > /tmp/hospital-c.json
import json, yaml
c = yaml.safe_load(open("../../contracts/api/ai/hospital-document-review.v1.yaml"))
op = c["paths"]["/v1/hospital-document-reviews"]["post"]
print(json.dumps(op["requestBody"]["content"]["application/json"]["examples"]["hospitalC"]["value"]))
PY
curl -s -X POST localhost:8600/v1/hospital-document-reviews \
  -H 'content-type: application/json' --data-binary @/tmp/hospital-c.json
```

Checked live on 2026-10-10. **Claude** (`claude-opus-5-5`, about 10 s) returned four findings, all cited, none dropped: the declared PostgreSQL 13 against the architecture document's PostgreSQL 12 (with the verbatim quote), the missing security contact, HL7v2 declared while the notes and document describe only nightly file exports, and how the DMI integration will be validated without a test environment. **Ollama** alone (`qwen2.5:3b`, about 8 s) returned one vague finding, in English rather than the dossier's French, quoting the whole document. Both answers conform to the contract. Output varies between runs and models and is **not validated**; a finding is a prompt for the reviewer, not a fact about the hospital.

Not done: the Hospital Portal's assisted review (HC-057) still uses its SIMULATED rules and does not call this API; the Governance Node does not record these findings on applications; text extraction from uploaded files; authentication of callers; recording reviews.

## AI provider port and adapters (HC-151, HC-153)

Use cases reach a model only through the `AiProvider` port in [`application/ai_provider.py`](application/ai_provider.py). It sits below task-level ports such as `ClinicalExtractor`: a future model-backed extractor calls `AiProvider` and turns its output into extraction items. The port is a `typing.Protocol`, so adapters do not import or subclass anything from the application layer:

| Member | Meaning |
|---|---|
| `describe() -> ProviderDescriptor` | Provider ID, model ID, `is_mock`, and supported `AiTask`s (`extraction`, `summarization`, `explanation`, `review`). |
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
  "supported_tasks": ["explanation", "extraction", "review", "summarization"],
  "notice": "Configured AI provider chain (ADR-0006). A mock provider is not validated intelligence, and any AI output is advisory and requires human review."
}
```

The port is internal to AI Services and is not a cross-component contract, so nothing is added under `contracts/`.

## Layout

```text
services/ai/
├── main.py                     # composition root: create_app(settings) wires providers and routes
├── domain/                     # ServiceStatus, extraction draft and document review rules, AdvisoryOutput — stdlib only
├── application/                # use cases, ports, ModelClinicalExtractor, ModelDocumentReviewer, FallbackAiProvider — imports only domain
├── adapters/inbound/http/      # FastAPI routers and Pydantic models
├── adapters/outbound/          # Claude, Ollama, and mock providers; FixtureClinicalExtractor and FixtureDocumentReviewer (MOCKED)
├── infrastructure/settings.py  # environment configuration (no secrets)
└── tests/                      # unit, HTTP/contract, provider-contract, layer-boundary, and opt-in live tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library. FastAPI, Pydantic, `httpx`, and `claude_agent_sdk` belong in `adapters/`, `infrastructure/`, and `main.py` only.

## Responsibilities and owned concepts

Potential extraction, summarization, document review, lab interpretation assistance, priority explanation, medication explanation, and LLM orchestration behind explicit ports. Clinical extraction (HC-153) and hospital document review (HC-154) are IMPLEMENTED with real providers; the other capabilities are PLANNED.

## Communication boundaries

Provider SDKs stay in outbound adapters and outside Domain. Consumers use versioned request/result contracts with provenance and review state.

## Non-responsibilities

No AI output automatically becomes clinical truth. AI does not autonomously diagnose, prescribe, triage critical cases, approve institutions/research, or serve as the sole medication-safety source.

## Expected contracts

[`clinical-extraction.v1.yaml`](../../contracts/api/ai/clinical-extraction.v1.yaml) (HC-152) and [`hospital-document-review.v1.yaml`](../../contracts/api/ai/hospital-document-review.v1.yaml) (HC-154). Explanation and model-capability contracts are PLANNED.
