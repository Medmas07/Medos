# Documentation

## Source hierarchy

When documents conflict, use this order:

1. [Federated Healthcare Ecosystem](product/FEDERATED_HEALTHCARE_ECOSYSTEM.md) — canonical product vision.
2. [Architecture](architecture.md) — canonical technical architecture and boundaries.
3. [Agent Instructions](../AGENTS.md) — mandatory coding-agent behavior.
4. [Contributing](../CONTRIBUTING.md) — canonical Git/GitHub workflow.
5. [Planning](planning/backlog.md) — implementation sequence and temporary ticket definitions.
6. [Architecture Decision Records](decisions/README.md) — accepted technical decisions.
7. Component READMEs — local ownership and current status only.
8. Production, infrastructure, and IoT documentation — environment-specific guidance.

Documentation describes intent unless the [current status](CURRENT_STATUS.md), actual code, and validation evidence show implementation. Complete the [agent startup checklist](AGENT_STARTUP_CHECKLIST.md) before coding.

## Status vocabulary

Use these labels consistently:

- **CONFIRMED** — an explicitly decided product or architecture constraint.
- **PLANNED** — intended but not implemented.
- **MOCKED** — implemented only with demo behavior or fixture data.
- **IMPLEMENTED** — exists in repository code or artifacts; not necessarily verified.
- **VALIDATED** — implemented and verified by tests or applicable live/runtime validation.
- **OPTIONAL** — may be adopted if a validated need arises.
- **DEPRECATED** — retained temporarily but should no longer be used.
- **OPEN** — unresolved and not safe to assume.

Avoid ambiguous present tense. For example, say “The Patient timeline is PLANNED; verify implementation in code and tickets,” not “The Patient timeline is implemented.”

## Documentation map

- [Product vision](product/FEDERATED_HEALTHCARE_ECOSYSTEM.md): scope, stakeholders, trust, ownership, and product model.
- [Architecture](architecture.md): technical boundaries and current architecture status.
- [Current status](CURRENT_STATUS.md): what is and is not implemented.
- [Open questions](OPEN_QUESTIONS.md): unresolved technology and architecture decisions.
- [Security audit and threat model](security/threat-model.md): trust boundaries, STRIDE threats, and findings (HC-215); not an independent review.
- [Glossary](GLOSSARY.md): repository-specific terminology.
- [Planning](planning/backlog.md): backlog, [milestones](planning/milestones.md), [demo](planning/demo-scenario.md), and [dependencies](planning/dependency-map.md).
- [ADRs](decisions/README.md): consequential accepted decisions and template.
- [Deployment](deployment/README.md): runtime environments and deployment guidance.
- [Research](research/README.md): time-boxed findings and sources.
- [API documentation](api/README.md) and [communication contracts](../contracts/README.md).
- [IoT](../iot/README.md): OPTIONAL embedded boundary and current PlatformIO preparation.
- [Project workflow](project-workflow.md): collaboration and project-board guidance.
- [Diagrams](diagrams/README.md): architecture and flow diagrams.

## Reading paths

- **New human contributor:** product vision → current status → architecture → contributing → relevant ticket/component.
- **Coding agent:** agent startup checklist → AGENTS.md → product vision → architecture → current status → current ticket and code.
- **Architect:** product vision → architecture → open questions → ADRs → contracts.
- **Product contributor:** product vision → current status → planning backlog → canonical demo scenario.
