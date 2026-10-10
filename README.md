# HackCure Federated Healthcare Platform

This repository reserves the architectural boundaries for a federated healthcare ecosystem spanning autonomous hospital nodes, an independent ethics/governance authority, patient and clinician applications, research capabilities, and company-managed distribution services. It contains no product implementation yet.

Future business applications and services must follow Clean Architecture or Hexagonal Architecture. Cross-component communication must use explicit, versionable contracts rather than shared persistence. See [the architecture guide](docs/architecture.md).

## Repository structure

- `apps/`: web and mobile user-facing products.
- `instances/`: autonomous deployable hospital and governance runtime boundaries.
- `services/`: justified backend capabilities for AI, research, federation, and notifications.
- `integrations/`: adapters for DMI/HIS, SciAgents, and other external systems.
- `contracts/`: canonical API, event, schema, and federation communication definitions.
- `packages/`: narrowly reusable, domain-independent helpers and optional shared types.
- `iot/`: optional embedded or connected-device support.
- `infrastructure/`: technical deployment assets.
- `production/`: production-like validation guidance and reserved configuration.
- `docs/`: architecture, product, research, deployment, API, and decision records.
- `scripts/`: repository automation after a concrete need is established.
- `tests/`: future cross-component integration and end-to-end validation.

## Getting started

Python is confirmed for potential AI/ML components, but no Python library, framework, application framework, persistence technology, or notification provider has been selected. Add setup instructions only with validated requirements and accepted decisions.

Start with the [documentation index](docs/README.md), [architecture guide](docs/architecture.md), [contribution guide](CONTRIBUTING.md), and [agent rules](AGENTS.md).
