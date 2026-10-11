"""Build a hospital's Hospital Node installation package (HC-221).

The platform operator runs this once a hospital is approved. The package carries what
the hospital needs to run its own Node from the HC-220 image (ADR-0016): a deployment
manifest, the Node's configuration, a compose file, the image itself, checksums, and
an installation helper. It never carries clinical records: the hospital points the
helper at its own data, which never leaves its host.

A package is built only for an approval the Governance Node confirms, through its
hospital approval API (`getHospitalApproval`, hospital-approval.v1.yaml). The builder
does not decide approval and has no offline override.

    python build_package.py --node-config ../../docker/hospital-node/hospital-a.json \\
        --approval-decision dec-hospital-a --image-archive hospital-node.tar

Standard library only, so it runs wherever the platform operator has Python 3.12.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

PACKAGE_FORMAT = "hospital-node-package/1"
TEMPLATE_DIR = Path(__file__).resolve().parent / "template"
DEFAULT_GOVERNANCE_URL = "http://127.0.0.1:8200"
DEFAULT_IMAGE_REF = "hackcure/hospital-node:dev"
# A bearer session for a Governance Node that requires authentication (HC-211).
TOKEN_ENV = "GOVERNANCE_SESSION_TOKEN"
OPAQUE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

# Where the image (HC-220) reads its configuration and data; compose.yaml mounts there.
CONTAINER_LAYOUT = {
    "storage_dir": "/var/lib/hospital-node",
    "mock_clinical_records": "data/clinical-records.json",
    "mock_access_grants": "data/access.json",
    "mock_governance_decisions": "data/governance.json",
    "mock_medication_rules": "data/medication-rules.json",
}
DATA_FILES = [
    Path(path).name for key, path in CONTAINER_LAYOUT.items() if key != "storage_dir"
]
PUBLIC_KEY_FILE = "governance-public-key.pem"
IMAGE_ARCHIVE = "images/hospital-node.tar"
SCRIPTS = ("install.sh", "check-runtime.sh")

NOT_INCLUDED = [
    {
        "item": "clinical_records",
        "reason": "The hospital's data stays on its own host. install.sh --data-dir points "
        "the Node to it; the platform never ships or holds records.",
    },
    {
        "item": "node_secrets",
        "reason": "The Node has no secret of its own yet: its callers are not authenticated. "
        "Nothing is generated, and the platform never sends a secret.",
    },
    {
        "item": "dmi_adapter_configuration",
        "reason": "The Node does not load a DMI adapter at runtime yet (HC-120 to HC-123 are "
        "tested, not wired). DMI configuration stays hospital-local.",
    },
    {
        "item": "container_runtime",
        "reason": "Never installed by the helper. check-runtime.sh (HC-222) reports what is "
        "missing or incompatible, with instructions for the host's administrator.",
    },
    {
        "item": "health_checks",
        "reason": "Deployment health checks are HC-223. /health is checked by hand.",
    },
    {
        "item": "registration",
        "reason": "The helper does not register the Node with the Federation registry; the "
        "platform operator does, through the registry API.",
    },
    {
        "item": "signature",
        "reason": "Neither the package nor the image is signed. SHA-256 checksums detect a "
        "corrupted file, not a forged package.",
    },
]


class PackageError(RuntimeError):
    pass


@dataclass(frozen=True)
class Image:
    reference: str
    # Docker reports the OCI index digest (containerd image store) or the config
    # digest (classic store) as the image ID; the helper accepts either.
    accepted_ids: tuple[str, ...]
    archive: Path
    # The platform the image runs on, from its configuration, e.g. linux and amd64.
    os: str
    architecture: str


Fetch = Callable[[str, dict[str, str]], tuple[int, bytes]]


def http_get(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise PackageError(
            f"Cannot reach the Governance Node at {url}: {error}"
        ) from error


def load_node_config(path: Path) -> dict:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise PackageError(
            f"Cannot read the Node configuration {path}: {error}"
        ) from error
    if not isinstance(config, dict):
        raise PackageError(f"{path} is not a JSON object.")
    for key in ("node_ref", "organization_ref"):
        if not isinstance(config.get(key), str) or not OPAQUE_REF.match(config[key]):
            raise PackageError(f"{path}: {key} must be an opaque reference.")
    port = config.get("port")
    if not isinstance(port, int) or isinstance(port, bool) or not 1024 <= port <= 65535:
        raise PackageError(f"{path}: port must be an integer from 1024 to 65535.")
    # The package's compose.yaml mounts the data at fixed places; a configuration that
    # names others would start a Node that cannot find its files.
    for key, expected in CONTAINER_LAYOUT.items():
        if config.get(key) != expected:
            raise PackageError(
                f"{path}: {key} must be {expected!r}, the container layout (HC-220)."
            )
    if "governance_public_key" in config:
        raise PackageError(
            f"{path}: governance_public_key is set by --governance-public-key, not in the file."
        )
    return config


def verify_approval(
    governance_url: str,
    decision_ref: str,
    organization_ref: str,
    fetch: Fetch = http_get,
    token: str | None = None,
) -> dict:
    if not OPAQUE_REF.match(decision_ref):
        raise PackageError(f"{decision_ref!r} is not a decision reference.")
    url = (
        f"{governance_url.rstrip('/')}/v1/hospital-approvals/"
        f"{urllib.parse.quote(decision_ref, safe='')}"
    )
    headers = {"accept": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    status, body = fetch(url, headers)
    if status == 404:
        raise PackageError(
            f"The Governance Node has no hospital approval {decision_ref}."
        )
    if status in (401, 403):
        raise PackageError(
            f"The Governance Node refused to show {decision_ref} ({status}). "
            f"Set {TOKEN_ENV} to a reviewer's session when it requires authentication."
        )
    if status != 200:
        raise PackageError(f"The Governance Node answered {status} for {decision_ref}.")
    try:
        decision = json.loads(body)
    except ValueError as error:
        raise PackageError("The Governance Node's answer is not JSON.") from error
    # The contract asks a consumer checking an approval to check both fields.
    if decision.get("decision_ref") != decision_ref:
        raise PackageError(
            f"The Governance Node answered for another decision than {decision_ref}."
        )
    if decision.get("organization_ref") != organization_ref:
        raise PackageError(
            f"{decision_ref} is for {decision.get('organization_ref')!r}, "
            f"not {organization_ref!r}."
        )
    if decision.get("outcome") != "approved":
        raise PackageError(
            f"{decision_ref} is {decision.get('outcome')!r}, not an approval."
        )
    return decision


def read_image_archive(path: Path, reference: str) -> Image:
    """Reads the image IDs from a `docker save` archive, without Docker."""
    try:
        with tarfile.open(path) as archive:
            manifest = json.load(archive.extractfile("manifest.json"))
            try:
                index = json.load(archive.extractfile("index.json"))
            except KeyError:
                index = None  # docker save before Docker 25 writes no OCI index
    except (OSError, KeyError, ValueError, tarfile.TarError, TypeError) as error:
        raise PackageError(f"{path} is not a docker save archive: {error}") from error

    entry = next((e for e in manifest if reference in (e.get("RepoTags") or [])), None)
    if entry is None:
        raise PackageError(f"{path} does not contain {reference}.")
    platform = _image_platform(path, entry["Config"])
    config = Path(entry["Config"]).name.removesuffix(".json")
    accepted = [f"sha256:{config}"]
    for item in (index or {}).get("manifests", []):
        name = (item.get("annotations") or {}).get("io.containerd.image.name", "")
        if name == reference or name.endswith(f"/{reference}"):
            accepted.append(item["digest"])
    for image_id in accepted:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise PackageError(f"{path}: {image_id!r} is not an image digest.")
    return Image(reference, tuple(dict.fromkeys(accepted)), path, *platform)


def _image_platform(path: Path, config_name: str) -> tuple[str, str]:
    # check-runtime.sh compares it with the daemon's platform (HC-222).
    try:
        with tarfile.open(path) as archive:
            config = json.load(archive.extractfile(config_name))
    except (OSError, KeyError, ValueError, tarfile.TarError, TypeError) as error:
        raise PackageError(
            f"{path}: cannot read the image configuration: {error}"
        ) from error
    platform = (config.get("os"), config.get("architecture"))
    if not all(isinstance(v, str) and re.fullmatch(r"[a-z0-9]+", v) for v in platform):
        raise PackageError(f"{path}: the image configuration names no platform.")
    return platform


def render(name: str, values: dict[str, str]) -> bytes:
    # A Windows checkout may hold CRLF; install.sh must run on Linux hosts.
    text = (TEMPLATE_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n")
    for key, value in values.items():
        text = text.replace(f"@{key}@", value)
    if leftover := re.search(r"@[A-Z_]+@", text):
        raise PackageError(f"Template {name} has an unfilled {leftover.group()}.")
    return text.encode("utf-8")


def build_files(
    config: dict,
    decision: dict,
    image: Image,
    governance_url: str,
    generated_at: str,
    public_key: bytes | None,
) -> dict[str, bytes]:
    node_ref = config["node_ref"]
    node_config = {
        "notice": (
            f"Hospital Node configuration of {node_ref}, from its installation package "
            "(HC-221). Paths are inside the container; compose.yaml mounts the files there."
        ),
        **{key: value for key, value in config.items() if key != "notice"},
    }
    key_volume = ""
    if public_key is not None:
        node_config["governance_public_key"] = PUBLIC_KEY_FILE
        key_volume = f"\n      - ./config/{PUBLIC_KEY_FILE}:/etc/hospital-node/{PUBLIC_KEY_FILE}:ro"

    values = {
        "NODE_REF": node_ref,
        "ORGANIZATION_REF": config["organization_ref"],
        "PORT": str(config["port"]),
        "IMAGE_REF": image.reference,
        "IMAGE_IDS": " ".join(image.accepted_ids),
        "IMAGE_ARCHIVE": IMAGE_ARCHIVE,
        "IMAGE_OS": image.os,
        "IMAGE_ARCH": image.architecture,
        "DATA_FILES": " ".join(DATA_FILES),
        "KEY_VOLUME": key_volume,
    }
    files = {
        "config/node.json": _json(node_config),
        "compose.yaml": render("compose.yaml", values),
        "install.sh": render("install.sh", values),
        "check-runtime.sh": render("check-runtime.sh", values),
        "README.md": render("README.md", values),
        IMAGE_ARCHIVE: image.archive.read_bytes(),
    }
    if public_key is not None:
        files[f"config/{PUBLIC_KEY_FILE}"] = public_key

    manifest = {
        "package_format": PACKAGE_FORMAT,
        "notice": (
            "Hospital Node installation package (HC-221, D3). It contains no clinical "
            "record and no secret. Not signed and not a production release."
        ),
        "generated_at": generated_at,
        "node": {
            "node_ref": node_ref,
            "organization_ref": config["organization_ref"],
            "port": config["port"],
            "published_on": f"127.0.0.1:{config['port']}",
        },
        "approval": {
            "decision_ref": decision["decision_ref"],
            "application_ref": decision.get("application_ref"),
            "organization_ref": decision["organization_ref"],
            "outcome": decision["outcome"],
            "decided_at": decision.get("decided_at"),
            "policy_ref": decision.get("policy_ref"),
            "conditions": decision.get("conditions", []),
            "verified_with": f"{governance_url.rstrip('/')}/v1/hospital-approvals/",
            "verified_at": generated_at,
        },
        "image": {
            "reference": image.reference,
            "accepted_ids": list(image.accepted_ids),
            "platform": f"{image.os}/{image.architecture}",
            "archive": IMAGE_ARCHIVE,
            "registry": None,
        },
        "governance_trust": {
            "public_key": f"config/{PUBLIC_KEY_FILE}"
            if public_key is not None
            else None,
            "note": "Verifies Governance-signed synchronization authorizations (HC-214)."
            if public_key is not None
            else "Not included: the Node checks synchronization decisions against its "
            "MOCKED fictional decisions.",
        },
        "data": {
            "required_files": DATA_FILES,
            "provided_by": "the hospital, at installation (install.sh --data-dir)",
        },
        "not_included": NOT_INCLUDED,
    }
    files["manifest.json"] = _json(manifest)
    files["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(content).hexdigest()}  {name}\n"
        for name, content in sorted(files.items())
    ).encode("utf-8")
    return files


def write_package(
    files: dict[str, bytes], root: str, out_dir: Path, mtime: int
) -> Path:
    """Writes a reproducible .tar.gz: sorted entries, fixed owner and times."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{root}-package.tar.gz"
    with open(target, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=mtime) as zipped:
            with tarfile.open(
                fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT
            ) as tar:
                directories = {f"{root}/{d}" for n in files for d in _parents(n)}
                for name in sorted(directories | {root}):
                    tar.addfile(_info(name, 0, 0o755, mtime, tarfile.DIRTYPE))
                for name, content in sorted(files.items()):
                    mode = 0o755 if name in SCRIPTS else 0o644
                    info = _info(
                        f"{root}/{name}", len(content), mode, mtime, tarfile.REGTYPE
                    )
                    tar.addfile(info, io.BytesIO(content))
    return target


