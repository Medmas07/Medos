# ADR-0008: The Hospital Node serves the medication safety check

## Status

Accepted — 2026-10-11, chosen by the HC-162 assignee during HC-162 ([#135](https://github.com/Medmas07/Hackcure_hackathon/issues/135)); subject to pull-request review.

## Context

The [medication safety check contract](../../contracts/api/medication-safety/medication-safety-check.v1.yaml) (HC-160) left its provider OPEN: "the Hospital Node serving the clinician or a dedicated service; a dedicated service needs an ADR" ([OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md)). HC-162 implements the deterministic engine and must put it somewhere.

Forces:

- **Safety source:** warnings must come from deterministic rules or a validated source, never an LLM (AGENTS.md, product vision section 18). The engine must not live where a model could be mistaken for it.
- **Data boundary:** the contract is stateless. The caller sends the authorized medication history it already holds, possibly from several organizations, and the provider never fetches hospital data itself. No central service may connect to hospital DMIs.
- **Repository boundaries:** `services/` holds justified AI, Federation, Notification, and Research capabilities only, and speculative services are forbidden.
- **Demo:** the clinician's workflow is served by a Hospital Node; one fewer process to run is simpler for a two-day hackathon.

## Decision

1. **Each Hospital Node serves `POST /v1/medication-safety-checks`** per the contract, as the node serving the clinician. The engine runs inside that hospital's boundary.
2. **The engine is Hospital Node domain code** (`domain/medication_safety.py`): standard library only, deterministic, with no model and no provider SDK.
3. **Rules come through an application-owned port**, `InteractionRuleSource`. Its only adapter today reads the fictional HC-161 rule set (`demo-data/medication-rules.json`) at startup and reports every result as `mocked: true`. A validated source (HC-163) is a new adapter behind the same port.
4. **The check stays stateless:** the node does not read its own clinical repository for it, does not store the request, and does not attach AI explanations (HC-164 does, through AI Services).

## Alternatives considered

- **A dedicated `services/medication-safety/` service:** closer to the vision's "Medication Safety Service" wording, and one deployment for every hospital. Not chosen: it adds a service, a port, and an ADR-level boundary for a stateless function, and AGENTS.md does not list it among justified services. A later ADR can extract the engine, which is self-contained domain code behind a port.
- **AI Services:** rejected. It would put the safety source in the component whose output is advisory, against the rule that an LLM is never the safety source.
- **Engine without an HTTP host:** keeps the question open, but nothing could be demonstrated or consumed.

## Consequences

### Positive

- No new service; the check runs where the clinician's request is served, inside a hospital boundary.
- The engine is testable without a web server, and the rule source is replaceable.
- The medication history a caller assembles is processed by the hospital serving the clinician, not sent to a company service.

### Negative

- Every Hospital Node carries the same rule set; versions could drift between nodes once real sources exist. Rule distribution is OPEN.
- A non-hospital caller (for example a private practice without a node) has no check unless a node serves it.
- Callers are not authenticated (demo depth), like the node's other APIs.

## Follow-up

- HC-163: a validated interaction source behind `InteractionRuleSource`.
- HC-164: attach AI explanations (AI Services, HC-156) to warnings.
- The medication terminology (for example RxNorm or ATC) remains OPEN; the demo uses a fictional local code system.
