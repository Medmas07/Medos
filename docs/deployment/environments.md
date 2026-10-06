# Runtime environments

## Development

Used for daily implementation. It may enable hot reload, debugging, verbose logs, and local dependencies. Development-only behavior and credentials must not leak into preview or production.

## Preview

Used to validate final artifacts before publication. It runs locally or in a temporary environment and should use production builds, production-like variable handling, optimized components, real service boundaries, and Docker when applicable. It must not use production secrets.

## Production

The real environment accessible to users or the jury. Public frontend, backend, APIs, optional AI services, and optional IoT endpoints exist only when their corresponding components and deployment decisions are confirmed.

## Validation flow

```text
Development
     |
     v
Lint / Tests
     |
     v
Build
     |
     v
Local Production Preview
     |
     v
Integration / E2E Validation
     |
     v
Deployment
```

Concrete commands will be documented after the stack is selected. Preview and production are separate environments, and a passing build alone does not validate a deployment.

## Hosting candidates

- Frontend hosting: TBD. Candidate: Vercel, subject to framework compatibility and an ADR.
- Backend hosting: TBD. Candidates include a controlled machine with an explicitly authorized Cloudflare Tunnel, Render or an equivalent PaaS, and another suitable provider.
- AI service hosting: TBD if an independent Python service is justified.
- IoT exposure: TBD if IoT is adopted; prefer communication through a backend or gateway.

Candidate availability, pricing, limits, and security properties must be verified when the decision is made. No candidate is currently configured or endorsed as final.

## Health checks

Exposed services should eventually provide a minimal health check such as `GET /health` or an equivalent mechanism. It must not disclose credentials, database URLs, environment variables, stack traces, or private network details. No endpoint is created until a backend exists.
