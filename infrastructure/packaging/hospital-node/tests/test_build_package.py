"""HC-221: the installation package, built without Docker or a Governance Node.

The Governance Node's answer is a test double at the HTTP boundary, and the image
archive is a small file with the layout `docker save` writes. Running the package's
helper against Docker is checked by hand (see the README).
"""

import hashlib
import io
import json
import shutil
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

import build_package as bp

REPO = Path(__file__).resolve().parents[4]
CONTAINER_CONFIGS = REPO / "infrastructure" / "docker" / "hospital-node"
DEMO_DATA = REPO / "demo-data"
NOW = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)
CONFIG_DIGEST = "a" * 64
INDEX_DIGEST = "sha256:" + "b" * 64
APPROVAL_A = {
    "decision_ref": "dec-hospital-a",
    "application_ref": "app-hospital-a",
    "organization_ref": "org-hospital-a",
    "outcome": "approved",
    "decided_by_ref": "usr-olfa",
    "decided_at": "2025-01-28T11:00:00+01:00",
    "policy_ref": "pol-governance-v1",
    "rationale": "Dossier complet et conforme à la charte de gouvernance.",
    "conditions": [],
}


def governance(status=200, body=APPROVAL_A, seen=None):
    def fetch(url, headers):
        if seen is not None:
            seen.append((url, headers))
        return status, json.dumps(body).encode()

    return fetch


def image_archive(tmp_path, tags=(bp.DEFAULT_IMAGE_REF,), with_index=True):
    path = tmp_path / "hospital-node.tar"
    members = {
        "manifest.json": [
            {
                "Config": f"blobs/sha256/{CONFIG_DIGEST}",
                "RepoTags": list(tags),
                "Layers": [],
            }
        ],
    }
    if with_index:
        members["index.json"] = {
            "schemaVersion": 2,
            "manifests": [
                {
                    "digest": INDEX_DIGEST,
                    "annotations": {"io.containerd.image.name": f"docker.io/{tags[0]}"},
                }
            ],
        }
    with tarfile.open(path, "w") as tar:
        for name, value in members.items():
            data = json.dumps(value).encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


def build(tmp_path, hospital="hospital-a", **kwargs):
    kwargs.setdefault("fetch", governance())
    return bp.build(
        CONTAINER_CONFIGS / f"{hospital}.json",
        kwargs.pop("decision_ref", "dec-hospital-a"),
        kwargs.pop("archive", None) or image_archive(tmp_path),
        tmp_path / "dist",
        now=NOW,
        **kwargs,
    )


def unpack(package, tmp_path):
    target = tmp_path / "unpacked"
    with tarfile.open(package) as tar:
        tar.extractall(target, filter="data")
    return target / "node-hospital-a"


def test_a_package_holds_the_node_and_no_clinical_record(tmp_path):
    package = build(tmp_path)

    assert package.name == "node-hospital-a-package.tar.gz"
    with tarfile.open(package) as tar:
        names = sorted(m.name for m in tar.getmembers() if m.isfile())
    assert names == [
        "node-hospital-a/README.md",
        "node-hospital-a/SHA256SUMS",
        "node-hospital-a/compose.yaml",
        "node-hospital-a/config/node.json",
        "node-hospital-a/images/hospital-node.tar",
        "node-hospital-a/install.sh",
        "node-hospital-a/manifest.json",
    ]
    root = unpack(package, tmp_path)
    content = b"".join(p.read_bytes() for p in root.rglob("*") if p.is_file())
    records = json.loads((DEMO_DATA / "records" / "hospital-a.json").read_text("utf-8"))
    for kind in ("encounters", "medications", "labReports"):
        for record in records[kind]:
            assert record["id"].encode() not in content


