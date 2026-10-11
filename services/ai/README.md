# AI Services

## Purpose and status

Python + FastAPI is CONFIRMED by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md). The runtime skeleton is IMPLEMENTED (HC-150). **Real clinical extraction is IMPLEMENTED (HC-153, D3):** `POST /v1/clinical-extractions` implements the [clinical extraction contract](../../contracts/api/ai/clinical-extraction.v1.yaml) with Claude (through the Claude Agent SDK) as the primary provider and a local Ollama model as the fallback, as decided by [ADR-0006](../../docs/decisions/ADR-0006-ai-provider-strategy.md). The deterministic fixture extractor (HC-152) remains available as an explicit MOCKED mode. Extraction quality is **not clinically validated**; drafts are advisory and always pending clinician review. **LLM-assisted hospital document review is IMPLEMENTED (HC-154, D3):** `POST /v1/hospital-document-reviews` implements the [hospital document review contract](../../contracts/api/ai/hospital-document-review.v1.yaml) with the same providers; its findings are advisory and must cite the dossier. **Lab extraction is IMPLEMENTED (HC-155, D3):** `POST /v1/lab-extractions` implements the [lab extraction contract](../../contracts/api/ai/lab-extraction.v1.yaml); values are verified against the report and flags are computed deterministically, never by the model. **Medication warning explanation is IMPLEMENTED (HC-156, D3):** `POST /v1/medication-warning-explanations` implements the [medication warning explanation contract](../../contracts/api/ai/medication-warning-explanation.v1.yaml); model text is shown only if it passes deterministic checks, otherwise a template is. **Priority queue explanation is IMPLEMENTED (HC-157, D3):** `POST /v1/priority-queue-explanations` implements the [priority queue explanation contract](../../contracts/api/ai/priority-queue-explanation.v1.yaml); it puts a deterministic queue entry in words, never ranks, and its model text is checked the same way. Summarization and the other AI capabilities are PLANNED.

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
| `AI_LAB_MODE` | `model` | Lab extraction (HC-155): `model` calls real providers; `fixture` returns fixed results for the demo report only (MOCKED) |
| `AI_EXPLANATION_MODE` | `model` | Medication warning explanation (HC-156): `model` calls real providers and checks their text, falling back to the template; `template` uses only the deterministic template |
| `AI_PRIORITY_EXPLANATION_MODE` | `model` | Priority queue explanation (HC-157): the same two modes, set on their own |
| `AI_PROVIDERS` | `claude,ollama` | Provider order; the next one is tried only if one is unavailable or times out |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Claude model |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Local fallback model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `AI_PROVIDER_TIMEOUT_SECONDS` | `120` | Per-provider timeout |

For an offline, deterministic demo: `AI_EXTRACTION_MODE=fixture AI_REVIEW_MODE=fixture AI_LAB_MODE=fixture AI_EXPLANATION_MODE=template AI_PRIORITY_EXPLANATION_MODE=template fastapi dev main.py --port 8600`.

`GET http://localhost:8600/health` returns:

```json
{
  "status": "ok",
  "service": "ai-services",
  "version": "0.7.0",
  "capabilities": ["clinical-extraction:model", "hospital-document-review:model", "lab-extraction:model", "medication-warning-explanation:model", "priority-queue-explanation:model"],
  "notice": "Capabilities marked :model call a language model; capabilities marked :mocked return deterministic fictional fixtures. Any AI output is advisory and requires review by an accountable human."
}
```

In fixture mode the capabilities are `clinical-extraction:mocked`, `hospital-document-review:mocked`, and `lab-extraction:mocked`, and the explanations are `medication-warning-explanation:template` and `priority-queue-explanation:template`: a deterministic template is not a mock of the model, but it calls none. Each capability follows its own mode. The suffix and the `notice` field make the boundary visible. FastAPI's generated OpenAPI document is served at `/openapi.json`; the versioned contract under `contracts/` remains the source of truth.

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

## Lab extraction (HC-155)

`POST /v1/lab-extractions` turns a lab report's **text** into a draft of structured results for clinician review, in the shape a Hospital Node keeps them (`lab_reports` in [`hospital-node-federation.v1.yaml`](../../contracts/federation/hospital-node-federation.v1.yaml)): `test`, numeric `value`, `unit`, the `reference_range` printed with it, and a `flag`. Every draft is `advisory: true` and `pending_clinician_review`; a clinician confirms or corrects each result before it is used or stored.

