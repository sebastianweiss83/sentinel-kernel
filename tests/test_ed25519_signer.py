"""Tests for Ed25519 default signer (v3.4 Evidence Release).

Covers the :class:`sentinel.crypto.ed25519_signer.Ed25519Signer` class:
key generation, persistence, default-path resolution, sign/verify
round-trip, and the new Sentinel() default-signer behaviour.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Skip the whole module when the [ed25519] extra isn't installed —
# the smoke-test / bare-install CI path does not pull `cryptography`.
pytest.importorskip("cryptography")

from sentinel import Sentinel  # noqa: E402
from sentinel.crypto.ed25519_signer import (  # noqa: E402
    _ENV_DISABLE,
    _ENV_KEY_PATH,
    Ed25519Signer,
    _default_key_path,
)
from sentinel.storage import SQLiteStorage  # noqa: E402

# ---------------------------------------------------------------------------
# Keypair generation + persistence
# ---------------------------------------------------------------------------


def test_generate_produces_signer_with_algorithm() -> None:
    signer = Ed25519Signer.generate()
    assert signer.algorithm == "Ed25519"


def test_sign_produces_prefixed_base64() -> None:
    signer = Ed25519Signer.generate()
    sig = signer.sign(b"payload")
    assert sig.startswith("Ed25519:")
    assert len(sig) > len("Ed25519:")


def test_verify_accepts_valid_signature() -> None:
    signer = Ed25519Signer.generate()
    sig = signer.sign(b"payload-under-test")
    assert signer.verify(b"payload-under-test", sig) is True


def test_verify_rejects_tampered_payload() -> None:
    signer = Ed25519Signer.generate()
    sig = signer.sign(b"payload")
    assert signer.verify(b"tampered", sig) is False


def test_verify_rejects_wrong_prefix() -> None:
    signer = Ed25519Signer.generate()
    sig = signer.sign(b"payload")
    altered = "ML-DSA-65:" + sig.removeprefix("Ed25519:")
    assert signer.verify(b"payload", altered) is False


def test_verify_rejects_invalid_base64() -> None:
    signer = Ed25519Signer.generate()
    assert signer.verify(b"payload", "Ed25519:not-base64!!!") is False


def test_verify_rejects_wrong_key() -> None:
    signer_a = Ed25519Signer.generate()
    signer_b = Ed25519Signer.generate()
    sig = signer_a.sign(b"payload")
    assert signer_b.verify(b"payload", sig) is False


# ---------------------------------------------------------------------------
# On-disk persistence
# ---------------------------------------------------------------------------


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    key_path = tmp_path / "keys" / "test.key"
    signer = Ed25519Signer.generate()
    written = signer.save(key_path)
    assert written == key_path
    assert key_path.exists()
    # Unix mode 0o600 restricts permissions on non-Windows platforms.
    if sys.platform != "win32":
        mode = key_path.stat().st_mode & 0o777
        assert mode == 0o600, f"expected 0600, got {mode:o}"

    loaded = Ed25519Signer.from_path(key_path)
    sig = loaded.sign(b"roundtrip-payload")
    assert signer.verify(b"roundtrip-payload", sig) is True


def test_from_path_rejects_non_ed25519_key(tmp_path: Path) -> None:
    not_a_key = tmp_path / "not-a-key.pem"
    not_a_key.write_bytes(b"this is not a key")
    # pyca/cryptography raises a ValueError subclass on unparseable
    # PEM input; any exception is acceptable here — the guarantee is
    # that ``from_path`` does not silently return a broken signer.
    with pytest.raises(Exception):  # noqa: B017 - any exception fails the load
        Ed25519Signer.from_path(not_a_key)


def test_from_path_rejects_valid_non_ed25519_pem(tmp_path: Path) -> None:
    """A valid PEM that is not Ed25519 (e.g. RSA) must be rejected."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = rsa_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path = tmp_path / "rsa.key"
    key_path.write_bytes(pem)

    with pytest.raises(ValueError, match="not an Ed25519 private key"):
        Ed25519Signer.from_path(key_path)


def test_public_key_pem_shape() -> None:
    signer = Ed25519Signer.generate()
    pem = signer.public_key_pem()
    assert pem.startswith(b"-----BEGIN PUBLIC KEY-----")
    assert pem.rstrip().endswith(b"-----END PUBLIC KEY-----")


# ---------------------------------------------------------------------------
# Default-key resolution
# ---------------------------------------------------------------------------


def test_default_key_path_honours_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_ENV_KEY_PATH, "/tmp/custom-key-path.pem")
    assert _default_key_path() == Path("/tmp/custom-key-path.pem")


def test_default_key_path_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_ENV_KEY_PATH, raising=False)
    assert _default_key_path() == Path.home() / ".sentinel" / "ed25519.key"


def test_from_default_key_creates_if_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key_path = tmp_path / "nested" / "ed25519.key"
    monkeypatch.setenv(_ENV_KEY_PATH, str(key_path))
    monkeypatch.delenv(_ENV_DISABLE, raising=False)

    signer = Ed25519Signer.from_default_key()
    assert signer is not None
    assert key_path.exists()

    # Second call re-loads the same key, not a new one.
    reloaded = Ed25519Signer.from_default_key()
    assert reloaded is not None
    sig = signer.sign(b"x")
    assert reloaded.verify(b"x", sig) is True


def test_from_default_key_respects_create_if_missing_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key_path = tmp_path / "nonexistent.key"
    monkeypatch.setenv(_ENV_KEY_PATH, str(key_path))
    monkeypatch.delenv(_ENV_DISABLE, raising=False)

    signer = Ed25519Signer.from_default_key(create_if_missing=False)
    assert signer is None
    assert not key_path.exists()