def test_the_manifest_cites_the_verified_approval_and_the_image(tmp_path):
    seen = []
    root = unpack(build(tmp_path, fetch=governance(seen=seen)), tmp_path)
    manifest = json.loads((root / "manifest.json").read_text("utf-8"))

    assert seen[0][0] == "http://127.0.0.1:8200/v1/hospital-approvals/dec-hospital-a"
    assert "authorization" not in seen[0][1]
    assert manifest["package_format"] == "hospital-node-package/1"
    assert manifest["node"] == {
        "node_ref": "node-hospital-a",
        "organization_ref": "org-hospital-a",
        "port": 8101,
        "published_on": "127.0.0.1:8101",
    }
    assert manifest["approval"]["decision_ref"] == "dec-hospital-a"
    assert manifest["approval"]["verified_at"] == "2026-10-11T09:00:00+00:00"
    assert manifest["image"]["accepted_ids"] == [
        f"sha256:{CONFIG_DIGEST}",
        INDEX_DIGEST,
    ]
    assert manifest["image"]["registry"] is None
    assert {i["item"] for i in manifest["not_included"]} >= {
        "clinical_records",
        "node_secrets",
        "dmi_adapter_configuration",
        "signature",
    }


def test_the_node_configuration_and_compose_file_match_the_container_layout(tmp_path):
    root = unpack(build(tmp_path), tmp_path)
    config = json.loads((root / "config" / "node.json").read_text("utf-8"))
    compose = (root / "compose.yaml").read_text("utf-8")

    source = json.loads((CONTAINER_CONFIGS / "hospital-a.json").read_text("utf-8"))
    assert {k: v for k, v in config.items() if k != "notice"} == {
        k: v for k, v in source.items() if k != "notice"
    }
    assert '"127.0.0.1:8101:8101"' in compose
    assert "pull_policy: never" in compose
    assert compose.count(":ro") == 5
    assert "@" not in compose.replace("@sha256", "")


def test_every_file_is_listed_in_the_checksums(tmp_path):
    root = unpack(build(tmp_path), tmp_path)
    sums = dict(
        reversed(line.split("  ", 1))
        for line in (root / "SHA256SUMS").read_text("utf-8").splitlines()
    )

    files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    assert set(sums) == files - {"SHA256SUMS"}
    for name, digest in sums.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest


def test_a_package_is_reproducible(tmp_path):
    first = build(tmp_path).read_bytes()
    second = build(tmp_path).read_bytes()

    assert first == second


def test_install_sh_has_unix_line_endings_and_is_executable(tmp_path):
    with tarfile.open(build(tmp_path)) as tar:
        member = tar.getmember("node-hospital-a/install.sh")
        script = tar.extractfile(member).read()

    assert member.mode == 0o755
    assert b"\r\n" not in script
    assert script.startswith(b"#!/bin/sh\n")


@pytest.mark.parametrize(
    ("status", "body", "message"),
    [
        (404, {"code": "decision_not_found"}, "no hospital approval"),
        (200, {**APPROVAL_A, "outcome": "rejected"}, "not an approval"),
        (200, {**APPROVAL_A, "organization_ref": "org-hospital-b"}, "org-hospital-b"),
        (200, {**APPROVAL_A, "decision_ref": "dec-hospital-b"}, "another decision"),
        (401, {"code": "authentication_required"}, "GOVERNANCE_SESSION_TOKEN"),
        (500, {}, "answered 500"),
    ],
    ids=[
        "unknown",
        "rejected",
        "other-organization",
        "other-decision",
        "auth",
        "error",
    ],
)
def test_no_package_without_a_confirmed_approval(tmp_path, status, body, message):
    with pytest.raises(bp.PackageError, match=message):
        build(tmp_path, fetch=governance(status, body))
    assert not (tmp_path / "dist").exists()


def test_an_unreachable_governance_node_stops_the_build(tmp_path):
    with pytest.raises(bp.PackageError, match="Cannot reach"):
        build(tmp_path, fetch=bp.http_get, governance_url="http://127.0.0.1:9")


def test_a_session_token_is_sent_as_a_bearer(tmp_path):
    seen = []
    build(tmp_path, fetch=governance(seen=seen), token="session-123")

    assert seen[0][1]["authorization"] == "Bearer session-123"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            {"mock_clinical_records": "../../demo-data/records/hospital-a.json"},
            "container",
        ),
        ({"storage_dir": "../.storage/hospital-a"}, "container"),
        ({"port": 80}, "port"),
        ({"node_ref": "Hôpital A"}, "node_ref"),
        ({"governance_public_key": "key.pem"}, "--governance-public-key"),
    ],
    ids=["records-path", "storage", "port", "ref", "key-in-file"],
)
def test_a_configuration_outside_the_container_layout_is_refused(
    tmp_path, change, message
):
    source = json.loads((CONTAINER_CONFIGS / "hospital-a.json").read_text("utf-8"))
    path = tmp_path / "node.json"
    path.write_text(json.dumps({**source, **change}), encoding="utf-8")

    with pytest.raises(bp.PackageError, match=message):
        bp.build(
            path,
            "dec-hospital-a",
            image_archive(tmp_path),
            tmp_path / "dist",
            fetch=governance(),
            now=NOW,
        )


