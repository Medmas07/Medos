# AI Services

## Purpose and status

Python is CONFIRMED for potential AI components. Specific frameworks, providers, models, hosting, and APIs are OPEN. All capabilities are PLANNED; no AI implementation exists.

## Responsibilities and owned concepts

Potential extraction, summarization, document review, lab interpretation assistance, priority explanation, medication explanation, and LLM orchestration behind explicit ports.

## Communication boundaries

Provider SDKs stay in outbound adapters and outside Domain. Consumers use versioned request/result contracts with provenance and review state.

## Non-responsibilities

No AI output automatically becomes clinical truth. AI does not autonomously diagnose, prescribe, triage critical cases, approve institutions/research, or serve as the sole medication-safety source.

## Expected contracts

PLANNED provider-neutral extraction, explanation, review, provenance, error, and model-capability contracts.
