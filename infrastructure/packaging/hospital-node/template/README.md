# Hospital Node @NODE_REF@ — installation package

This package installs the Hospital Node of `@ORGANIZATION_REF@` on a host the hospital controls. It was built after the Governance / Ethics Authority approved the hospital; `manifest.json` cites that approval.

It contains no clinical record and no secret. The Node reads the hospital's data from a directory on this host, which never leaves it. **Demo depth (D3):** the package is not signed, the Node's callers are not authenticated, and its records are the fictional demo files. It is not a production release.

## Contents

| File | Purpose |
|---|---|
| `manifest.json` | What the package is: node identity, the approval it was built for, the image, and what is not included and why. |
| `compose.yaml` | How the Node runs: read-only, without capabilities, published on `127.0.0.1:@PORT@` only. |
| `config/node.json` | The Node's configuration: its identity, its port, and where it finds its files. |
| `images/hospital-node.tar` | The Hospital Node image `@IMAGE_REF@`. There is no registry. |
| `install.sh` | The installation helper. |
| `check-runtime.sh` | Checks that this host can run the Node, and says what is missing. |
| `SHA256SUMS` | The checksum of every other file. |

## Install

Requirements: Docker Engine with the Compose plugin (version 2 or later), already installed by the host's administrator, running @IMAGE_OS@/@IMAGE_ARCH@ containers. The helpers never install software. On Windows, run them from Git Bash or WSL.

Check the host first; it changes nothing and needs no data:

```sh
./check-runtime.sh   # exit code 0: ready; 3: something is missing, with what to do
```

Put the hospital's data in one directory, with these files: `@DATA_FILES@`. Then:

```sh
./install.sh --data-dir /path/to/data --verify-only   # checks only, no Docker needed
./install.sh --data-dir /path/to/data
curl -s http://127.0.0.1:@PORT@/health
```

The helper checks every file against `SHA256SUMS` and that the data files are there, then runs `check-runtime.sh` (exit code 3 if the host is not ready). It then loads the image and checks that it is the one this package was built with. Finally it writes `.env`, starts the Node, and checks that it stays up for a few seconds. The Node refuses to start on records held by another organization; the helper then shows the log, removes the container, and fails (exit code 4).

Stop the Node with `docker compose down` from this directory.

## Not done by this package

Health checks (HC-223), registration with the Federation registry (done by the platform operator), signatures, and updates. See `not_included` in `manifest.json`.
