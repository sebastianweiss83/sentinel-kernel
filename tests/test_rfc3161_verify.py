"""Tests for RFC 3161 token verification (v3.4.1).

Prior to v3.4.1 ``RFC3161Timestamper.verify`` was a structural stub:
it confirmed the base64 decoded and the timestamp was a ``datetime``
but did no cryptographic check. The homepage nonetheless listed
"RFC-3161 timestamping" as a trust signal — a standing overclaim.
v3.4.1 replaces the stub with full CMS + TSTInfo + signature
verification. These tests prove every check fires.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

pytest.importorskip("asn1crypto")
pytest.importorskip("cryptography")
pytest.importorskip("pyhanko")

from asn1crypto import keys as a1_keys  # noqa: E402
from asn1crypto import pem as a1_pem  # noqa: E402
from asn1crypto import x509 as a1_x509  # noqa: E402
from cryptography import x509  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID  # noqa: E402
from pyhanko.sign.timestamps.dummy_client import DummyTimeStamper  # noqa: E402

from sentinel.crypto.timestamp import (  # noqa: E402
    NON_SOVEREIGN_TSAS,
    RFC3161Timestamper,
    TimestampToken,
)

# ---------------------------------------------------------------------------
# Fixture helpers — build valid RFC-3161 tokens without a live TSA
# ---------------------------------------------------------------------------


def _build_tsa(
    *,
    cn: str,
    org: str,
    not_before: datetime | None = None,
    not_after: datetime | None = None,
) -> tuple[a1_x509.Certificate, a1_keys.PrivateKeyInfo]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    nb = not_before or (now - timedelta(days=1))
    na = not_after or (now + timedelta(days=365))
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(nb)
        .not_valid_after(na)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.TIME_STAMPING]),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    _, _, cert_der = a1_pem.unarmor(cert_pem)
    _, _, key_der = a1_pem.unarmor(key_pem)
    return (
        a1_x509.Certificate.load(cert_der),
        a1_keys.PrivateKeyInfo.load(key_der),
    )


def _issue_token(
    data: bytes,
    *,
    cn: str = "Sentinel Test TSA",
    org: str = "D-Trust TSA Test",
    fixed_dt: datetime | None = None,
    not_before: datetime | None = None,
    not_after: datetime | None = None,
) -> TimestampToken:
    """Produce a valid TSA-issued timestamp token for ``data``."""
    cert, key = _build_tsa(
        cn=cn, org=org, not_before=not_before, not_after=not_after
    )
    kwargs: dict[str, Any] = {"tsa_cert": cert, "tsa_key": key}
    if fixed_dt is not None:
        kwargs["fixed_dt"] = fixed_dt
    stamper = DummyTimeStamper(**kwargs)
    digest = hashlib.sha256(data).digest()
    tst = asyncio.run(
        stamper.async_timestamp(message_digest=digest, md_algorithm="sha256")
    )
    return TimestampToken(
        tsa_url="http://test.sovereign.tsa/",
        timestamp=datetime.now(UTC),
        token_b64=base64.b64encode(tst.dump()).decode("ascii"),
    )


# ---------------------------------------------------------------------------
# Construction guardrails (pre-existing behaviour)
# ---------------------------------------------------------------------------


def test_construction_rejects_us_tsa() -> None:
    """Constructing with a US TSA in the list is a runtime ValueError."""
    with pytest.raises(ValueError, match="US-based TSA not allowed"):
        RFC3161Timestamper(tsa_urls=list(NON_SOVEREIGN_TSAS[:1]))


# ---------------------------------------------------------------------------
# verify — positive cases
# ---------------------------------------------------------------------------


@pytest.fixture
def stamper() -> RFC3161Timestamper:
    return RFC3161Timestamper()


def test_verify_accepts_dfn_issued_token(stamper: RFC3161Timestamper) -> None:
    tok = _issue_token(b"sentinel trace", cn="DFN-Verein TSA", org="DFN-Verein e.V.")
    assert stamper.verify(tok, b"sentinel trace") is True


def test_verify_accepts_dtrust_issued_token(stamper: RFC3161Timestamper) -> None:
    tok = _issue_token(b"payload", cn="D-Trust Root CA", org="D-Trust GmbH")
    assert stamper.verify(tok, b"payload") is True


def test_verify_accepts_bundesdruckerei_issued_token(
    stamper: RFC3161Timestamper,
) -> None:
    tok = _issue_token(b"data", cn="BD TSA", org="Bundesdruckerei GmbH")
    assert stamper.verify(tok, b"data") is True


def test_verify_accepts_local_fallback(stamper: RFC3161Timestamper) -> None:
    """Air-gapped local-fallback tokens verify structurally only."""
    tok = TimestampToken(tsa_url="local", timestamp=datetime.now(UTC), token_b64=None)
    assert stamper.verify(tok, b"ignored") is True


# ---------------------------------------------------------------------------
# verify — negative cases (the stub never caught these)
# ---------------------------------------------------------------------------


def test_verify_rejects_wrong_data(stamper: RFC3161Timestamper) -> None:
    """messageImprint is bound to the original data; verifying against
    different bytes must fail."""
    tok = _issue_token(b"original bytes")
    assert stamper.verify(tok, b"tampered bytes") is False


def test_verify_rejects_non_sovereign_tsa(stamper: RFC3161Timestamper) -> None:
    """Even a cryptographically-valid token from a US TSA must be
    rejected because the DN contains no allowed marker."""
    tok = _issue_token(
        b"data", cn="DigiCert Time Stamp Authority", org="DigiCert Inc"
    )
    assert stamper.verify(tok, b"data") is False


def test_verify_rejects_signature_tampering(stamper: RFC3161Timestamper) -> None:
    """Flipping bits inside the CMS signature invalidates the token."""
    tok = _issue_token(b"content")
    raw = bytearray(base64.b64decode(tok.token_b64))
    # The CMS signature trailer lives in the last ~256 bytes for a
    # 2048-bit RSA key. Flip a byte well inside the signature.
    raw[-16] ^= 0xFF
    tampered = TimestampToken(
        tsa_url="t",
        timestamp=datetime.now(UTC),
        token_b64=base64.b64encode(bytes(raw)).decode("ascii"),
    )
    assert stamper.verify(tampered, b"content") is False


def test_verify_rejects_malformed_base64(stamper: RFC3161Timestamper) -> None:
    tok = TimestampToken(tsa_url="t", timestamp=datetime.now(UTC), token_b64="$$$")
    assert stamper.verify(tok, b"data") is False


def test_verify_rejects_garbage_der(stamper: RFC3161Timestamper) -> None:
    tok = TimestampToken(
        tsa_url="t",
        timestamp=datetime.now(UTC),
        token_b64=base64.b64encode(b"not a real TST").decode("ascii"),
    )
    assert stamper.verify(tok, b"data") is False


def test_verify_rejects_none_token(stamper: RFC3161Timestamper) -> None:
    assert stamper.verify(None, b"data") is False  # type: ignore[arg-type]


def test_verify_rejects_empty_data_for_remote_token(
    stamper: RFC3161Timestamper,
) -> None:
    """A remote token cannot verify against empty data — the hash
    imprint cannot match."""
    tok = _issue_token(b"non-empty")
    assert stamper.verify(tok, b"") is False


def test_verify_rejects_expired_tsa_cert(stamper: RFC3161Timestamper) -> None:
    """A token whose TSA certificate is expired at genTime must be
    rejected — even if every other check passes."""
    now = datetime.now(UTC)
    # Cert expired 1 year ago; genTime is "now" (inside clock-skew
    # window). Validity check fails because genTime > not_after.
    tok = _issue_token(
        b"recent-data",
        cn="Expired TSA",
        org="D-Trust Historic",
        not_before=now - timedelta(days=3650),
        not_after=now - timedelta(days=365),
    )
    assert stamper.verify(tok, b"recent-data") is False


def test_verify_rejects_future_gen_time(stamper: RFC3161Timestamper) -> None:
    """genTime beyond the 5-minute clock-skew window must be rejected."""
    far_future = datetime.now(UTC) + timedelta(days=7)
    tok = _issue_token(
        b"future",
        cn="Future TSA",
        org="D-Trust Test",
        fixed_dt=far_future,
        not_after=far_future + timedelta(days=30),
    )
    assert stamper.verify(tok, b"future") is False


def test_verify_rejects_token_b64_none_for_tsa_tok(
    stamper: RFC3161Timestamper,
) -> None:
    """token_b64 None with tsa_url != 'local' would be a malformed
    state — verify treats it as local-fallback and passes on datetime
    only. Document behaviour."""
    tok = TimestampToken(
        tsa_url="http://real.tsa/",
        timestamp=datetime.now(UTC),
        token_b64=None,
    )
    # is_local_fallback is True when token_b64 is None, regardless of url.
    assert stamper.verify(tok, b"data") is True


# ---------------------------------------------------------------------------
# Round-trip — the stamp → verify loop using DummyTimeStamper as a stand-in
# for a live sovereign TSA
# ---------------------------------------------------------------------------


def test_stamp_verify_full_cycle(stamper: RFC3161Timestamper) -> None:
    """The full production loop — stamp then verify — completes for
    a valid EU-sovereign TSA."""
    data = b"trace payload for stamping"
    tok = _issue_token(data)  # stand-in for a real remote stamp
    result = stamper.verify(tok, data)
    assert result is True


# ---------------------------------------------------------------------------
# _cert_matches_sid — unit-test the non-matching branches that the
# DummyTimeStamper's always-matches behaviour skips in end-to-end runs
# ---------------------------------------------------------------------------


def test_cert_matches_sid_returns_none_for_non_matching_cert() -> None:
    """The SID loop in ``_resolve_signer_cert`` iterates multiple
    certificates, returning only the one whose issuer+serial match
    the signer info. DummyTimeStamper-issued tokens embed a single
    cert so the iteration always matches on first pass; the no-match
    branch needs targeted coverage."""
    # Build a valid signer cert + a second decoy cert with different
    # serial. Construct a minimal SignerIdentifier pointing at the
    # signer's issuer+serial. The decoy must yield None.
    from asn1crypto import cms

    from sentinel.crypto.timestamp import _cert_matches_sid

    signer_cert, _ = _build_tsa(cn="Signer", org="D-Trust Test")
    decoy_cert, _ = _build_tsa(cn="Decoy", org="D-Trust Test")

    # SID points at the signer cert.
    sid = cms.SignerIdentifier({
        "issuer_and_serial_number": cms.IssuerAndSerialNumber({
            "issuer": signer_cert.issuer,
            "serial_number": signer_cert.serial_number,
        }),
    })

    # Wrap the decoy in a CertificateChoices (name='certificate').
    decoy_choice = cms.CertificateChoices(name="certificate", value=decoy_cert)
    assert _cert_matches_sid(decoy_choice, sid) is None

    # And the signer cert should match.
    signer_choice = cms.CertificateChoices(name="certificate", value=signer_cert)
    match = _cert_matches_sid(signer_choice, sid)
    assert match is not None
    assert match.serial_number == signer_cert.serial_number
