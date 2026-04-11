"""Quantum-safe trace signing for Sentinel.

Uses ML-DSA-65 (FIPS 204) — NIST post-quantum standard.
BSI TR-02102-1 recommended algorithm.

The key difference from cloud competitors: keys are stored
CLIENT-SIDE — never on external servers. All cryptography runs
in-process. Works fully air-gapped. No API key, no network, no
server.

Install::

    pip install sentinel-kernel[pqc]

Usage::

    from sentinel.crypto import QuantumSafeSigner

    QuantumSafeSigner.generate_keypair("/etc/sentinel/keys/")

    signer = QuantumSafeSigner(key_path="/etc/sentinel/keys/signing.key")
    sentinel = Sentinel(signer=signer)

Keys never leave your infrastructure. The public key can be shared
with anyone who needs to verify traces. The private key stays
operator-side, forever.
"""

from __future__ import annotations

import base64
import contextlib
import os
from pathlib import Path

_MISSING_DEP_MESSAGE = (
    "Quantum-safe signing requires liboqs-python. Install the extra:\n"
    "    pip install sentinel-kernel[pqc]\n"
    "Note: requires libssl and libcrypto on your system."
)

try:  # pragma: no cover - environment dependent
    import oqs
    _HAS_OQS = True
except ImportError:  # pragma: no cover - hit only when extra not installed
    _HAS_OQS = False
    oqs = None

class QuantumSafeSigner:
    """Sign and verify Sentinel traces with a post-quantum algorithm.

    Default algorithm: ``ML-DSA-65`` (FIPS 204), which is BSI
    TR-02102-1 recommended.
    """

    SUPPORTED_ALGORITHMS = {"ML-DSA-44", "ML-DSA-65", "ML-DSA-87"}
    SIGNATURE_PREFIX_FMT = "{algorithm}:"

    def __init__(
        self,
        algorithm: str = "ML-DSA-65",
        key_path: str | None = None,
        public_key_path: str | None = None,
    ) -> None:
        if not _HAS_OQS:
            raise ImportError(_MISSING_DEP_MESSAGE)

        if algorithm not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"algorithm must be one of {sorted(self.SUPPORTED_ALGORITHMS)}, got {algorithm!r}"
            )
        self.algorithm = algorithm
        self.key_path = key_path
        self.public_key_path = public_key_path

        self._private_key: bytes | None = None
        self._public_key: bytes | None = None
        if key_path:
            self._private_key = Path(key_path).read_bytes()
        if public_key_path:
            self._public_key = Path(public_key_path).read_bytes()

    @classmethod
    def generate_keypair(
        cls,
        output_dir: str,
        algorithm: str = "ML-DSA-65",
    ) -> None:
        """Generate a signing keypair and save to ``output_dir``.

        Creates::

            {output_dir}/signing.key   (private key — protect this)
            {output_dir}/signing.pub   (public key — can be shared)

        Key material is never printed.
        """
        if not _HAS_OQS:
            raise ImportError(_MISSING_DEP_MESSAGE)
        if algorithm not in cls.SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"algorithm must be one of {sorted(cls.SUPPORTED_ALGORITHMS)}, got {algorithm!r}"
            )

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        with oqs.Signature(algorithm) as sig:
            public_key = sig.generate_keypair()
            private_key = sig.export_secret_key()

        priv_path = out / "signing.key"
        pub_path = out / "signing.pub"
        priv_path.write_bytes(private_key)
        pub_path.write_bytes(public_key)
        # Best-effort restrict private key mode
        with contextlib.suppress(OSError):  # pragma: no cover - Windows etc.
            os.chmod(priv_path, 0o600)

        print(f"Generated {algorithm} keypair:")
        print(f"  private: {priv_path} (mode 600 — keep secret)")
        print(f"  public:  {pub_path} (share freely to verify)")

    def sign(self, data: bytes) -> str:
        """Sign ``data`` and return ``{algorithm}:{base64(sig)}``."""
        if self._private_key is None:
            raise RuntimeError("no private key loaded — pass key_path to __init__")
        with oqs.Signature(self.algorithm, self._private_key) as signer:
            signature = signer.sign(data)
        encoded = base64.b64encode(signature).decode("ascii")
        return f"{self.algorithm}:{encoded}"

    def verify(self, data: bytes, signature: str) -> bool:
        """Verify ``signature`` for ``data``. Returns True if valid.

        All in-process. Zero network calls.
        """
        if self._public_key is None:
            raise RuntimeError("no public key loaded — pass public_key_path to __init__")
        if ":" not in signature:
            return False
        prefix, encoded = signature.split(":", 1)
        if prefix != self.algorithm:
            return False
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, Exception):
            return False
        with oqs.Signature(self.algorithm) as verifier:
            return bool(verifier.verify(data, raw, self._public_key))

    # For tests / generic use-cases where caller has kept the keypair in memory
    def install_memory_keys(
        self,
        *,
        private_key: bytes | None = None,
        public_key: bytes | None = None,
    ) -> None:
        """Install an in-memory keypair without touching disk.

        Only used by tests and short-lived scripts — production
        deployments should rely on ``key_path`` / ``public_key_path``.
        """
        if private_key is not None:
            self._private_key = private_key
        if public_key is not None:
            self._public_key = public_key
