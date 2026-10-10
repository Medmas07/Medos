# Project

## What this repository is

This repository currently contains the documented boundaries and delivery plan for a federated healthcare data and intelligence ecosystem. It is a structure-first hackathon repository, not an implemented healthcare product.

Before coding, follow the [agent startup checklist](docs/AGENT_STARTUP_CHECKLIST.md).

## Product vision

The CONFIRMED vision connects autonomous Hospital Nodes, an independent Governance / Ethics Authority, patient and clinician mobile products, company-managed web portals, and governed research through Federation and Compute-to-Data. Hospital clinical source data remains locally controlled. Read the [canonical product vision](docs/product/FEDERATED_HEALTHCARE_ECOSYSTEM.md).

## Architecture principles

- Clean / Hexagonal Architecture with inward dependencies.
- Explicit, versionable cross-component contracts.
- No central clinical database or direct cross-component SQL access.
- Hospital-local DMI Adapters.
- Governance-owned authorization and optional immutable audit integration.
- External SciAgents Integration rather than reimplementation.
- Advisory AI with accountable human validation.

See the [technical architecture](docs/architecture.md).

## Repository map

- `apps/`: Hospital, Governance, and Research web portals; Patient and Clinician mobile products.
- `instances/`: Hospital Node and Governance Node deployable boundaries.
- `services/`: AI, Federation, Notification, and Research capabilities.
- `integrations/`: SciAgents and future company/platform integrations.
- `contracts/`: API, event, federation, and technology-neutral message definitions.
- `infrastructure/`, `production/`, `iot/`: environment-specific or optional technical assets.
- `docs/`: product truth, architecture, status, planning, ADRs, and guidance.
- `tests/`: future cross-system integration and E2E validation.

## Source of truth

The [documentation index](docs/README.md) defines the complete precedence order. Product vision comes first, followed by technical architecture, agent instructions, contribution workflow, plans, ADRs, and local component documentation.

## Current status

The repository structure, governance templates, placeholder workflows, planning documents, and documentation are IMPLEMENTED. Product applications, runtimes, integrations, persistence, real AI, and distributed execution are not implemented. See [current status](docs/CURRENT_STATUS.md); never infer feature implementation from a README or plan.

## Development workflow

Work proceeds from a Ready issue through implementation, tests, review, validation, and Done. Technology selection requires the applicable ADR before framework initialization. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation map

- [Documentation index and status vocabulary](docs/README.md)
- [Canonical product vision](docs/product/FEDERATED_HEALTHCARE_ECOSYSTEM.md)
- [Technical architecture](docs/architecture.md)
- [Current implementation status](docs/CURRENT_STATUS.md)
- [Open questions](docs/OPEN_QUESTIONS.md)
- [Planning backlog](docs/planning/backlog.md)
- [Glossary](docs/GLOSSARY.md)
- [Architecture decisions](docs/decisions/README.md)

## Contributing

Read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before changing the repository. Do not commit, push, deploy, or modify remote resources without authorization.
