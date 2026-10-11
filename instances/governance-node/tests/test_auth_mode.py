import pytest

from adapters.outbound.credential_file import CredentialFileError, write_credential
from adapters.outbound.in_memory_hospital_applications import SeedError
from adapters.outbound.scrypt_password_hasher import ScryptPasswordHasher
from main import AUTH_ENV, CREDENTIALS_ENV, credentials_from_env
from tests.conftest import DEMO_DATA


def test_off_is_the_default(monkeypatch):
    monkeypatch.delenv(AUTH_ENV, raising=False)

    assert credentials_from_env(DEMO_DATA) is None


def test_required_reads_the_credential_file(monkeypatch, tmp_path):
    path = tmp_path / "credentials.json"
    write_credential(path, "usr-olfa", ScryptPasswordHasher((2**4, 8, 1)).hash("x"))
    monkeypatch.setenv(AUTH_ENV, "required")
    monkeypatch.setenv(CREDENTIALS_ENV, str(path))

    assert credentials_from_env(DEMO_DATA).person_refs() == ["usr-olfa"]


def test_required_without_a_credential_file_stops_startup(monkeypatch, tmp_path):
    monkeypatch.setenv(AUTH_ENV, "required")
    monkeypatch.setenv(CREDENTIALS_ENV, str(tmp_path / "missing.json"))

    with pytest.raises(CredentialFileError):
        credentials_from_env(DEMO_DATA)


def test_another_mode_stops_startup(monkeypatch):
    monkeypatch.setenv(AUTH_ENV, "optional")

    with pytest.raises(SeedError):
        credentials_from_env(DEMO_DATA)