def test_from_default_key_returns_none_when_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_ENV_KEY_PATH, str(tmp_path / "x.key"))
    monkeypatch.setenv(_ENV_DISABLE, "off")
    assert Ed25519Signer.from_default_key() is None


def test_from_default_key_returns_none_on_filesystem_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Point the key path at a path we can't create (parent is a file, not a dir).
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"I am a regular file")
    bad_path = blocker / "ed25519.key"  # parent is a file, cannot mkdir
    monkeypatch.setenv(_ENV_KEY_PATH, str(bad_path))
    monkeypatch.delenv(_ENV_DISABLE, raising=False)

    assert Ed25519Signer.from_default_key() is None


# ---------------------------------------------------------------------------
# Sentinel() default wiring
# ---------------------------------------------------------------------------


def test_sentinel_default_signer_is_ed25519(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_ENV_KEY_PATH, str(tmp_path / "ed25519.key"))
    monkeypatch.delenv(_ENV_DISABLE, raising=False)

    s = Sentinel(storage=SQLiteStorage(":memory:"))
    assert s._signer is not None
    assert s._signer.algorithm == "Ed25519"


def test_sentinel_explicit_none_signer_opts_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_ENV_KEY_PATH, str(tmp_path / "ed25519.key"))

    s = Sentinel(storage=SQLiteStorage(":memory:"), signer=None)
    assert s._signer is None


def test_sentinel_none_signer_produces_unsigned_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With signer=None, _sign_trace takes its early-return branch."""
    monkeypatch.setenv(_ENV_KEY_PATH, str(tmp_path / "ed25519.key"))

    s = Sentinel(storage=SQLiteStorage(":memory:"), signer=None)

    async def act(ctx: dict) -> dict:
        return {"handled": True}

    traced = s.trace(act)
    asyncio.run(traced({"i": 1}))

    [t] = s.storage.query()
    assert t.signature is None
    assert t.signature_algorithm is None


def test_sentinel_default_signer_populates_trace_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_ENV_KEY_PATH, str(tmp_path / "ed25519.key"))
    monkeypatch.delenv(_ENV_DISABLE, raising=False)

    s = Sentinel(storage=SQLiteStorage(":memory:"))

    async def act(ctx: dict) -> dict:
        return {"handled": True}

    traced = s.trace(act)
    asyncio.run(traced({"i": 1}))

    [t] = s.storage.query()
    assert t.signature is not None
    assert t.signature.startswith("Ed25519:")
    assert t.signature_algorithm == "Ed25519"


def test_sentinel_default_signer_disabled_by_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_ENV_KEY_PATH, str(tmp_path / "ed25519.key"))
    monkeypatch.setenv(_ENV_DISABLE, "off")

    s = Sentinel(storage=SQLiteStorage(":memory:"))
    assert s._signer is None


# ---------------------------------------------------------------------------
# CLI — `sentinel key init` / path / public (in-process for coverage)
# ---------------------------------------------------------------------------


from sentinel import cli  # noqa: E402 — imported late so module state is fresh


def test_cli_key_init_creates_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    key_path = tmp_path / "cli.key"
    monkeypatch.setenv(_ENV_KEY_PATH, str(key_path))
    monkeypatch.delenv(_ENV_DISABLE, raising=False)

    rc = cli.main(["key", "init"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert key_path.exists()
    assert "BEGIN PUBLIC KEY" in captured.out


def test_cli_key_init_refuses_to_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    key_path = tmp_path / "existing.key"
    Ed25519Signer.generate().save(key_path)
    before = key_path.read_bytes()

    monkeypatch.setenv(_ENV_KEY_PATH, str(key_path))

    rc = cli.main(["key", "init"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "already exists" in captured.err
    assert key_path.read_bytes() == before


def test_cli_key_init_force_overwrites(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    key_path = tmp_path / "existing.key"
    Ed25519Signer.generate().save(key_path)
    before = key_path.read_bytes()

    monkeypatch.setenv(_ENV_KEY_PATH, str(key_path))

    rc = cli.main(["key", "init", "--force"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert key_path.read_bytes() != before


def test_cli_key_init_honours_explicit_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    explicit = tmp_path / "explicit.key"
    monkeypatch.delenv(_ENV_KEY_PATH, raising=False)
    monkeypatch.delenv(_ENV_DISABLE, raising=False)

    rc = cli.main(["key", "init", "--path", str(explicit)])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert explicit.exists()


def test_cli_key_path_prints_resolved_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(_ENV_KEY_PATH, str(tmp_path / "somewhere.key"))

    rc = cli.main(["key", "path"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert str(tmp_path / "somewhere.key") in captured.out


def test_cli_key_public_prints_pem(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    key_path = tmp_path / "pub.key"
    Ed25519Signer.generate().save(key_path)
    monkeypatch.setenv(_ENV_KEY_PATH, str(key_path))

    rc = cli.main(["key", "public"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert "BEGIN PUBLIC KEY" in captured.out


def test_cli_key_public_honours_explicit_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    key_path = tmp_path / "alt.key"
    Ed25519Signer.generate().save(key_path)

    rc = cli.main(["key", "public", "--path", str(key_path)])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert "BEGIN PUBLIC KEY" in captured.out


def test_cli_key_public_fails_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(_ENV_KEY_PATH, str(tmp_path / "missing.key"))

    rc = cli.main(["key", "public"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "no Ed25519 key" in captured.err


def test_cli_key_no_subcommand_prints_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli.main(["key"])
    capsys.readouterr()  # drain help output
    assert rc == 1


def test_cli_key_public_rejects_non_ed25519_key(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    not_a_key = tmp_path / "garbage.pem"
    not_a_key.write_bytes(b"not a PEM")

    rc = cli.main(["key", "public", "--path", str(not_a_key)])
    capsys.readouterr()
    assert rc == 2