**The model only reads.** `ModelLabExtractor` ([`application/model_lab_extractor.py`](application/model_lab_extractor.py)) asks the provider chain, as an `extraction` task, for each numeric result's test, value, unit, printed range, and the verbatim line. It is told not to judge abnormality and never to use a usual range, and its schema has no flag field.

**Verified and flagged here** ([`domain/lab_extraction.py`](domain/lab_extraction.py), applied by `ExtractLabResults` whatever the extractor):

- the quote must be found in the report (exactly, or ignoring case only), and the value must be one of the numbers printed in it (a decimal comma reads as a point); otherwise the result is dropped and counted in `unverified_results_dropped`;
- a range is kept only if both bounds are printed in the quote; otherwise the result has no range;
- `flag` is computed: below the range `low`, above it `high`, inside it `normal` (`flag_basis: reference_range`). Without a printed range the flag is `null` (`no_reference_range`). **The model is never the source of an abnormal flag**, as the product vision requires.

Numeric results only: qualitative ones ("négatif") are skipped. Known limit: verification checks that a value is printed in its quote, not that it is the result rather than one of the range bounds; clinician review covers this.

**Fixture mode (MOCKED).** With `AI_LAB_MODE=fixture`, `FixtureLabExtractor` ([`adapters/outbound/fixture_lab_extractor.py`](adapters/outbound/fixture_lab_extractor.py)) returns fixed results for `DEMO_LAB_REPORT`, Hospital B's fictional pre-treatment panel for Patient A (`lab-b-2026-leila`) as a report prints it, and nothing for any other text. Its results go through the same verification and flagging.

Errors: `400 invalid_request`, `503 extraction_unavailable`. Like the document review, the route parses its own body and runs the extraction in the threadpool.

Demo, with the service running:

```bash
python -c "from adapters.outbound.fixture_lab_extractor import DEMO_LAB_REPORT as t; import json; print(json.dumps({'patient_ref': 'pat-a', 'requested_by': 'clin-x', 'source': {'text': t}}))" > /tmp/lab.json
curl -s -X POST localhost:8600/v1/lab-extractions -H 'content-type: application/json' --data-binary @/tmp/lab.json
```

Checked live on 2026-10-11 with **Claude** (`claude-opus-5-5`, about 6 s) and with **Ollama** alone (`qwen2.5:3b`, 6 to 8 s). Both returned the demo panel's three seed values with their ranges, all `normal`. On a fictional control report (potassium 5,6 mmol/L (3,5 – 5,0), sodium 131 mmol/L (135 – 145), CRP 3 mg/L with no range, a qualitative albumin result), both gave potassium `high`, sodium `low`, CRP unflagged, and skipped the qualitative result; Ollama also proposed one row that failed verification and was dropped. Every answer conforms to the contract. Output varies between runs and models and is **not clinically validated**.

Not done: no clinician workflow calls it yet, and nothing is stored; scanned or PDF reports, unit normalization, and qualitative results.

## Medication warning explanation (HC-156)

`POST /v1/medication-warning-explanations` puts **one deterministic medication warning** in plain words for the clinician. It returns exactly the `Explanation` object that [`medication-safety-check.v1.yaml`](../../contracts/api/medication-safety/medication-safety-check.v1.yaml) reserves for AI Services in `Warning.explanation` (a test keeps the two schemas identical). **AI is never the safety source:** the warning's `rule_source.kind` can only be `deterministic_rule_set` or `validated_source`, and the explanation does not decide whether there is an interaction, how serious it is, or what to prescribe.

**Input.** The warning's content only: id, severity (`contraindicated`, `major`, `moderate`, `minor`), summary, the two medication names, and the rule source; plus an opaque `requested_by`. No patient reference or medication history.

**Model text is checked before it is shown** ([`domain/medication_explanation.py`](domain/medication_explanation.py), applied by `ExplainMedicationWarning`):

- it names both medications as given (case and accents ignored);
- it states the warning's own severity and names no other (whole words, French or English, so "majoration du risque" is not "major");
- it gives no dose, quantity, or frequency (a number with mg, mL, IU, tablets, "2 fois par jour", ...);
- it gives no recommendation or directive (recommend, avoid, do not combine, stop, replace, switch, ...): the warning carries none. Saying the decision to prescribe is the clinician's is allowed;
- it is at most 800 characters.

