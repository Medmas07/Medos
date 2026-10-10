# ADR-0006: AI provider strategy — Claude first, local Ollama fallback

## Status

Accepted — 2026-10-10, chosen by the HC-153 assignee during HC-153 ([#128](https://github.com/Medmas07/Hackcure_hackathon/issues/128)); subject to pull-request review.

## Context

HC-151 defined a provider-neutral `AiProvider` port in `services/ai/` with only a deterministic mock adapter. HC-152 defined the clinical extraction contract with only a fixture extractor. HC-153 requires real clinical extraction. AGENTS.md keeps AI providers and models OPEN until an ADR decides them.

Forces:

- **Quality:** extraction must return schema-valid structured data whose evidence quotes match the source text.
- **No secrets in the repository**, and nothing for contributors to configure beyond tools they already use.
- **Data boundary:** whether clinical text may leave the hospital boundary is OPEN ([OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md)). The demo uses only fictional data.
- **Availability during a live demo:** a cloud call can fail (network, login, rate limits), and the demo should not depend on one provider.
- **Clean / Hexagonal Architecture:** provider SDKs stay in outbound adapters; application logic must not depend on a provider.

## Decision

1. **Primary provider: Claude through the Claude Agent SDK** (`claude-agent-sdk`, Python), model `claude-opus-5-5`. The SDK drives the locally installed Claude Code CLI and uses its existing login, so the service needs no API key. The adapter runs the agent as a plain text-in, JSON-out call: no built-in tools (`tools=[]`), no user or project settings (`setting_sources=[]`), a turn limit, and the extraction JSON Schema as `output_format`.
2. **Fallback provider: a local model served by Ollama**, default `qwen2.5:3b` (about 1.9 GB; chosen over `qwen2.5:7b` because the 4.7 GB download was impractical on the network used for validation, and configurable through `OLLAMA_MODEL`), called over Ollama's HTTP API (`/api/chat`) with the same JSON Schema as `format` and temperature 0. Text never leaves the machine.
3. **Switching layer:** `FallbackAiProvider` (application layer) implements the same `AiProvider` port over an ordered list of providers. It moves to the next provider only when one is `unavailable` or times out, never on an invalid request. It adds an uncertainty note naming the providers that failed, and the answering provider is recorded in the result's provenance.
4. **Extraction logic is provider-neutral:** `ModelClinicalExtractor` (application layer) builds the instructions and schema, parses the JSON, and keeps only items whose `evidence_quote` is found in the source text. It reports no model confidence, because self-reported confidence is not calibrated. If every provider fails, the API returns the contract's `503 extraction_unavailable`.
5. **Configuration by environment, no secrets:** `AI_EXTRACTION_MODE` (`model` by default, or `fixture` for the deterministic demo mock), `AI_PROVIDERS` (order, default `claude,ollama`), `CLAUDE_MODEL`, `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `AI_PROVIDER_TIMEOUT_SECONDS`. See `services/ai/.env.example`.

## Alternatives considered

- **Anthropic API SDK (`anthropic`) with an API key:** the natural choice for a single structured-output call, and better suited to server deployment. Not chosen now because no key is available to the team, and keys add secret handling. It is the expected replacement for the Agent SDK adapter before any hosted deployment.
- **Ollama only:** keeps all text local, but extraction quality from a small local model is lower and slower on contributor laptops.
- **Claude only:** best quality, but the demo would fail whenever the CLI login or network is unavailable.
- **A generic multi-provider library (for example LiteLLM):** adds a large dependency to solve a two-provider problem that a small adapter pair and the existing port already solve.

## Consequences

### Positive

- Real extraction works on a contributor machine with no secret in the repository.
- The demo keeps working offline or without a Claude login, using the local model.
- Providers can be reordered or removed by configuration, and new ones added behind the same port.
- Provenance shows which provider produced each draft.

### Negative

- **The Agent SDK depends on the Claude Code CLI and an interactive login.** That suits development and demos, not a hosted service. A server deployment needs a different Claude adapter (API key or workload identity) and its own decision.
- **With Claude, fictional source text is sent to Anthropic.** This is acceptable for fictional data only. Real clinical text must not be sent until the data-boundary question is decided.
- The Agent SDK is a full agent harness used for a single call. It is heavier than a plain API client, and each call starts a CLI process.
- The fallback model must be downloaded (several GB) and the Ollama server must be running.
- Model output is non-deterministic. Tests use test doubles; live behaviour is checked by opt-in live tests.

## Follow-up

- Replace the Agent SDK adapter with an API-client adapter before any hosted deployment.
- Decide whether clinical text may leave the hospital boundary; if not, make Ollama (or another local model) the primary provider for real data.
- Measure extraction quality with an evaluation set before any claim beyond D3 demo use.
