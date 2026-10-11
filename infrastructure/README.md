# Infrastructure

Status: OPEN. Place deployment, environment, and platform assets here only after they are justified and documented by the applicable ADR.

## Docker

[ADR-0016](../docs/decisions/ADR-0016-hospital-node-container-image.md) adopts OCI container images, built and run with Docker, for the **Hospital Node only** (HC-220, IMPLEMENTED at D3). Each runtime's image recipe lives with its code ([`instances/hospital-node/Dockerfile`](../instances/hospital-node/Dockerfile)). This directory holds environment assets:

- [`docker/hospital-node/`](docker/hospital-node/): the demo composition of Hospital A, Hospital B, and the private practice, plus their container configurations. Each container mounts only its own configuration and fictional records, read-only, and is published on loopback only. Usage is in the [Hospital Node README](../instances/hospital-node/README.md#container-hc-220).

Other runtimes are not containerized. Image registry, orchestration, hosting, and deployment topology remain OPEN.
