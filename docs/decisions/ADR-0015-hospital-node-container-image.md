# ADR-0015: Hospital Node container image — one OCI image, hospital configuration and data mounted at runtime

## Status

Accepted — 2026-10-11, chosen by the HC-220 assignee during HC-220 ([#169](https://github.com/Medmas07/Hackcure_hackathon/issues/169)); subject to pull-request review.

## Context

Each Hospital Node is an autonomous, separately deployable trust boundary, expected to be containerized ([ADR-0003](ADR-0003-backend-runtime-strategy.md), HC-220). Until now the container runtime and images were OPEN: the root `docker-compose.yml` was an empty placeholder, and `infrastructure/README.md` stated that Docker had not been adopted. HC-220 asks for a containerized Hospital Node at D3. Its follow-ups, the installation package (HC-221), container runtime detection (HC-222), and deployment health checks (HC-223), all depend on an image existing.

Forces:

- **One codebase, one process per hospital** (ADR-0003): the same build must serve every hospital, with separate identity, configuration, and storage.
- **Hospital data stays with its hospital:** an image is a distributable artifact. It must not carry any hospital's records, even fictional ones, or another hospital's configuration.
- **Unauthenticated callers:** the Node's APIs do not authenticate callers yet, so nothing should expose them beyond the host by default.
- **Hospitals choose their own infrastructure:** the format must not tie them to one vendor's runtime.
- **The research sandbox** (HC-186) needs a POSIX environment and a writable temporary directory.

## Decision

1. **Format: an OCI container image**, built from `instances/hospital-node/Dockerfile` with that directory as build context. The recipe lives with the code it packages, like its pinned `requirements.txt`. Docker Engine with Docker Compose is the tool used for local and demo runs. Any OCI-compatible runtime can run the image, but only Docker was tested.
2. **Base image: the official `python:3.12-slim` (Debian bookworm)**, pinned by exact version and digest so a rebuild is reproducible. Dependencies come from the Node's own pinned `requirements.txt`; development dependencies, tests, and demo configurations are not included.
3. **One image for every hospital.** The image holds code only. Each hospital's configuration file is mounted read-only at `/etc/hospital-node/node.json`, the variable `HOSPITAL_NODE_CONFIG` points there, and the files it names are mounted next to it. A node without a configuration refuses to start, as it does outside a container.
4. **Least privilege by default:** the Node runs as an unprivileged user (uid 10001) and cannot write its own code. The demo composition adds a read-only root filesystem with a `tmpfs` at `/tmp`, drops every Linux capability, and sets `no-new-privileges`.
5. **Listening:** inside the container the Node listens on every interface (`HOSPITAL_NODE_HOST=0.0.0.0`) at the port in its configuration. Outside a container the default stays `127.0.0.1`. The demo composition publishes each port on the host's loopback only.
6. **Demo composition** in `infrastructure/docker/hospital-node/compose.yaml`: Hospital A, Hospital B, and the private practice, each with its own container configuration and only its own fictional records, at the ports of the Federation registry seed.

## Alternatives considered

- **Bake the demo data into the image:** a single self-contained image would be easier to demo, but every hospital's image would carry every hospital's records. Rejected.
- **One image per hospital:** it would bake in identity and configuration. That contradicts ADR-0003's single codebase, multiplies builds, and still mixes configuration with code. Rejected.
- **Build from the repository root** with a repository-wide `.dockerignore`: the context would include every app, mobile build output, and other components. Rejected in favor of the Node's own directory.
- **Alpine or distroless base images:** smaller, but Alpine's musl builds of Python wheels are less predictable, and distroless images complicate debugging at hackathon depth. They can be reconsidered for production.
- **No container, an installer script around a virtual environment:** it depends on each hospital's host Python and gives no isolation boundary. Rejected; the product vision expects containerized Nodes.

## Consequences

### Positive

- One reproducible, pinned image runs any hospital's Node. Hospital A, Hospital B, and the private practice run from it side by side, and services on the host reach them exactly as before.
- No hospital's data or configuration is in the image, and each container sees only its own files, read-only.
- On Linux containers the HC-186 research sandbox applies real POSIX resource limits (`posix_rlimit`), instead of the `parent_enforced` fallback on Windows hosts.

### Negative

- The container is a process boundary, not a security certification. Callers are still unauthenticated, persistence is still absent, and nothing here makes the Node production-ready.
- Hospital configuration files and data mounts must be written per hospital. The demo container configurations duplicate the identity and port of the demo configurations; a test keeps them in sync.
- The image is about 290 MB, because `fastapi[standard]` brings development-server dependencies the Node does not need in production.
- No image registry, signing, or software bill of materials yet: the image is built locally.

## Follow-up

- HC-221: package the image with a hospital's configuration for installation.
- HC-222: detect the container runtime on the hospital's host, and never install it silently.
- HC-223: container and deployment health checks; `/health` remains liveness only.
- HC-224: containerize the Governance Node the same way.
- Later and still OPEN: image registry and signing, orchestration, hosting topology, and an image with fewer dependencies for production.
