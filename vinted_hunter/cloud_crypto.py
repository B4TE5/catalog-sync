"""Cifrado autenticado de artefactos públicos con separación de propósito."""

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITERATIONS = 600_000
BOARD_CONTEXT = b"catalog-sync:board:v1"
STATE_CONTEXT = b"catalog-sync:state:v1"


def encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def decode(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def derive(key: str, salt: bytes) -> bytes:
    if len(base64.b64decode(key + "=" * (-len(key) % 4), altchars=b"-_", validate=True)) != 32:
        raise ValueError("La clave debe representar 32 bytes en base64url")
    return PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    ).derive(key.encode())


def seal(data: bytes, key: str, context: bytes) -> str:
    salt, nonce = os.urandom(16), os.urandom(12)
    payload = AESGCM(derive(key, salt)).encrypt(nonce, data, context)
    return json.dumps(
        {"v": 1, "salt": encode(salt), "nonce": encode(nonce), "data": encode(payload)},
        separators=(",", ":"),
    )


def unseal(envelope: str, key: str, context: bytes) -> bytes:
    parsed: dict[str, Any] = json.loads(envelope)
    if parsed.get("v") != 1:
        raise ValueError("Versión de artefacto cifrado incompatible")
    salt, nonce = decode(parsed["salt"]), decode(parsed["nonce"])
    if len(salt) != 16 or len(nonce) != 12:
        raise ValueError("Parámetros de cifrado inválidos")
    return AESGCM(derive(key, salt)).decrypt(nonce, decode(parsed["data"]), context)