def test_the_image_archive_must_hold_the_named_image(tmp_path):
    with pytest.raises(bp.PackageError, match="does not contain"):
        build(tmp_path, archive=image_archive(tmp_path, tags=("other/image:1",)))

    not_an_archive = tmp_path / "x.tar"
    not_an_archive.write_text("nope")
    with pytest.raises(bp.PackageError, match="not a docker save archive"):
        build(tmp_path, archive=not_an_archive)


def test_an_archive_without_an_oci_index_still_pins_the_image(tmp_path):
    image = bp.read_image_archive(
        image_archive(tmp_path, with_index=False), bp.DEFAULT_IMAGE_REF
    )

    assert image.accepted_ids == (f"sha256:{CONFIG_DIGEST}",)


def test_the_governance_public_key_is_bootstrap_trust_material(tmp_path):
    key = tmp_path / "governance.pub.pem"
    key.write_text(
        "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEA\n-----END PUBLIC KEY-----\n"
    )
    root = unpack(build(tmp_path, public_key_path=key), tmp_path)

    config = json.loads((root / "config" / "node.json").read_text("utf-8"))
    assert config["governance_public_key"] == "governance-public-key.pem"
    assert (
        root / "config" / "governance-public-key.pem"
    ).read_bytes() == key.read_bytes()
    assert "governance-public-key.pem:ro" in (root / "compose.yaml").read_text("utf-8")

    private = tmp_path / "governance.pem"
    private.write_text("-----BEGIN PRIVATE KEY-----\nx\n-----END PRIVATE KEY-----\n")
    with pytest.raises(bp.PackageError, match="not a PEM public key"):
        build(tmp_path, public_key_path=private)


# The helper's checks, which need no Docker. Skipped where no POSIX shell exists.
SH = shutil.which("sh")


def data_dir(tmp_path, hospital="hospital-a", skip=()):
    target = tmp_path / "hospital-data"
    target.mkdir()
    sources = {
        "clinical-records.json": DEMO_DATA / "records" / f"{hospital}.json",
        "access.json": DEMO_DATA / "access.json",
        "governance.json": DEMO_DATA / "governance.json",
        "medication-rules.json": DEMO_DATA / "medication-rules.json",
    }
    for name, source in sources.items():
        if name not in skip:
            shutil.copyfile(source, target / name)
    return target


def run_helper(root, *args):
    return subprocess.run(
        [SH, str(root / "install.sh"), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.skipif(SH is None, reason="no POSIX shell")
def test_the_helper_verifies_the_package_and_the_data_without_docker(tmp_path):
    root = unpack(build(tmp_path), tmp_path)

    result = run_helper(root, "--data-dir", str(data_dir(tmp_path)), "--verify-only")

    assert result.returncode == 0, result.stderr
    assert "Package and data checked." in result.stdout
    assert not (root / ".env").exists()


@pytest.mark.skipif(SH is None, reason="no POSIX shell")
def test_the_helper_refuses_a_changed_package(tmp_path):
    root = unpack(build(tmp_path), tmp_path)
    config = root / "config" / "node.json"
    config.write_text(
        config.read_text("utf-8").replace("8101", "8102"), encoding="utf-8"
    )

    result = run_helper(root, "--data-dir", str(data_dir(tmp_path)), "--verify-only")

    assert result.returncode == 1
    assert "corrupted or was changed" in result.stderr


@pytest.mark.skipif(SH is None, reason="no POSIX shell")
def test_the_helper_needs_every_data_file(tmp_path):
    root = unpack(build(tmp_path), tmp_path)

    missing = run_helper(
        root,
        "--data-dir",
        str(data_dir(tmp_path, skip={"access.json"})),
        "--verify-only",
    )
    no_dir = run_helper(root, "--verify-only")

    assert missing.returncode == 2
    assert "missing from" in missing.stderr and "access.json" in missing.stderr
    assert no_dir.returncode == 2
    assert "--data-dir is required" in no_dir.stderr
