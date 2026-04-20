"""Ed25519 default signer for Sentinel (v3.4 Evidence Release).

This module provides :class:`Ed25519Signer` — the default cryptographic
signer for decision attestations. Ed25519 is fast, small (64-byte
signatures, 32-byte public keys), widely interoperable, and shipped
by every serious crypto library.

Install::

    pip install 'sentinel-kernel[ed25519]'   # or [pdf] / [dev]

Usage::

    from sentinel import Sentinel
    # Default: loads or creates a key at ~/.sentinel/ed25519.key
    sentinel = Sentinel()

    # Explicit signer:
    from sentinel.crypto.ed25519_signer import Ed25519Signer
    signer = Ed25519Signer.from_path("/secure/keystore/agent.key")
    sentinel = Sentinel(signer=signer)

    # Opt out of signing entirely:
    sentinel = Sentinel(signer=None)

Sovereignty guarantees
----------------------
- Keys live on the operator's filesystem (``0o600`` mode). Never
  transmitted, never written to the trace store.
- Signing runs entirely in-process. Zero network calls.
- Works fully air-gapped. The verifier needs only the public key.

License posture
---------------
``cryptography`` (pyca) is community-maintained under BSD-3/Apache-2.0
dual licensing. It is not US-incorporated, makes no network calls,
and is installable entirely from local wheels. It satisfies
Sentinel's three invariants.
"""

from __future__ import annotations

import base64
import contextlib
import os
from pathlib import Path
from typing import Any

_MISSING_DEP_MESSAGE = (
    "Ed25519 signing requires the `cryptography` library. Install "
    "the extra:\n    pip install 'sentinel-kernel[ed25519]'\n"
    "or install it directly:\n    pip install 'cryptography>=42.0'"
)


try:  # pragma: no cover - environment dependent
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )

    _HAS_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover - hit only when extra not installed
    _HAS_CRYPTOGRAPHY = False
    Ed25519PrivateKey = None  # type: ignore[assignment,misc]
    Ed25519PublicKey = None  # type: ignore[assignment,misc]
    InvalidSignature = None  # type: ignore[assignment,misc]
    serialization = None  # type: ignore[assignment]


_ENV_KEY_PATH = "SENTINEL_KEY_PATH"
_ENV_DISABLE = "SENTINEL_DEFAULT_SIGNER"


def _default_key_path() -> Path:
    """Resolve the canonical on-disk key path.

    Honours ``SENTINEL_KEY_PATH`` if set, otherwise falls back to
    ``~/.sentinel/ed25519.key``.
    """
    env = os.environ.get(_ENV_KEY_PATH)
    if env:
        return Path(env).expanduser()
    return Path.home() / ".sentinel" / "ed25519.key"


class Ed25519Signer:
    """Sign and verify canonical payloads with Ed25519.

    Construct by loading from disk (:meth:`from_path`,
    :meth:`from_default_key`) or by generating a new keypair
    (:meth:`generate`). The signer exposes :meth:`sign` returning a
    string of the form ``"Ed25519:<base64>"`` that is compatible with
    the rest of Sentinel's signature plumbing.
    """

    algorithm = "Ed25519"
    _SIGNATURE_PREFIX = "Ed25519:"

    def __init__(self, private_key: Any, public_key: Any) -> None:
        if not _HAS_CRYPTOGRAPHY:  # pragma: no cover - only hit when extra missing
            raise ImportError(_MISSING_DEP_MESSAGE)
        self._private_key = private_key
        self._public_key = public_key

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def generate(cls) -> Ed25519Signer:
        """Generate a fresh Ed25519 keypair in memory (no disk I/O)."""
        if not _HAS_CRYPTOGRAPHY:  # pragma: no cover - only hit when extra missing
            raise ImportError(_MISSING_DEP_MESSAGE)
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return cls(private_key, public_key)

    @classmethod
    def from_path(cls, path: Path | str) -> Ed25519Signer:
        """Load a signer from a PEM-encoded private key at ``path``.

        The public key is derived from the private key.
        """
        if not _HAS_CRYPTOGRAPHY:  # pragma: no cover - only hit when extra missing
            raise ImportError(_MISSING_DEP_MESSAGE)
        p = Path(path).expanduser()
        pem_bytes = p.read_bytes()
        private_key = serialization.load_pem_private_key(
            pem_bytes, password=None
        )
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError(
                f"key at {p} is not an Ed25519 private key "
                f"(got {type(private_key).__name__})"
            )
        public_key = private_key.public_key()
        return cls(private_key, public_key)

    @classmethod
    def from_default_key(
        cls,
        *,
        create_if_missing: bool = True,
    ) -> Ed25519Signer | None:
        """Load or create the default signer.

        The default key path is ``SENTINEL_KEY_PATH`` if set, otherwise
        ``~/.sentinel/ed25519.key``.

        Returns ``None`` when the library is unusable here — either
        ``cryptography`` is not installed, the environment variable
        ``SENTINEL_DEFAULT_SIGNER=off`` is set, or the key path is
        not writable (CI sandboxes, read-only filesystems). The caller
        is expected to treat ``None`` as "no signing configured", which
        is the same behaviour as pre-v3.4.

        :param create_if_missing: when True (default), a new keypair is
            generated and persisted with mode ``0o600`` if no file
            exists at the default path. When False, missing keys cause
            ``None`` to be returned.
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
            # Unwriteable filesystem / permission denied / key path
            # points at a directory. Fall back to no-signer rather
            # than crashing Sentinel() construction.
            return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path | str) -> Path:
        """Write the private key to ``path`` as PEM with mode 0o600.

        Creates parent directories as needed. Safe to call multiple
        times — the file is overwritten atomically-ish.

        :returns: the resolved :class:`Path`.
        """
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
        """Return the PEM-encoded SubjectPublicKeyInfo for verifiers."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    # ------------------------------------------------------------------
    # Core sign / verify
    # ------------------------------------------------------------------

    def sign(self, payload: bytes) -> str:
        """Sign ``payload`` and return ``"Ed25519:<base64>"``."""
        raw = self._private_key.sign(payload)
        return self._SIGNATURE_PREFIX + base64.b64encode(raw).decode("ascii")

    def verify(self, payload: bytes, signature: str) -> bool:
        """Verify a signature produced by :meth:`sign`. Zero network."""
        if not signature.startswith(self._SIGNATURE_PREFIX):
            return False
        encoded = signature[len(self._SIGNATURE_PREFIX):]
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error):
            return False
        try:
            self._public_key.verify(raw, payload)
        except InvalidSignature:
            return False
        return True


__all__ = [
    "Ed25519Signer",
]
