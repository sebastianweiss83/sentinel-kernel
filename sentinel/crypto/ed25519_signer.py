"""Ed25519 signer — default cryptographic signer for attestations.

Wraps pyca/cryptography. Keys live on the operator's filesystem
(mode ``0o600``) and are never transmitted. Install the
``[ed25519]`` / ``[pdf]`` / ``[dev]`` extra to enable.
"""

from __future__ import annotations

import base64
import contextlib
import os
from pathlib import Path
from typing import Any

_MISSING_DEP = (
    "Ed25519 signing requires `cryptography`. Install:\n"
    "    pip install 'sentinel-kernel[ed25519]'"
)

try:  # pragma: no cover - environment dependent
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )

    _HAS_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover - only when extra missing
    _HAS_CRYPTOGRAPHY = False
    Ed25519PrivateKey = None  # type: ignore[assignment,misc]
    Ed25519PublicKey = None  # type: ignore[assignment,misc]
    InvalidSignature = None  # type: ignore[assignment,misc]
    serialization = None  # type: ignore[assignment]


_ENV_KEY_PATH = "SENTINEL_KEY_PATH"
_ENV_DISABLE = "SENTINEL_DEFAULT_SIGNER"


def _default_key_path() -> Path:
    """``$SENTINEL_KEY_PATH`` if set, else ``~/.sentinel/ed25519.key``."""
    env = os.environ.get(_ENV_KEY_PATH)
    if env:
        return Path(env).expanduser()
    return Path.home() / ".sentinel" / "ed25519.key"


class Ed25519Signer:
    """Signer for canonical byte payloads.

    Construct via :meth:`from_default_key`, :meth:`from_path`, or
    :meth:`generate`. :meth:`sign` returns ``"Ed25519:<base64>"``.
    """

    algorithm = "Ed25519"
    _PREFIX = "Ed25519:"

    def __init__(self, private_key: Any, public_key: Any) -> None:
        if not _HAS_CRYPTOGRAPHY:  # pragma: no cover - only hit when extra missing
            raise ImportError(_MISSING_DEP)
        self._private_key = private_key
        self._public_key = public_key

    @classmethod
    def generate(cls) -> Ed25519Signer:
        """Fresh in-memory keypair."""
        if not _HAS_CRYPTOGRAPHY:  # pragma: no cover - only hit when extra missing
            raise ImportError(_MISSING_DEP)
        private_key = Ed25519PrivateKey.generate()
        return cls(private_key, private_key.public_key())

    @classmethod
    def from_path(cls, path: Path | str) -> Ed25519Signer:
        """Load a signer from a PEM-encoded private key file."""
        if not _HAS_CRYPTOGRAPHY:  # pragma: no cover - only hit when extra missing
            raise ImportError(_MISSING_DEP)
        p = Path(path).expanduser()
        private_key = serialization.load_pem_private_key(p.read_bytes(), password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError(
                f"key at {p} is not an Ed25519 private key "
                f"(got {type(private_key).__name__})"
            )
        return cls(private_key, private_key.public_key())

    @classmethod
    def from_default_key(cls, *, create_if_missing: bool = True) -> Ed25519Signer | None:
        """Load or create the default signer.

        Returns ``None`` if ``cryptography`` isn't installed, if
        ``SENTINEL_DEFAULT_SIGNER=off``, or if the key path isn't
        writable — callers treat ``None`` as the pre-v3.4 no-signer
        default.
        """
        if not _HAS_CRYPTOGRAPHY:  # pragma: no cover - only hit when extra missing
            return None
        if os.environ.get(_ENV_DISABLE, "").lower() in {"off", "0", "no"}:
            return None

        path = _default_key_path()
        try:
            if path.exists():
                return cls.from_path(path)
            if not create_if_missing:
                return None
            signer = cls.generate()
            signer.save(path)
            return signer
        except OSError:
            # Unwriteable FS or permission denied — fall back to
            # no-signer rather than crashing Sentinel() construction.
            return None

    def save(self, path: Path | str) -> Path:
        """Write the private key as PEM with mode ``0o600``."""
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        target.write_bytes(pem)
        with contextlib.suppress(OSError):  # pragma: no cover - Windows etc.
            os.chmod(target, 0o600)
        return target

    def public_key_pem(self) -> bytes:
        pem: bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem

    def sign(self, payload: bytes) -> str:
        raw = self._private_key.sign(payload)
        return self._PREFIX + base64.b64encode(raw).decode("ascii")

    def verify(self, payload: bytes, signature: str) -> bool:
        if not signature.startswith(self._PREFIX):
            return False
        try:
            raw = base64.b64decode(signature[len(self._PREFIX):], validate=True)
        except ValueError:
            # Covers both binascii.Error (ValueError subclass) and plain
            # garbage input.
            return False
        try:
            self._public_key.verify(raw, payload)
        except InvalidSignature:
            return False
        return True


__all__ = ["Ed25519Signer"]