Text that fails any check is **discarded**: the deterministic template is returned instead (`generated_by.kind: deterministic_template`), and `rejected_reasons` says why. The same happens when no model answers or its output is not valid JSON, so this endpoint always answers `200` for a valid request and never returns unchecked model text. The template restates the warning: *"Interaction majeure entre Dolorane et Coagulix selon Règles fictives de démonstration (règle rule-coagulix-dolorane) : Risque hémorragique accru. La décision appartient au clinicien."* These are word and pattern checks: they catch these faults, not every unfaithful sentence, which is why the result stays advisory.

`ModelWarningExplainer` ([`application/model_warning_explainer.py`](application/model_warning_explainer.py)) sends the warning as an `explanation` task with instructions to explain only. `AI_EXPLANATION_MODE=template` uses `TemplateExplainer` and calls no model. A warning whose source is anything else (for example `llm`) is a `400`.

Demo, with the service running, on the canonical demo rule ([`demo-data/medication-rules.json`](../../demo-data/medication-rules.json), `rule-coagulix-dolorane`: Dolorane proposed for a patient taking Coagulix):

```bash
curl -s -X POST localhost:8600/v1/medication-warning-explanations -H 'content-type: application/json' -d '{
  "requested_by": "clin-x", "warning": {"warning_id": "warning-1", "type": "drug_drug_interaction",
  "severity": "major", "summary": "Risque hémorragique accru.",
  "proposed_medication": {"name": "Dolorane", "code": null},
  "conflicting_medication": {"name": "Coagulix", "code": null},
  "rule_source": {"kind": "deterministic_rule_set", "name": "Règles fictives de démonstration",
  "version": "1.0", "rule_id": "rule-coagulix-dolorane", "reference": null}}}'
```

Checked live on 2026-10-11 with the warning as `major` and as `moderate`. **Claude** (`claude-opus-5-5`, 4 to 7 s) explained both faithfully and passed every check ("interaction de sévérité majeure", "... modérée"). **Ollama** alone (`qwen2.5:3b`, about 1.5 s) had both texts replaced by the template: for the major warning it called the interaction merely "importante" (severity not stated), and for the moderate one it wrote that the advice is "de ne pas associer" the two medications, a recommendation the warning does not make. Those two runs are why the severity and directive checks exist. Every answer conforms to both contracts. Output varies between runs and models and is **not clinically validated**.

Hospital Nodes configured with this service's URL call this endpoint for each warning of their medication safety check (HC-162) and attach the result (HC-164).

Not done: explanations for patients; languages other than the warning's own.

## Priority queue explanation (HC-157)

`POST /v1/priority-queue-explanations` puts **one entry of a clinician's priority queue** in plain words: why the patient sits at this rank with this priority, given the factors the priority method used (product vision, section 19). **AI never ranks the queue:** the entry's `method.kind` can only be `deterministic_rule_set` or `deterministic_mock`, and the explanation does not set or change the rank, priority, or score, assess urgency, or triage. Critical triage must never rely on it. The `explanation` object has the same shape as the medication one.

**Input.** The entry as the method produced it: rank, priority (`high`, `medium`, `low`), optional score, 1 to 10 factors (id, type, short label, severity, optional weight), and the method; plus an opaque `requested_by`. No patient reference. **Factor ids are not sent to the model**: it sees factors as `F1`, `F2`, ... by position, because an id can carry meaning. An early live run had the demo id `alert-b-hba1c` turned into "sucre dans le sang persistant", which no factor says.

**Model text is checked before it is shown** ([`domain/priority_explanation.py`](domain/priority_explanation.py), applied by `ExplainPriorityEntry`):

- it cites every factor as `[F1]`, `[F2]`, ... and no other; citations are removed from the returned text;
- it states the entry's own priority ("priorité haute", "high priority", ...) and names no other. A factor's severity ("sévérité haute") is not a priority;
- every number in it is in the entry (rank, score, weights, number of factors, or the labels and method);
- it claims no urgency (urgent, critique, immédiat, vital, ...), interprets no condition (diagnostic, suggère, probable, mal contrôlé, aggravation, ...), and gives no directive (recommander, devrait, il faut, voir ... en premier, appeler, should, ...). Words that the entry's own labels or method description contain are allowed;
- it is at most 800 characters.

Text that fails any check is **discarded** and the deterministic template is returned, with `rejected_reasons`; the same happens when no model answers. The template restates the entry: *"Priorité haute, rang 1 dans la file, score 82, selon la méthode « Priorité fictive de démonstration » (version 1.0, simulée), à partir de : Résultat biologique anormal non revu (sévérité haute) ; Suivi en retard (sévérité moyenne). Ce classement n'est pas un triage clinique. La décision appartient au clinicien."* These are word and pattern checks: they catch these faults, not every unfaithful sentence. They cannot tell, for example, whether a model guessed the patient's sex; the prompt asks for "le patient".

