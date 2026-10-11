"""HC-211 outbound adapters: the scrypt hasher and the credential file."""

import json

import pytest

from adapters.outbound.credential_file import (
    CredentialFile,
    CredentialFileError,
    write_credential,
)
from adapters.outbound.fixture_reviewer_directory import FixtureReviewerDirectory
from adapters.outbound.scrypt_password_hasher import (
    DEFAULT_COST,
    InvalidPasswordHash,
    ScryptPasswordHasher,
    parse,
)
from tests.conftest import DEMO_DATA

# Cheap for tests; the Node uses DEFAULT_COST.
CHEAP = ScryptPasswordHasher(cost=(2**4, 8, 1))
PEOPLE = FixtureReviewerDirectory.load(DEMO_DATA / "people.json")


def test_a_hash_verifies_its_password_only():
    encoded = CHEAP.hash("correct horse battery")

    assert CHEAP.verify("correct horse battery", encoded)
    assert not CHEAP.verify("correct horse batterY", encoded)


def test_hashes_are_salted_and_carry_their_cost():
    first, second = CHEAP.hash("same"), CHEAP.hash("same")

    assert first != second
    assert first.startswith("scrypt$16$8$1$")
    assert CHEAP.verify("same", second)


def test_the_default_cost_is_owasp_scrypt():
    assert DEFAULT_COST == (2**15, 8, 3)
    n, r, p, salt, key = parse(ScryptPasswordHasher().hash("x"))
    assert (n, r, p, len(salt), len(key)) == (2**15, 8, 3, 16, 32)


def test_no_stored_hash_never_verifies():
    assert not CHEAP.verify("anything", None)


@pytest.mark.parametrize(
    "encoded",
    [
        "",
        "plain$password",
        "bcrypt$16$8$1$AAAAAAAAAAAAAAAAAAAAAA==$" + "A" * 44,
        "scrypt$15$8$1$AAAAAAAAAAAAAAAAAAAAAA==$" + "A" * 44,
        "scrypt$16$8$1$short$" + "A" * 44,
        "scrypt$16$8$1$AAAAAAAAAAAAAAAAAAAAAA==$AAAA",
    ],
)
def test_parse_rejects_what_is_not_a_usable_scrypt_hash(encoded):
    with pytest.raises(InvalidPasswordHash):
        parse(encoded)


def test_credential_file_round_trip(tmp_path):
    path = tmp_path / "credentials.json"
    write_credential(path, "usr-olfa", CHEAP.hash("first"))
    write_credential(path, "usr-mehdi", CHEAP.hash("other"))
    write_credential(path, "usr-olfa", CHEAP.hash("second"))

    credentials = CredentialFile.load(path, PEOPLE)

    assert credentials.person_refs() == ["usr-mehdi", "usr-olfa"]
    assert CHEAP.verify("second", credentials.password_hash("usr-olfa"))
    assert credentials.password_hash("usr-aymen") is None
    assert "second" not in path.read_text(encoding="utf-8")


def _file(tmp_path, entries) -> object:
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"credentials": entries}), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        ([{"person_ref": "pat-a", "password_hash": "x"}], "not a known person"),
        ([{"person_ref": "usr-olfa", "password_hash": "plain"}], "usr-olfa"),
        ([{"person_ref": "usr-olfa"}], "cannot read"),
        (
            [{"person_ref": "usr-olfa", "password_hash": CHEAP.hash("a")}] * 2,
            "appears twice",
        ),
    ],
)
def test_an_invalid_credential_file_stops_loading(tmp_path, entries, message):
    with pytest.raises(CredentialFileError, match=message):
        CredentialFile.load(_file(tmp_path, entries), PEOPLE)


def test_a_missing_credential_file_stops_loading(tmp_path):
    with pytest.raises(CredentialFileError, match="cannot read"):
        CredentialFile.load(tmp_path / "absent.json", PEOPLE)
