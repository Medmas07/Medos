# Production and Preview

## Purpose

This directory is reserved for tooling and configuration that builds optimized artifacts, runs them locally under production-like conditions, validates environment variables and service communication, and prepares the system for deployment. It contains no production secrets and does not imply that a deployment platform or container strategy has been selected.

## Environments

### Development

Development is for daily work and may use hot reload, debugging, verbose logs, and local dependencies.

### Preview

Preview runs production builds locally or in a temporary environment using production-like configuration, optimized frontend and backend artifacts, real service boundaries, and Docker when applicable. Preview is validation before publication; it is not production.

### Production

Production is the real environment accessible to users or the jury. Public components will be defined only after product and deployment decisions are accepted.

## Build validation

The intended flow is `Development -> Lint / Tests -> Build -> Local Production Preview -> Integration / E2E Validation -> Deployment`. A working development server or successful build is not sufficient deployment evidence.

## Local production preview

Concrete preview commands will be added after frameworks are selected. Preview should run the same optimized artifacts intended for deployment and validate applicable service boundaries and critical paths.

## Environment variables

Environment names such as `.env.preview` and `.env.production` are conceptual. Real values, especially sensitive ones, must remain outside Git. Safe variable names may be documented in the root `.env.example` only after the corresponding service exists.

## Docker

Docker is adopted for the Hospital Node only ([ADR-0016](../docs/decisions/ADR-0016-hospital-node-container-image.md), HC-220): its image and a demo composition of three fictional hospitals exist under [`infrastructure/docker/hospital-node/`](../infrastructure/docker/hospital-node/), and an approved hospital's installation package is built by [`infrastructure/packaging/hospital-node/`](../infrastructure/packaging/hospital-node/README.md) (HC-221). The root `docker-compose.yml` remains a neutral placeholder. A `docker-compose.preview.yml` may be introduced once the other runtimes are containerized.

## Deployment

### Frontend

Frontend hosting: TBD

Candidate: Vercel. Suitability depends on the selected frontend framework and must be recorded in an ADR before configuration or connection.

### Backend

Backend hosting: TBD

Candidates:

- controlled machine plus an explicitly authorized Cloudflare Tunnel;
- Render or an equivalent PaaS;
- another provider suitable for the final stack and hackathon constraints.

Availability, pricing, capacity, and security must be verified at decision time. Cloudflare Tunnel is only a candidate: do not install or activate it, create tunnel configuration, store tunnel tokens, or expose a machine automatically.

### AI services

AI Services run as their own Python + FastAPI service in `services/ai/` ([ADR-0003](../docs/decisions/ADR-0003-backend-runtime-strategy.md)). Preview it with `fastapi run main.py --port 8600` from that directory. AI libraries, providers, and hosting remain OPEN.

### IoT

IoT remains optional. If adopted, a device should normally communicate through a backend or gateway using a protocol chosen from actual constraints. Do not expose an embedded device directly to the Internet without an explicit need and security analysis.

## Security

Do not store secrets, private hostnames, credentials, certificates, production data, or populated environment files here. Future health checks should reveal service availability only—not credentials, database URLs, environment variables, internal stack traces, or private network information.

## Deployment checklist

Apply only the checks relevant to components that exist:

- [ ] lint passes
- [ ] automated tests pass
- [ ] production build succeeds
- [ ] production preview starts successfully
- [ ] frontend can reach backend
- [ ] backend health check succeeds
- [ ] AI service connectivity validated if applicable
- [ ] IoT connectivity validated if applicable
- [ ] required environment variables are defined
- [ ] no development credentials are used
- [ ] no secrets are committed
- [ ] no debug endpoint is unintentionally exposed
- [ ] E2E critical path validated
