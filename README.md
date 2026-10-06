# Project Name

## Status

Repository bootstrap for a two-day healthcare hackathon. Functional requirements and the technology stack are not yet defined.

## About

The product scope will be documented after requirements are validated. This repository intentionally contains no speculative product implementation.

## Architecture

Future business applications and services must follow Clean Architecture or Hexagonal Architecture. Business rules remain independent from frameworks and infrastructure. See [the architecture guide](docs/architecture.md).

## Repository structure

- `apps/`: application entry points reserved for web, mobile, and API applications.
- `services/`: optional specialized services, if justified later.
- `iot/`: optional embedded or connected-device component, if the challenge requires one.
- `packages/`: shared code and types, when real reuse exists.
- `infrastructure/`: deployment and infrastructure assets.
- `production/`: local production-like validation guidance and reserved configuration areas.
- `docs/`: product, architecture, API, research, and decision documentation.
- `tests/`: cross-application integration and end-to-end tests.

## Getting started

Python is confirmed for potential AI/ML components, but no Python library or AI framework has been selected. All other setup instructions will be added with the corresponding architecture decisions.

## Documentation

Start with the [documentation index](docs/README.md). Record significant technical choices as [Architecture Decision Records](docs/decisions/README.md).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) before making changes.
