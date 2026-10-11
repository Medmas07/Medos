"""A test-only Web Push receiver: what a device's UnifiedPush connector does.

It holds the RFC 8291 user agent keys and decrypts aes128gcm push messages, to check
what the service sends. Not part of the service.
"""

import hashlib
import hmac
import os
import struct
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def _hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


@dataclass
class Receiver:
    private_key: ec.EllipticCurvePrivateKey = field(
        default_factory=lambda: ec.generate_private_key(ec.SECP256R1())
    )
    auth: bytes = field(default_factory=lambda: os.urandom(16))

    @property
    def p256dh(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            Encoding.X962, PublicFormat.UncompressedPoint
        )

    def decrypt(self, body: bytes) -> bytes:
        salt, (record_size, key_length) = body[:16], struct.unpack("!IB", body[16:21])
        as_public = body[21 : 21 + key_length]
        ciphertext = body[21 + key_length :]
        assert record_size >= len(ciphertext)
        sender = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_public)
        ecdh_secret = self.private_key.exchange(ec.ECDH(), sender)
        prk_key = _hmac(self.auth, ecdh_secret)
        ikm = _hmac(prk_key, b"WebPush: info\x00" + self.p256dh + as_public + b"\x01")
        prk = _hmac(salt, ikm)
        cek = _hmac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
        nonce = _hmac(prk, b"Content-Encoding: nonce\x00\x01")[:12]
        record = AESGCM(cek).decrypt(nonce, ciphertext, None)
        plaintext, delimiter = record.rstrip(b"\x00")[:-1], record.rstrip(b"\x00")[-1:]
        assert delimiter == b"\x02", "not a single last record"
        return plaintext