def build(
    node_config_path: Path,
    decision_ref: str,
    image_archive: Path,
    out_dir: Path,
    *,
    image_ref: str = DEFAULT_IMAGE_REF,
    governance_url: str = DEFAULT_GOVERNANCE_URL,
    public_key_path: Path | None = None,
    fetch: Fetch = http_get,
    token: str | None = None,
    now: datetime | None = None,
) -> Path:
    config = load_node_config(node_config_path)
    decision = verify_approval(
        governance_url, decision_ref, config["organization_ref"], fetch, token
    )
    image = read_image_archive(image_archive, image_ref)
    public_key = None
    if public_key_path is not None:
        try:
            public_key = public_key_path.read_bytes()
        except OSError as error:
            raise PackageError(f"Cannot read {public_key_path}: {error}") from error
        if b"-----BEGIN PUBLIC KEY-----" not in public_key or b"PRIVATE" in public_key:
            raise PackageError(f"{public_key_path} is not a PEM public key.")
    moment = (now or datetime.now(UTC)).replace(microsecond=0)
    files = build_files(
        config, decision, image, governance_url, moment.isoformat(), public_key
    )
    return write_package(files, config["node_ref"], out_dir, int(moment.timestamp()))


def _json(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _parents(name: str) -> list[str]:
    parts = name.split("/")[:-1]
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def _info(name: str, size: int, mode: int, mtime: int, kind: bytes) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size, info.mode, info.mtime, info.type = size, mode, mtime, kind
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--node-config",
        type=Path,
        required=True,
        help="the hospital's container configuration (HC-220 layout)",
    )
    parser.add_argument(
        "--approval-decision",
        required=True,
        help="the Governance Node's approval decision, e.g. dec-hospital-a",
    )
    parser.add_argument(
        "--image-archive",
        type=Path,
        required=True,
        help="output of: docker save -o hospital-node.tar IMAGE",
    )
    parser.add_argument("--image-ref", default=DEFAULT_IMAGE_REF)
    parser.add_argument("--governance-url", default=DEFAULT_GOVERNANCE_URL)
    parser.add_argument(
        "--governance-public-key",
        type=Path,
        help="the Governance Node's signing public key (HC-214), optional",
    )
    parser.add_argument("--out", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    try:
        package = build(
            args.node_config,
            args.approval_decision,
            args.image_archive,
            args.out,
            image_ref=args.image_ref,
            governance_url=args.governance_url,
            public_key_path=args.governance_public_key,
            token=os.environ.get(TOKEN_ENV) or None,
        )
    except PackageError as error:
        print(f"Package not built: {error}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    print(f"{package}\nsha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
