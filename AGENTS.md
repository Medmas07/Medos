# Agent Instructions

## Scope

These instructions apply to the entire repository. Keep changes appropriate for a two-day hackathon and within the issue being handled.

## Sources of truth

Use, in order: validated functional requirements, accepted ADRs, `docs/architecture.md`, repository documentation, and the current issue. Surface contradictions instead of guessing.

## Architecture invariants

- Respect Clean Architecture / Hexagonal Architecture for every business backend or service.
- Keep the Domain independent of frameworks, databases, ORMs, brokers, external APIs, Docker, cloud providers, and infrastructure libraries.
- Make dependencies point inward.
- Route external interactions through ports and adapters.
- Keep primary business logic out of controllers, routes, and repositories.
- Do not import infrastructure directly into the Domain.
- Prefer simple boundaries suitable for a two-day hackathon.

## Dependency rules

Allowed dependency direction: `infrastructure/framework -> adapters -> application -> domain`. Application may depend on Domain; adapters may depend on Application and Domain; infrastructure may depend on inner layers. The reverse is forbidden. Do not bypass a port for speed without explicitly documenting the debt.

## Repository structure

Place applications in `apps/`, justified specialized services in `services/`, reusable units in `packages/`, technical deployment assets in `infrastructure/`, cross-system tests in `tests/`, and durable knowledge in `docs/`. Do not scaffold internal application layers until the relevant stack and requirements are known.

## Development rules

- Work only from validated requirements or an explicit issue.
- Do not invent abstractions without a real need.
- Do not create a microservice without justification and an ADR.
- Do not create a layer only to resemble a diagram.
- Introduce an abstraction only when it protects the core from an external detail or clearly improves testability.
- Avoid speculative CQRS, event sourcing, generic repositories, factories, and artificial domain events.

## Issue workflow

Move work through `Backlog -> Ready -> In Progress -> In Review -> Testing -> Done`; use `Blocked` when progress depends on unresolved input. Self-assign a Ready issue before implementation and keep its status current.

## Git rules

Branch from the agreed base using the conventions in `CONTRIBUTING.md`. Keep commits focused and use `type(scope): concise description`. Do not rewrite shared history or include unrelated changes.

## Pull Request rules

Link the issue, explain scope and architecture impact, provide verification evidence, disclose debt and open questions, and keep the PR reviewable. Do not merge without the required review and validation.

## Testing rules

Prioritize Domain tests, then Application/use-case tests, integration tests, and E2E tests. Domain and use cases must be testable without Docker, a real database, network access, or a running web server. Use fakes or test doubles at ports. Add no speculative business tests before requirements exist.

## Documentation rules

Update documentation with behavior or architecture changes. Record consequential choices as ADRs. Mark unknowns explicitly; never present an unvalidated technology choice as final. Keep Markdown links relative and valid.

## Security and secrets

Never commit credentials, tokens, patient data, personal data, production data, or populated environment files. Use `.env.example` with non-sensitive placeholders. Treat healthcare data as sensitive and document security/privacy assumptions once requirements are known.

## Dependency management

Add dependencies only for an implemented requirement. Prefer maintained, minimal packages; pin or lock versions using the chosen ecosystem; review licenses and security implications. Do not install a framework merely to prepare the repository.

## Definition of Done

The issue acceptance criteria are met; boundaries are preserved; relevant tests and checks pass; documentation and ADRs are current; no secrets or sensitive data are present; the PR includes verification evidence; and known limitations are explicit.

## Out-of-scope discoveries

Record unrelated discoveries in a new proposed issue or in the PR notes. Do not expand the current change without agreement.

## Forbidden actions

Do not invent product requirements, adopt an undecided stack, bypass architecture boundaries silently, put business logic in delivery or persistence code, add unjustified services or abstractions, commit secrets or health data, or modify remote GitHub resources without explicit authorization.
