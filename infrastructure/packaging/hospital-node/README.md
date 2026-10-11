# Hospital Node installation package (HC-221)

IMPLEMENTED at D3 and checked locally with Docker Desktop 29.1 (Linux engine) and a running Governance Node. Not signed, not published, and not a production release.

After the Governance / Ethics Authority approves a hospital, the platform operator builds that hospital's installation package with [`build_package.py`](build_package.py). The hospital runs its Node from the package on a host it controls. The package follows the product vision's §7 ([installation and distribution](../../../docs/product/FEDERATED_HEALTHCARE_ECOSYSTEM.md#7-hospital-node-installation-and-distribution)) and reuses the HC-220 image and container layout ([ADR-0016](../../../docs/decisions/ADR-0016-hospital-node-container-image.md)).

## Building a package

```bash
docker build -t hackcure/hospital-node:dev instances/hospital-node
docker save -o hospital-node.tar hackcure/hospital-node:dev

cd infrastructure/packaging/hospital-node
python build_package.py \
  --node-config ../../docker/hospital-node/hospital-a.json \
  --approval-decision dec-hospital-a \
  --image-archive ../../../hospital-node.tar \
  --out dist
```

The builder writes `dist/node-hospital-a-package.tar.gz` and prints its SHA-256. It uses the Python standard library only.

**Approval first.** The builder asks the Governance Node (`--governance-url`, default `http://127.0.0.1:8200`) for the cited decision through `getHospitalApproval` ([`hospital-approval.v1.yaml`](../../../contracts/api/governance/hospital-approval.v1.yaml)). It builds nothing in these cases:

- the decision is unknown, including a decision that is not a hospital approval;
- the decision is not `approved`;
- it is for another organization than the configuration;
- the Governance Node cannot be reached or answers with an error.

There is no offline override; the builder never decides approval itself. With [authentication required](../../../instances/governance-node/README.md#authentication-hc-211), set `GOVERNANCE_SESSION_TOKEN` to a governance reviewer's bearer session. The approval is checked when the package is built, not again at installation.

**Inputs.**

- `--node-config`: the hospital's configuration in the container layout, such as the [demo container configurations](../../docker/hospital-node/). The builder refuses a configuration whose files are not where the package's `compose.yaml` mounts them.
- `--image-archive`: the output of `docker save`. The builder reads the image IDs from it without Docker.
- `--governance-public-key` (optional): the Governance Node's signing public key ([HC-214](../../../instances/hospital-node/README.md#signed-synchronization-authorizations-hc-214)). It is shipped as bootstrap trust material, and the Node then verifies signed synchronization authorizations. A private key is refused.

**Reproducible.** Entries are sorted, owners and times are fixed, so the same inputs at the same time give the same bytes.

## What the package holds

| File | Purpose |
|---|---|
| `manifest.json` | Deployment manifest: package format `hospital-node-package/1`; the node identity and port; the approval as the Governance Node answered it, with where and when it was checked; the image reference and the IDs it may have; the Governance trust material; the data files the hospital must provide; and `not_included`, each with its reason. |
| `compose.yaml` | The HC-220 hardening: read-only root filesystem, `tmpfs` at `/tmp`, no capabilities, `no-new-privileges`. The port is published on `127.0.0.1` only, and `pull_policy: never`. |
| `config/node.json` | The Node configuration (configuration template filled for this hospital), and optionally `config/governance-public-key.pem`. |
| `images/hospital-node.tar` | The image itself. There is no registry, so the package carries it (about 73 MB). |
| `install.sh` | The installation helper (POSIX `sh`). |
| `README.md` | Instructions for the hospital. |
| `SHA256SUMS` | The checksum of every other file. |

**Never in a package:**

- **Clinical records.** The hospital's data stays on its host, and `install.sh --data-dir` points the Node to it.
- **Secrets.** The Node has none yet, so the helper generates no secret, and the platform never sends one.
- **DMI adapter configuration.** The Node loads no DMI adapter at runtime yet ([DMI port](../../../instances/hospital-node/README.md#dmi-port-hc-120)), so a DMI configuration would be a file nothing reads.

## Installing

On the hospital's host, after extracting the archive: `./install.sh --data-dir DIR`. The helper runs these steps in order, and stops at the first failure:

1. Checks every file against `SHA256SUMS` (exit code `1` if one changed).
2. Checks that the data directory has the four data files (exit code `2`). `--verify-only` stops here and needs no Docker.
3. Checks that Docker Engine with the Compose plugin is installed and its daemon answers. If not, it prints instructions and exits with code `3`. **It never installs software** and never asks for administrator rights.
4. Loads the image from the package and checks that its ID is one the manifest names.
5. Writes `.env` (the data directory, the only local configuration) and runs `docker compose up -d`.
6. Fails with exit code `4` if the Node stops or restarts within 8 seconds, for example on another organization's records. It then shows the Node's log and removes the container. This is a startup check, not a health check (HC-223).

On Windows, the helper runs from Git Bash or WSL; there is no PowerShell helper. With Git Bash, extract the archive from its own directory (`tar -xzf node-hospital-a-package.tar.gz`), because GNU tar reads `C:` as a host name.

## Checked

`pytest` (25 tests, no Docker and no Governance Node needed) checks the following:

- the package contents, and that none of the hospital's records are in it;
- the manifest and the checksums;
- that two builds give the same bytes;
- every approval refusal, and the bearer session;
- configuration and image archive refusals, and the public key;
- the helper's `--verify-only` checks: a changed file and missing data are refused.

The tests that run the helper are skipped where there is no POSIX shell.

By hand, with the Governance Node running (`python main.py`) and Docker Desktop 29.1:

- Hospital C (`dec-hospital-c`, still in review), `dec-hospital-b` cited for Hospital A, and `dec-sync-002` are each refused, and nothing is written.
- Hospital A's package installs on a host where the image had been removed. The image is loaded from the package, its ID matches, and `/health` answers on `127.0.0.1:8101` with Hospital A's record counts. The container is read-only, without capabilities, and runs as `hospital-node`.
- Hospital B's package, built with a Governance public key, reports `"synchronization_decisions": "signed"` in `/health`. Hospital A and Hospital B ran side by side.
- Without Docker on `PATH`, the helper stops with exit code `3` and instructions. With Hospital B's records under Hospital A's package, it stops with exit code `4`, shows the Node's own refusal, and leaves no container.

## Not done at D3

- Signing the package or the image, and an image registry (OPEN).
- Updates and uninstall beyond `docker compose down`.
- Runtime detection beyond "Docker is there" (HC-222).
- Deployment health checks (HC-223).
- Registering the Node with the Federation registry, which stays the platform operator's step through the registry API.
- Building packages from the Hospital Portal. Its download page still assembles the HC-061 demo manifest in the browser and points to this package for the image and the helper.
- Production hosting. The Node's callers are still unauthenticated and its data is MOCKED.
