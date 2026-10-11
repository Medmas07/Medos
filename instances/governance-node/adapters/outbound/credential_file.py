"""CredentialStore over a local JSON file of password hashes (HC-211, ADR-0010).

    {"credentials": [{"person_ref": "usr-olfa", "password_hash": "scrypt$..."}]}

The file is created on each machine with `python -m auth.set_password` and is never
committed: it holds no password, but its hashes would let anyone try to guess them
offline. Each credential must name a person of the reviewer directory; a malformed
file, an unknown person, a duplicate, or a hash that is not scrypt stops startup.
"""

import json
from pathlib import Path

from adapters.outbound.scrypt_password_hasher import InvalidPasswordHash, parse
from application.hospital_approval import ReviewerDirectory


class CredentialFileError(RuntimeError):
    pass


class CredentialFile:
    def __init__(self, hashes: dict[str, str]) -> None:
        self._hashes = dict(hashes)

    @classmethod
    def load(cls, path: Path, people: ReviewerDirectory) -> "CredentialFile":
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))["credentials"]
            pairs = [(e["person_ref"], e["password_hash"]) for e in entries]
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise CredentialFileError(
                f"cannot read credentials {path}: {error}"
            ) from error
        hashes: dict[str, str] = {}
        for person_ref, encoded in pairs:
            if person_ref in hashes:
                raise CredentialFileError(f"{path}: {person_ref} appears twice")
            if people.reviewer(person_ref) is None:
                raise CredentialFileError(f"{path}: {person_ref} is not a known person")
            try:
                parse(encoded)
            except (InvalidPasswordHash, AttributeError) as error:
                raise CredentialFileError(f"{path}: {person_ref}: {error}") from error
            hashes[person_ref] = encoded
        return cls(hashes)

    def password_hash(self, person_ref: str) -> str | None:
        return self._hashes.get(person_ref)

    def person_refs(self) -> list[str]:
        return sorted(self._hashes)


def write_credential(path: Path, person_ref: str, password_hash: str) -> None:
    """Add or replace one person's hash, keeping the others."""
    entries = []
    if path.exists():
        entries = json.loads(path.read_text(encoding="utf-8"))["credentials"]
    entries = [e for e in entries if e["person_ref"] != person_ref]
    entries.append({"person_ref": person_ref, "password_hash": password_hash})
    entries.sort(key=lambda e: e["person_ref"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"credentials": entries}, indent=2) + "\n", encoding="utf-8"
    )
    path.chmod(0o600)
