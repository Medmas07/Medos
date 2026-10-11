"""Web Push message encryption, RFC 8291 with the aes128gcm content coding (RFC 8188).

UnifiedPush requires every push message to be encrypted this way, to the keys the
device registered: the push server relays bytes it cannot read. One record, no
padding. Checked against the test vector of RFC 8291, Appendix A.
"""

import hashlib
import hmac
import os
import struct

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

RECORD_SIZE = 4096


def _hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def _public_bytes(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)


def encrypt(
    plaintext: bytes,
    ua_public: bytes,
    auth_secret: bytes,
    *,
    sender_key: ec.EllipticCurvePrivateKey | None = None,
    salt: bytes | None = None,
) -> bytes:
    """The aes128gcm body of a push message. `sender_key` and `salt` are for tests."""
    sender_key = sender_key or ec.generate_private_key(ec.SECP256R1())
    salt = salt or os.urandom(16)
    as_public = _public_bytes(sender_key)
    ua_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public)
    ecdh_secret = sender_key.exchange(ec.ECDH(), ua_key)

    # RFC 8291 section 3.3: combine the shared secret and the authentication secret.
    prk_key = _hmac(auth_secret, ecdh_secret)
    key_info = b"WebPush: info\x00" + ua_public + as_public
    ikm = _hmac(prk_key, key_info + b"\x01")

    # RFC 8188 section 2.2: content encryption key and nonce.
    prk = _hmac(salt, ikm)
    cek = _hmac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = _hmac(prk, b"Content-Encoding: nonce\x00\x01")[:12]

    # One record: the plaintext, then the last-record delimiter 0x02.
    ciphertext = AESGCM(cek).encrypt(nonce, plaintext + b"\x02", None)
    header = salt + struct.pack("!IB", RECORD_SIZE, len(as_public)) + as_public
    return header + ciphertext
