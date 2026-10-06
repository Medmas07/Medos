# Architecture

## 1. Context

This repository supports a two-day healthcare hackathon. Functional requirements and the technology stack are not yet known. The sole architectural constraint already accepted is that business backends and services follow Clean Architecture or Hexagonal Architecture principles.

## 2. Architectural principles

### Clean Architecture

Business policy belongs at the center. Frameworks, persistence, delivery mechanisms, third-party SDKs, Docker, and cloud services are replaceable details. Code is organized around clear boundaries without creating layers or abstractions that have no demonstrated need.

### Hexagonal Architecture

The application communicates with external actors through ports. Inbound adapters invoke application use cases; outbound adapters implement ports required by those use cases. Adapters translate between external representations and internal concepts.

### Dependency Rule

Dependencies point inward:

```text
domain
   ↑
application
   ↑
adapters
   ↑
infrastructure / framework
```

- Domain knows no outer layer.
- Application may depend on Domain.
- Adapters may depend on Application and Domain.
- Infrastructure and frameworks may depend on inner layers.
- Reverse dependencies are forbidden.

Forbidden examples include `domain -> Prisma`, `domain -> TypeORM`, `domain -> SQLAlchemy`, `domain -> NestJS`, `domain -> FastAPI`, and `domain -> PostgreSQL`.

An acceptable relationship is an Application-defined `RepositoryPort` implemented by an infrastructure-facing `PrismaRepository` or `SQLAlchemyRepository`. No ORM has been selected by this example.

### Ports and Adapters

External interactions must cross explicit ports when a real use case requires them. Conceptually:

```text
UseCase -> RepositoryPort <- PersistenceAdapter
```

Potential ports include notification, AI service, file storage, authentication, event publishing, or external medical API contracts, but none should be created before validated requirements demonstrate a need.

## 3. Functional requirements

To be defined from the validated product brief. Do not infer a healthcare workflow from the project context alone.

## 4. Non-functional requirements

To be defined.

## 5. Constraints

- Business backends and services must preserve Clean/Hexagonal boundaries independently of the selected framework.
- The Domain must not depend on web frameworks, databases, ORMs, brokers, external APIs, Docker, cloud providers, or infrastructure libraries.
- The design must remain pragmatic for a two-day hackathon.

## 6. System overview

To be defined after product boundaries and runtime components are known.

The future backend may use the following conceptual organization, adapted to the selected language and framework:

```text
src/
├── domain/
│   ├── entities/
│   ├── value-objects/
│   ├── services/
│   ├── events/
│   └── errors/
├── application/
│   ├── use-cases/
│   ├── dto/
│   ├── ports/
│   │   ├── inbound/
│   │   └── outbound/
│   └── services/
├── adapters/
│   ├── inbound/
│   │   ├── http/
│   │   ├── websocket/
│   │   └── cli/
│   └── outbound/
│       ├── persistence/
│       ├── external-api/
│       ├── messaging/
│       └── storage/
├── infrastructure/
│   ├── database/
│   ├── configuration/
│   ├── logging/
│   ├── security/
│   └── observability/
└── main/
```

This is a boundary model, not a mandate to create every directory.

## IoT / Edge components

An IoT component may be added if the challenge requires one; it is not a mandatory part of the current system. Any embedded code will live in `iot/`, where PlatformIO is prepared as the intended development tooling. The target hardware, embedded framework, and device/backend communication protocol remain undetermined.

When it provides real value, firmware should preserve Clean/Hexagonal boundaries between application logic and hardware-specific code. A simple firmware may use a lightweight structure rather than creating speculative layers. Hardware APIs and SDKs should be isolated behind adapters or infrastructure when a small separation keeps application logic testable.

## 7. Domain layer

Domain contains business entities, value objects, domain services, events, errors, and rules only. It contains no HTTP or JSON-specific logic, ORM models, database queries, framework decorators, environment access, Docker logic, or external SDKs.

## 8. Application layer

Application orchestrates use cases and may contain application services, commands, queries, DTOs, and ports. Use cases should be small and named from validated system actions. They must remain testable without real infrastructure.

## 9. Ports

Ports are contracts owned by the inner layers for required inbound or outbound interactions. Introduce a port only when it protects the core from an external detail or clearly improves testability; avoid speculative interfaces and generic repositories.

## 10. Adapters

Adapters translate between the application and the outside world. They contain integration behavior, not core business policy.

### Inbound adapters

Possible inbound adapters include REST, GraphQL, WebSocket, CLI, scheduled jobs, and event consumers. None is selected. Controllers and routes call use cases and must not host primary business logic.

### Outbound adapters

Possible outbound adapters include persistence, filesystem, external API, AI, messaging, notification, and object-storage integrations. None is selected. Repositories implement persistence ports and must not become the home of business logic.

## 11. Infrastructure

Infrastructure contains technical configuration and implementations such as database access, logging, security, and observability. It may depend inward; inner layers must not depend on it.

If NestJS is selected, decorators, modules, controllers, HTTP DTOs, and ORM integration stay in outer layers. If FastAPI is selected for a specialized Python service, FastAPI routes remain inbound delivery adapters. In either case, endpoints delegate to use cases.

If both are justified, the preferred starting model is one primary business backend and a specialized Python service for a demonstrated ML/AI/CV/NLP need, rather than competing business backends. This choice requires an ADR.

## 12. Components

To be defined.

## 13. Data flow

To be defined from use cases. In general, an inbound adapter translates a request, invokes an Application use case, and the use case reaches external systems only through ports implemented by outbound adapters.

## 14. API boundaries

To be defined.

## 15. Data model

To be defined from validated domain concepts.

## 16. Authentication and authorization

To be decided and recorded by ADR when requirements are known.

## 17. External integrations

To be defined. Each integration must sit behind an appropriate port when used by the application core.

## 18. Deployment architecture

To be decided. Docker support is reserved but not adopted.

## 19. Observability

To be defined.

## 20. Security and privacy

To be defined from the data classification, jurisdiction, threat model, and validated healthcare requirements. Never commit secrets, personal data, or patient data.

## 21. Testing strategy

Test priority is:

```text
Domain tests
     |
Application / use-case tests
     |
Integration tests
     |
E2E tests
```

Business rules and use cases must be testable without Docker, a real database, network access, or a running NestJS/FastAPI server. Ports enable fakes and test doubles. Do not write speculative business tests before requirements exist.

## 22. Technical decisions

The backend framework, frontend framework, database, ORM, NestJS, FastAPI, any combined topology, Docker adoption, authentication, REST/GraphQL, WebSocket, deployment, AI integration, and monolith/services boundary remain open and require ADRs when decided. Clean/Hexagonal principles are a starting constraint rather than an open ADR.

## 23. Open questions

- What problem and users are in scope?
- Which functional and non-functional requirements are validated?
- What data classifications, privacy obligations, and security controls apply?
- Which runtime components and technology stack best support the validated scope?
