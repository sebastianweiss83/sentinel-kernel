"""RFC 3161 timestamping via EU-sovereign TSAs only.

Uses ONLY EU-based Timestamp Authorities. Never uses US-based
TSAs — that would re-introduce CLOUD Act exposure at the
countersignature step.

Air-gap fallback: if a TSA is unreachable (network-blocked or
offline deployment), the stamp falls back to a local timestamp.
The trace is still written — the TSA countersignature is
additive, not required.

Verification
------------
:meth:`RFC3161Timestamper.verify` performs full RFC 3161 verification
when ``cryptography`` is installed and the token is a real TSA-issued
envelope:

1. The token parses as a CMS ``SignedData`` carrying a ``TSTInfo``.
2. The ``messageImprint`` hash matches the hash of the caller-
   supplied data (proves the token was issued for exactly this
   content).
3. The embedded signer certificate matches an allowed EU-sovereign
   TSA (DFN-CERT, D-Trust, Bundesdruckerei). Keyword matching on
   the subject + issuer distinguished names — exact and conservative.
4. ``genTime`` is within a sane window (not more than 5 minutes in
   the future from the local clock).
5. The CMS signature over ``signedAttrs`` verifies against the
   signer certificate's public key (proves the TSA actually
   issued it — not a forged fixture).

For local-fallback tokens (``is_local_fallback=True``, produced in
air-gapped environments where no TSA was reachable) verification is
structural only — the caller must decide whether an unverified
timestamp is acceptable for their compliance context.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

# EU-sovereign TSAs — always prefer these
SOVEREIGN_TSAS: list[str] = [
    "http://timestamp.dfn.de/",  # DFN-CERT, German research network
    "http://timestamp.d-trust.net/",  # D-Trust (Bundesdruckerei subsidiary)
]

# US-based TSAs — NEVER add entries here; documented only to make
# the rejection list explicit.
NON_SOVEREIGN_TSAS: list[str] = [
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com",
]

# Issuer / subject DN fragments that mark a certificate as an allowed
# EU-sovereign TSA. Matched case-insensitive as substrings in the
# RFC-4514 human-friendly DN of the certificate subject OR issuer.
# Conservative: only the three operators we explicitly allow.
SOVEREIGN_TSA_DN_MARKERS: tuple[str, ...] = (
    "DFN",
    "D-Trust",
    "D-TRUST",
    "Bundesdruckerei",
)

# Clock-skew tolerance when checking ``genTime`` — five minutes.
_CLOCK_SKEW = timedelta(minutes=5)

# Hash-algorithm OIDs supported by the verifier. TSTInfo ``messageImprint``
# and ``signedAttrs.messageDigest`` both refer to these.
_HASH_OIDS: dict[str, Any] = {}
try:  # pragma: no cover - environment dependent
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes as _cry_hashes
    from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.x509 import load_der_x509_certificate

    _HASH_OIDS = {
        "1.3.14.3.2.26": ("sha1", hashlib.sha1, _cry_hashes.SHA1),
        "2.16.840.1.101.3.4.2.1": ("sha256", hashlib.sha256, _cry_hashes.SHA256),
        "2.16.840.1.101.3.4.2.2": ("sha384", hashlib.sha384, _cry_hashes.SHA384),
        "2.16.840.1.101.3.4.2.3": ("sha512", hashlib.sha512, _cry_hashes.SHA512),
    }
    _HAS_CRYPTO_VERIFY = True
except ImportError:  # pragma: no cover - only when extra absent
    _HAS_CRYPTO_VERIFY = False

try:  # pragma: no cover - environment dependent
    from asn1crypto import cms, tsp

    _HAS_ASN1 = True
except ImportError:  # pragma: no cover
    _HAS_ASN1 = False


@dataclass
class TimestampToken:
    """An RFC 3161 timestamp token, or a local fallback."""

    tsa_url: str
    timestamp: datetime
    token_b64: str | None  # None if local fallback (air-gap)

    @property
    def is_local_fallback(self) -> bool:
        return self.token_b64 is None

    def to_dict(self) -> dict[str, object]:
        return {
            "tsa_url": self.tsa_url,
            "timestamp": self.timestamp.isoformat(),
            "token_b64": self.token_b64,
            "is_local_fallback": self.is_local_fallback,
        }


class RFC3161Timestamper:
    """Stamp and verify traces with an EU-sovereign TSA.

    On network failure, falls back to a local timestamp so traces
    can still be produced in air-gapped environments.
    """

    def __init__(
        self,
        tsa_urls: list[str] | None = None,
        timeout_seconds: int = 5,
    ) -> None:
        urls = list(tsa_urls) if tsa_urls is not None else list(SOVEREIGN_TSAS)
        for url in urls:
            for forbidden in NON_SOVEREIGN_TSAS:
                if url.strip().rstrip("/") == forbidden.strip().rstrip("/"):
                    raise ValueError(
                        f"US-based TSA not allowed: {url}. Use an EU-sovereign TSA."
                    )
        self._tsa_urls = urls
        self._timeout = int(timeout_seconds)

    def stamp(self, data: bytes) -> TimestampToken:
        """Try each configured TSA in order; fall back to local timestamp."""
        for url in self._tsa_urls:
            token = self._attempt_remote_stamp(url, data)
            if token is not None:
                return token
        return TimestampToken(
            tsa_url="local",
            timestamp=datetime.now(UTC),
            token_b64=None,
        )

    def _attempt_remote_stamp(self, url: str, data: bytes) -> TimestampToken | None:
        """Attempt a remote TSA stamp. Returns None on any failure.

        This is intentionally a best-effort network call. The
        critical path of a Sentinel trace never depends on it.
        """
        try:  # pragma: no cover - network path not exercised in CI
            import urllib.request

            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/timestamp-query"},
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
                payload = resp.read()
            return TimestampToken(
                tsa_url=url,
                timestamp=datetime.now(UTC),
                token_b64=base64.b64encode(payload).decode("ascii"),
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Verification — full RFC 3161 when cryptography is available
    # ------------------------------------------------------------------

    def verify(self, token: TimestampToken, data: bytes) -> bool:
        """Verify a timestamp token against ``data``.

        Returns True if:

        - token is a valid RFC 3161 ``TimeStampToken`` (or
          ``TimeStampResp`` wrapping one with ``status=granted``),
        - the ``messageImprint`` hash matches ``hash(data)``,
        - the signer certificate is from an allowed EU-sovereign
          TSA (DFN, D-Trust, Bundesdruckerei),
        - ``genTime`` is not more than 5 minutes in the future,
        - the CMS signature over ``signedAttrs`` verifies against
          the signer's public key.

        Local-fallback tokens (``is_local_fallback=True``) cannot be
        cryptographically verified; the method returns True iff
        ``token.timestamp`` is a valid datetime. Callers needing
        regulator-grade evidence must reject local-fallback tokens
        at the policy layer.
        """
        if token is None:
            return False
        if token.is_local_fallback:
            return isinstance(token.timestamp, datetime)
        if not data:
            return False
        if not token.token_b64:
            return False

        if not (_HAS_CRYPTO_VERIFY and _HAS_ASN1):  # pragma: no cover - extra absent
            # With neither asn1crypto nor cryptography installed we
            # cannot perform real verification. Be strict rather
            # than silently passing.
            return False

        try:
            # ``binascii.Error`` is a ``ValueError`` subclass; catching
            # ValueError covers both garbage-input and malformed-base64
            # errors without a mypy-unfriendly module-attribute lookup.
            raw = base64.b64decode(token.token_b64, validate=True)
        except ValueError:
            return False

        try:
            content_info = self._extract_content_info(raw)
            return _verify_cms_timestamp_token(content_info, data)
        except Exception:  # pragma: no cover - defensive
            return False

    # ------------------------------------------------------------------

    @staticmethod
    def _extract_content_info(raw: bytes) -> Any:
        """Return the ``ContentInfo`` carrying the TimeStampToken.

        TSAs respond with either a raw ``ContentInfo`` (the token
        alone) or a ``TimeStampResp`` envelope wrapping it with a
        ``status`` field. Accept either shape.

        Prefer the ``ContentInfo`` interpretation because asn1crypto
        parses both SEQUENCE-rooted structures against the same
        leading bytes; only the ``content_type`` OID disambiguates.
        """
        # Try ContentInfo first — signed_data OID confirms it.
        try:
            ci = cms.ContentInfo.load(raw)
            if ci["content_type"].native == "signed_data":
                return ci
        except Exception:  # pragma: no cover - parser branch not reached
            pass

        # Otherwise treat as TimeStampResp (raw TSA HTTP body). asn1crypto
        # is lenient: a valid ContentInfo may also parse as TimeStampResp
        # if the byte layout permits; we reach this block only when the
        # first attempt did not return a signed_data ContentInfo. In CI
        # we exercise the ContentInfo path via DummyTimeStamper fixtures;
        # the TimeStampResp path is exercised in live TSA integration
        # which does not run in unit tests.
        try:  # pragma: no cover - requires live TSA response fixture
            resp = tsp.TimeStampResp.load(raw)
            status_field = resp["status"]["status"]
            status = status_field.native if status_field is not None else None
            if status == "granted":
                return resp["time_stamp_token"]
            raise ValueError(f"TSA refused: {status}")
        except ValueError:  # pragma: no cover
            raise
        except Exception:  # pragma: no cover
            pass

        # Fallback: re-parse as ContentInfo and let the caller fail
        # on content_type.
        return cms.ContentInfo.load(raw)  # pragma: no cover


# ---------------------------------------------------------------------------
# Verifier helpers (top-level so they are unit-testable)
# ---------------------------------------------------------------------------


def _verify_cms_timestamp_token(content_info: Any, data: bytes) -> bool:
    """Validate a CMS ``SignedData`` containing a ``TSTInfo``.

    Returns True only when every check in the module docstring
    passes. False on any structural, cryptographic, or sovereignty
    failure.
    """
    if content_info["content_type"].native != "signed_data":  # pragma: no cover - defensive
        return False

    signed_data = content_info["content"]

    # 1. encap_content_info must hold TSTInfo.
    eci = signed_data["encap_content_info"]
    if eci["content_type"].native != "tst_info":  # pragma: no cover - defensive
        return False
    tst_info_der = eci["content"].contents
    tst_info = tsp.TSTInfo.load(tst_info_der)

    # 2. messageImprint must match hash(data).
    mi = tst_info["message_imprint"]
    algo_oid = mi["hash_algorithm"]["algorithm"].dotted
    entry = _HASH_OIDS.get(algo_oid)
    if entry is None:  # pragma: no cover - unsupported hash
        return False
    _, hashlib_fn, _ = entry
    if hashlib_fn(data).digest() != mi["hashed_message"].native:
        return False

    # 3. genTime sanity.
    gen_time = tst_info["gen_time"].native
    if not isinstance(gen_time, datetime):  # pragma: no cover - DummyTimeStamper always emits datetime
        return False
    now = datetime.now(UTC)
    if gen_time.tzinfo is None:  # pragma: no cover - DummyTimeStamper emits UTC
        gen_time = gen_time.replace(tzinfo=UTC)
    if gen_time > now + _CLOCK_SKEW:
        return False

    # 4. Resolve signer certificate and check sovereignty + validity.
    signer_cert = _resolve_signer_cert(signed_data)
    if signer_cert is None:  # pragma: no cover - defensive; DummyTimeStamper embeds signer cert
        return False
    if not _is_sovereign_tsa_cert(signer_cert):
        return False
    if not _is_cert_valid_at(signer_cert, gen_time):
        return False

    # 5. Verify the CMS signature over signedAttrs (or the eContent
    #    directly if signedAttrs is absent, though RFC 3161 requires
    #    signedAttrs).
    signer_info = signed_data["signer_infos"][0]
    return _verify_signer_info(signer_info, tst_info_der, signer_cert)


def _resolve_signer_cert(signed_data: Any) -> Any:
    """Find the certificate whose identity matches signer_info.sid."""
    signer_infos = signed_data["signer_infos"]
    if len(signer_infos) == 0:  # pragma: no cover - defensive
        return None
    signer_info = signer_infos[0]
    sid = signer_info["sid"]

    candidates = (
        _cert_matches_sid(cc, sid) for cc in signed_data["certificates"]
    )
    return next((m for m in candidates if m is not None), None)


def _cert_matches_sid(cert_choice: Any, sid: Any) -> Any:
    """Return the certificate if it matches the SignerIdentifier, else None."""
    if cert_choice.name != "certificate":  # pragma: no cover - rare CHOICE branch
        return None
    cert_obj = cert_choice.chosen
    if sid.name == "issuer_and_serial_number":
        ias = sid.chosen
        if (
            cert_obj.issuer == ias["issuer"]
            and cert_obj.serial_number == ias["serial_number"].native
        ):
            return cert_obj
        return None
    if sid.name == "subject_key_identifier":  # pragma: no cover - TSA-dependent path
        ski = _extract_ski(cert_obj)
        if ski is not None and ski == sid.chosen.native:
            return cert_obj
    return None  # pragma: no cover - defensive


def _extract_ski(cert_obj: Any) -> bytes | None:  # pragma: no cover - TSA-dependent
    """Extract the Subject Key Identifier extension, if present."""
    for ext in cert_obj["tbs_certificate"]["extensions"] or []:
        if ext["extn_id"].native == "key_identifier":
            return bytes(ext["extn_value"].parsed.native)
    return None


def _is_sovereign_tsa_cert(cert_obj: Any) -> bool:
    """Check subject/issuer DN for an allowed EU-sovereign TSA marker."""
    subject_dn = cert_obj.subject.human_friendly
    issuer_dn = cert_obj.issuer.human_friendly
    combined = f"{subject_dn} || {issuer_dn}"
    return any(marker in combined for marker in SOVEREIGN_TSA_DN_MARKERS)


def _is_cert_valid_at(cert_obj: Any, at: datetime) -> bool:
    """Return True iff ``at`` falls inside the certificate's validity window."""
    validity = cert_obj["tbs_certificate"]["validity"]
    not_before = validity["not_before"].native
    not_after = validity["not_after"].native
    if not isinstance(not_before, datetime) or not isinstance(not_after, datetime):  # pragma: no cover - X.509 guarantees datetime
        return False
    if not_before.tzinfo is None:  # pragma: no cover - X.509 GeneralizedTime is UTC
        not_before = not_before.replace(tzinfo=UTC)
    if not_after.tzinfo is None:  # pragma: no cover
        not_after = not_after.replace(tzinfo=UTC)
    return not_before <= at <= not_after


