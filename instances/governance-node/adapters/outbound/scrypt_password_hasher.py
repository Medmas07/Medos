"""PasswordHasher with the standard library's scrypt (HC-211, ADR-0010).

A hash is stored as `scrypt$<n>$<r>$<p>$<salt>$<key>`, salt and key in base64, so its
cost parameters travel with it and can be raised for new hashes without breaking old
ones. The default cost (n=2^15, r=8, p=3, 32 MiB) is one of OWASP's scrypt settings.
"""

import base64
import hashlib
import hmac
import secrets

PREFIX = "scrypt"
DEFAULT_COST = (2**15, 8, 3)
SALT_BYTES = 16
KEY_BYTES = 32


class InvalidPasswordHash(ValueError):
    pass


def _maxmem(n: int, r: int, p: int) -> int:
    # scrypt needs about 128 * r * (n + p) bytes; leave OpenSSL some room.
    return 2 * 128 * r * (n + p)


def _derive(password: str, salt: bytes, n: int, r: int, p: int, size: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        maxmem=_maxmem(n, r, p),
        dklen=size,
    )


def parse(encoded: str) -> tuple[int, int, int, bytes, bytes]:
    """Its cost, salt, and key; InvalidPasswordHash if it is not one of ours."""
    parts = encoded.split("$")
    try:
        prefix, n, r, p, salt, key = parts
        n, r, p = int(n), int(r), int(p)
        salt, key = (
            base64.b64decode(salt, validate=True),
            base64.b64decode(key, validate=True),
        )
    except ValueError as error:
        raise InvalidPasswordHash("not a scrypt password hash") from error
    if prefix != PREFIX or n < 2 or n & (n - 1) or not 1 <= r <= 32 or not 1 <= p <= 16:
        raise InvalidPasswordHash("not a scrypt password hash with a usable cost")
    if len(salt) < SALT_BYTES or len(key) < KEY_BYTES:
        raise InvalidPasswordHash("scrypt password hash salt or key too short")
    return n, r, p, salt, key


class ScryptPasswordHasher:
    def __init__(self, cost: tuple[int, int, int] = DEFAULT_COST) -> None:
        self._cost = cost
        # Verified against when there is no stored hash, at the same cost.
        self._absent = self.hash(secrets.token_urlsafe(16))

    def hash(self, password: str) -> str:
        n, r, p = self._cost
        salt = secrets.token_bytes(SALT_BYTES)
        key = _derive(password, salt, n, r, p, KEY_BYTES)
        return "$".join(
            (
                PREFIX,
                str(n),
                str(r),
                str(p),
                base64.b64encode(salt).decode("ascii"),
                base64.b64encode(key).decode("ascii"),
            )
        )

    def verify(self, password: str, encoded: str | None) -> bool:
        n, r, p, salt, key = parse(encoded if encoded is not None else self._absent)
        candidate = _derive(password, salt, n, r, p, len(key))
        return hmac.compare_digest(candidate, key) and encoded is not None
