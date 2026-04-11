"""Tests for sentinel.crypto.signing — oqs is mocked entirely."""

from __future__ import annotations

import sys
import types
from contextlib import contextmanager
from pathlib import Path

import pytest

from sentinel.core.trace import DecisionTrace


class _FakeSigContext:
    """Fake oqs.Signature context manager used across tests.

    Produces deterministic "signatures" so verify/round-trip logic
    can be exercised without a real PQC library.
    """

    def __init__(self, algorithm: str, secret_key: bytes | None = None) -> None:
        self.algorithm = algorithm
        self._secret = secret_key

    def __enter__(self) -> _FakeSigContext:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def generate_keypair(self) -> bytes:
        # Public key returned; "secret" generated internally.
        self._secret = b"fake-secret-" + self.algorithm.encode()
        return b"fake-public-" + self.algorithm.encode()

    def export_secret_key(self) -> bytes:
        return self._secret or b""

    def sign(self, data: bytes) -> bytes:
        import hashlib

        return hashlib.sha256(data + (self._secret or b"")).digest()

    def verify(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        # Our fake signature was computed as sha256(data + secret),
        # and the fake secret is "fake-secret-<algorithm>".
        import hashlib

        algorithm = public_key.decode().replace("fake-public-", "")
        expected = hashlib.sha256(data + f"fake-secret-{algorithm}".encode()).digest()
        return signature == expected


@contextmanager
def _mocked_oqs() -> None:
    stub = types.ModuleType("oqs")
    stub.Signature = _FakeSigContext  # type: ignore[attr-defined]
    saved = sys.modules.get("oqs")
    sys.modules["oqs"] = stub
    # Force re-import of the signing module under the stub.
    for name in ("sentinel.crypto.signing", "sentinel.crypto"):
        sys.modules.pop(name, None)
    try:
        yield
    finally:
        if saved is None:
            sys.modules.pop("oqs", None)
        else:
            sys.modules["oqs"] = saved
        for name in ("sentinel.crypto.signing", "sentinel.crypto"):
            sys.modules.pop(name, None)


def test_signer_signs_and_verifies(tmp_path: Path) -> None:
    with _mocked_oqs():
        from sentinel.crypto.signing import QuantumSafeSigner

        QuantumSafeSigner.generate_keypair(str(tmp_path))
        signer = QuantumSafeSigner(
            key_path=str(tmp_path / "signing.key"),
            public_key_path=str(tmp_path / "signing.pub"),
        )
        data = b"payload"
        sig = signer.sign(data)
        assert sig.startswith("ML-DSA-65:")
        assert signer.verify(data, sig) is True


def test_signer_rejects_tampered_data(tmp_path: Path) -> None:
    with _mocked_oqs():
        from sentinel.crypto.signing import QuantumSafeSigner

        QuantumSafeSigner.generate_keypair(str(tmp_path))
        signer = QuantumSafeSigner(
            key_path=str(tmp_path / "signing.key"),
            public_key_path=str(tmp_path / "signing.pub"),
        )
        sig = signer.sign(b"original")
        assert signer.verify(b"tampered", sig) is False


def test_signer_rejects_wrong_prefix(tmp_path: Path) -> None:
    with _mocked_oqs():
        from sentinel.crypto.signing import QuantumSafeSigner

        QuantumSafeSigner.generate_keypair(str(tmp_path))
        signer = QuantumSafeSigner(
            key_path=str(tmp_path / "signing.key"),
            public_key_path=str(tmp_path / "signing.pub"),
        )
        assert signer.verify(b"x", "WRONG:aGVsbG8=") is False
        assert signer.verify(b"x", "no-colon") is False
        assert signer.verify(b"x", "ML-DSA-65:not-base64!@#") is False


def test_keygen_creates_two_files(tmp_path: Path) -> None:
    with _mocked_oqs():
        from sentinel.crypto.signing import QuantumSafeSigner

        QuantumSafeSigner.generate_keypair(str(tmp_path))
        assert (tmp_path / "signing.key").exists()
        assert (tmp_path / "signing.pub").exists()


def test_unsupported_algorithm_raises(tmp_path: Path) -> None:
    with _mocked_oqs():
        from sentinel.crypto.signing import QuantumSafeSigner

        with pytest.raises(ValueError):
            QuantumSafeSigner(algorithm="RSA-2048")
        with pytest.raises(ValueError):
            QuantumSafeSigner.generate_keypair(str(tmp_path), algorithm="RSA-2048")


def test_sign_without_key_raises(tmp_path: Path) -> None:
    with _mocked_oqs():
        from sentinel.crypto.signing import QuantumSafeSigner

        QuantumSafeSigner.generate_keypair(str(tmp_path))
        # Load only the public key — signing must fail
        signer = QuantumSafeSigner(public_key_path=str(tmp_path / "signing.pub"))
        with pytest.raises(RuntimeError):
            signer.sign(b"x")


def test_verify_without_public_key_raises(tmp_path: Path) -> None:
    with _mocked_oqs():
        from sentinel.crypto.signing import QuantumSafeSigner

        QuantumSafeSigner.generate_keypair(str(tmp_path))
        signer = QuantumSafeSigner(key_path=str(tmp_path / "signing.key"))
        with pytest.raises(RuntimeError):
            signer.verify(b"x", "ML-DSA-65:aGVsbG8=")


def test_missing_dep_helpful_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When liboqs-python is absent, instantiation raises a helpful ImportError."""
    saved = sys.modules.get("oqs")
    monkeypatch.setitem(sys.modules, "oqs", None)
    sys.modules.pop("sentinel.crypto.signing", None)
    sys.modules.pop("sentinel.crypto", None)
    try:
        from sentinel.crypto import signing as module

        module._HAS_OQS = False
        with pytest.raises(ImportError, match="sentinel-kernel\\[pqc\\]"):
            module.QuantumSafeSigner()
        with pytest.raises(ImportError):
            module.QuantumSafeSigner.generate_keypair(str(tmp_path))
    finally:
        if saved is not None:
            sys.modules["oqs"] = saved
        sys.modules.pop("sentinel.crypto.signing", None)
        sys.modules.pop("sentinel.crypto", None)


def test_install_memory_keys(tmp_path: Path) -> None:
    with _mocked_oqs():
        from sentinel.crypto.signing import QuantumSafeSigner

        signer = QuantumSafeSigner()
        signer.install_memory_keys(
            private_key=b"fake-secret-ML-DSA-65",
            public_key=b"fake-public-ML-DSA-65",
        )
        sig = signer.sign(b"data")
        assert signer.verify(b"data", sig) is True


def test_sentinel_signs_traces_when_signer_configured(tmp_path: Path) -> None:
    with _mocked_oqs():
        from sentinel import Sentinel
        from sentinel.crypto.signing import QuantumSafeSigner
        from sentinel.storage import SQLiteStorage

        QuantumSafeSigner.generate_keypair(str(tmp_path))
        signer = QuantumSafeSigner(
            key_path=str(tmp_path / "signing.key"),
            public_key_path=str(tmp_path / "signing.pub"),
        )

        sentinel = Sentinel(
            storage=SQLiteStorage(":memory:"),
            project="signing",
            signer=signer,
        )

        @sentinel.trace
        def act() -> dict:
            return {"ok": True}

        act()
        traces = sentinel.query(limit=1)
        assert traces[0].signature is not None
        assert traces[0].signature.startswith("ML-DSA-65:")
        assert traces[0].signature_algorithm == "ML-DSA-65"


def test_signing_airgap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    monkeypatch.setattr(
        socket.socket,
        "connect",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("net")),
    )
    with _mocked_oqs():
        from sentinel.crypto.signing import QuantumSafeSigner

        QuantumSafeSigner.generate_keypair(str(tmp_path))
        signer = QuantumSafeSigner(
            key_path=str(tmp_path / "signing.key"),
            public_key_path=str(tmp_path / "signing.pub"),
        )
        sig = signer.sign(b"airgap")
        assert signer.verify(b"airgap", sig) is True


def test_cli_keygen_with_mocked_oqs(tmp_path: Path) -> None:
    """Exercise `sentinel keygen` via the in-process CLI with a mocked oqs."""
    with _mocked_oqs():
        from sentinel import cli

        rc = cli.main(["keygen", "--output-dir", str(tmp_path / "kk")])
        assert rc == 0
        assert (tmp_path / "kk" / "signing.key").exists()
        assert (tmp_path / "kk" / "signing.pub").exists()


def test_cli_keygen_without_oqs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without oqs, keygen exits 2 with a helpful error."""
    saved = sys.modules.get("oqs")
    monkeypatch.setitem(sys.modules, "oqs", None)
    sys.modules.pop("sentinel.crypto.signing", None)
    sys.modules.pop("sentinel.crypto", None)
    try:
        from sentinel import cli
        from sentinel.crypto import signing as module

        module._HAS_OQS = False
        rc = cli.main(["keygen", "--output-dir", str(tmp_path / "kk")])
        assert rc == 2
    finally:
        if saved is not None:
            sys.modules["oqs"] = saved
        sys.modules.pop("sentinel.crypto.signing", None)
        sys.modules.pop("sentinel.crypto", None)


def test_decision_trace_carries_signature_fields() -> None:
    trace = DecisionTrace(project="t", agent="a")
    trace.signature = "ML-DSA-65:abc"
    trace.signature_algorithm = "ML-DSA-65"
    d = trace.to_dict()
    assert d["signature"] == "ML-DSA-65:abc"
    assert d["signature_algorithm"] == "ML-DSA-65"
    round_trip = DecisionTrace.from_dict(d)
    assert round_trip.signature == "ML-DSA-65:abc"
    assert round_trip.signature_algorithm == "ML-DSA-65"