`ModelPriorityExplainer` ([`application/model_priority_explainer.py`](application/model_priority_explainer.py)) sends the entry as an `explanation` task. `AI_PRIORITY_EXPLANATION_MODE=template` uses `TemplatePriorityExplainer` and calls no model. An entry whose method is anything else (for example `llm`) is a `400`, as is an unknown priority or factor type, a duplicate factor, or a patient reference.

Demo, with the service running, on the first entry of Dr X's fictional MOCKED queue ([`demo-data/clinician.json`](../../demo-data/clinician.json), `queue-clin-x-1`):

```bash
curl -s -X POST localhost:8600/v1/priority-queue-explanations -H 'content-type: application/json' -d '{
  "requested_by": "clin-x", "entry": {"entry_id": "queue-clin-x-1", "rank": 1, "priority": "high", "score": 82,
  "factors": [
    {"factor_id": "alert-b-hba1c", "type": "abnormal_lab", "label": "Résultat biologique anormal non revu", "severity": "high"},
    {"factor_id": "alert-b-followup", "type": "missed_follow_up", "label": "Suivi en retard", "severity": "medium"}],
  "method": {"kind": "deterministic_mock", "name": "Priorité fictive de démonstration", "version": "1.0"}}}'
```

Checked live on 2026-10-11 on both demo queue entries (`queue-clin-x-1`, high; `queue-clin-x-2`, medium, with "Traitement anticoagulant actif" as a `patient_context` factor). **Claude** (`claude-opus-5-5`, 7 to 9 s) explained both faithfully and passed every check. **Ollama** alone (`qwen2.5:3b`, 3 to 4 s) had the high entry replaced by the template in each of five runs, for giving the follow-up factor its own "priorité moyenne". Its medium-entry text passed, but it was loosely worded ("alerte de contexte important pour la prise en charge"). The checks are not a quality bar. Output varies between runs and models and is **not clinically validated**.

Not done: no Priority Engine exists, and no clinician product calls this API (HC-032, HC-044); explaining a whole queue or the order of two entries; explanations for patients.

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
├── domain/                     # ServiceStatus, extraction, document review, lab extraction, medication and priority explanation rules, AdvisoryOutput — stdlib only
├── application/                # use cases, ports, model-backed extractors, reviewer, and explainers, FallbackAiProvider — imports only domain
├── adapters/inbound/http/      # FastAPI routers and Pydantic models
├── adapters/outbound/          # Claude, Ollama, and mock providers; FixtureClinicalExtractor, FixtureDocumentReviewer, and FixtureLabExtractor (MOCKED)
├── infrastructure/settings.py  # environment configuration (no secrets)
└── tests/                      # unit, HTTP/contract, provider-contract, layer-boundary, and opt-in live tests
```

`tests/test_layer_boundaries.py` fails if `domain/` or `application/` imports anything other than inner layers or the standard library. FastAPI, Pydantic, `httpx`, and `claude_agent_sdk` belong in `adapters/`, `infrastructure/`, and `main.py` only.

## Responsibilities and owned concepts

Potential extraction, summarization, document review, lab interpretation assistance, priority explanation, medication explanation, and LLM orchestration behind explicit ports. Clinical extraction (HC-153), hospital document review (HC-154), lab extraction (HC-155), medication warning explanation (HC-156), and priority queue explanation (HC-157) are IMPLEMENTED with real providers; the other capabilities are PLANNED.

## Communication boundaries

Provider SDKs stay in outbound adapters and outside Domain. Consumers use versioned request/result contracts with provenance and review state.

## Non-responsibilities

No AI output automatically becomes clinical truth. AI does not autonomously diagnose, prescribe, triage critical cases, approve institutions/research, or serve as the sole medication-safety source.

## Expected contracts

[`clinical-extraction.v1.yaml`](../../contracts/api/ai/clinical-extraction.v1.yaml) (HC-152) [`hospital-document-review.v1.yaml`](../../contracts/api/ai/hospital-document-review.v1.yaml) (HC-154), [`lab-extraction.v1.yaml`](../../contracts/api/ai/lab-extraction.v1.yaml) (HC-155), [`medication-warning-explanation.v1.yaml`](../../contracts/api/ai/medication-warning-explanation.v1.yaml) (HC-156), and [`priority-queue-explanation.v1.yaml`](../../contracts/api/ai/priority-queue-explanation.v1.yaml) (HC-157). Model-capability contracts are PLANNED.
