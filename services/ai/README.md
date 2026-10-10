# AI Services

## Purpose and status

Python is CONFIRMED for potential AI components, and FastAPI is CONFIRMED as its HTTP runtime by [ADR-0003](../../docs/decisions/ADR-0003-backend-runtime-strategy.md); HC-150 creates the runtime. AI libraries, providers, models, hosting, and API contracts are OPEN. All capabilities are PLANNED; no AI implementation exists.

## Responsibilities and owned concepts

Potential extraction, summarization, document review, lab interpretation assistance, priority explanation, medication explanation, and LLM orchestration behind explicit ports.

## Communication boundaries

Provider SDKs stay in outbound adapters and outside Domain. Consumers use versioned request/result contracts with provenance and review state.

## Non-responsibilities

No AI output automatically becomes clinical truth. AI does not autonomously diagnose, prescribe, triage critical cases, approve institutions/research, or serve as the sole medication-safety source.

## Expected contracts

PLANNED provider-neutral extraction, explanation, review, provenance, error, and model-capability contracts.