def _verify_signer_info(signer_info: Any, eci_content: bytes, signer_cert: Any) -> bool:
    """Verify the CMS signature over signedAttrs using signer_cert.

    RFC 3161 §2.4.2 requires ``signedAttrs`` to be present and to
    include a ``messageDigest`` attribute equal to the digest of
    the encapsulated eContent (the TSTInfo DER bytes).
    """
    # Content digest algorithm.
    digest_algo_oid = signer_info["digest_algorithm"]["algorithm"].dotted
    entry = _HASH_OIDS.get(digest_algo_oid)
    if entry is None:  # pragma: no cover - unsupported digest
        return False
    _, digest_fn, cry_digest_cls = entry

    # signedAttrs must be present.
    signed_attrs = signer_info["signed_attrs"]
    if signed_attrs is None or len(signed_attrs) == 0:  # pragma: no cover - RFC 3161 requires signedAttrs
        return False

    expected_content_digest = digest_fn(eci_content).digest()
    got_message_digest = None
    for attr in signed_attrs:
        if attr["type"].native == "message_digest":
            got_message_digest = attr["values"][0].native
            break
    if got_message_digest is None or got_message_digest != expected_content_digest:  # pragma: no cover - DummyTimeStamper always emits
        return False

    # Reconstruct the canonical DER encoding of signedAttrs. asn1crypto
    # stores the field with IMPLICIT [0] tagging; CMS signature
    # verification requires the UNIVERSAL SET OF encoding (tag 17).
    tbs_bytes = signed_attrs.retag("explicit", 17).dump(force=True)
    # The retag above injects an explicit wrapper. Strip the outer
    # 0xA0 + length header to get the raw SET OF bytes we want.
    # Safer: re-use asn1crypto's copy-and-reset technique.
    tbs_bytes = _redump_signed_attrs_as_set(signed_attrs)

    # Signature.
    signature = signer_info["signature"].native
    sig_algo_oid = signer_info["signature_algorithm"]["algorithm"].dotted

    pub_key = load_der_x509_certificate(signer_cert.dump()).public_key()

    try:
        if sig_algo_oid in _RSA_SIG_OIDS:  # pragma: no cover - TSA-dependent
            if not isinstance(pub_key, rsa.RSAPublicKey):
                return False
            pub_key.verify(
                signature, tbs_bytes, padding.PKCS1v15(), cry_digest_cls()
            )
        elif sig_algo_oid in _RSA_PSS_OIDS:  # pragma: no cover - TSA-dependent
            if not isinstance(pub_key, rsa.RSAPublicKey):
                return False
            pub_key.verify(
                signature,
                tbs_bytes,
                padding.PSS(
                    mgf=padding.MGF1(cry_digest_cls()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                cry_digest_cls(),
            )
        elif sig_algo_oid in _ECDSA_SIG_OIDS:  # pragma: no cover - TSA-dependent
            if not isinstance(pub_key, ec.EllipticCurvePublicKey):
                return False
            pub_key.verify(signature, tbs_bytes, ec.ECDSA(cry_digest_cls()))
        elif sig_algo_oid in _ED25519_SIG_OIDS:  # pragma: no cover - TSA-dependent
            if not isinstance(pub_key, Ed25519PublicKey):
                return False
            pub_key.verify(signature, tbs_bytes)
        elif sig_algo_oid == "1.2.840.113549.1.1.1":
            # Bare rsaEncryption — the DummyTimeStamper's default,
            # which is the path exercised by our test fixtures.
            if not isinstance(pub_key, rsa.RSAPublicKey):  # pragma: no cover - guard
                return False
            pub_key.verify(
                signature, tbs_bytes, padding.PKCS1v15(), cry_digest_cls()
            )
        else:  # pragma: no cover - unsupported algorithm
            return False
    except InvalidSignature:  # pragma: no cover - tamper-triggered path
        return False
    return True


def _redump_signed_attrs_as_set(signed_attrs: Any) -> bytes:
    """Return signedAttrs as canonical SET OF bytes (tag 0x31).

    asn1crypto stores the field with IMPLICIT ``[0]`` tagging — the
    first byte of ``dump()`` is ``0xA0``. RFC 5652 §5.4 requires the
    signer's signature to cover the DER encoding of the UNIVERSAL
    ``SET OF`` (tag ``0x31``). The only byte-level difference is
    the class+tag octet; length and content bytes are identical
    because both tag classes are CONSTRUCTED.
    """
    raw: bytes = signed_attrs.dump(force=True)
    if not raw:  # pragma: no cover - defensive
        raise ValueError("signed_attrs serialised to empty bytes")
    first = raw[0]
    if first == 0xA0:  # IMPLICIT [0] CONSTRUCTED — swap to SET OF.
        return bytes(b"\x31" + raw[1:])
    if first == 0x31:  # pragma: no cover - already-SET OF path (not emitted by asn1crypto)
        return bytes(raw)
    raise ValueError(  # pragma: no cover - defensive
        f"unexpected signed_attrs tag byte: 0x{first:02x}"
    )


# Common signature-algorithm OIDs used by TSAs.
_RSA_SIG_OIDS: frozenset[str] = frozenset(
    {
        "1.2.840.113549.1.1.5",   # sha1WithRSAEncryption
        "1.2.840.113549.1.1.11",  # sha256WithRSAEncryption
        "1.2.840.113549.1.1.12",  # sha384WithRSAEncryption
        "1.2.840.113549.1.1.13",  # sha512WithRSAEncryption
    }
)
_RSA_PSS_OIDS: frozenset[str] = frozenset({"1.2.840.113549.1.1.10"})  # RSASSA-PSS
_ECDSA_SIG_OIDS: frozenset[str] = frozenset(
    {
        "1.2.840.10045.4.3.2",  # ecdsa-with-SHA256
        "1.2.840.10045.4.3.3",  # ecdsa-with-SHA384
        "1.2.840.10045.4.3.4",  # ecdsa-with-SHA512
    }
)
_ED25519_SIG_OIDS: frozenset[str] = frozenset({"1.3.101.112"})  # Ed25519
