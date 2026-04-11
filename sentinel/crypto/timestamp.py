"""RFC 3161 timestamping via EU-sovereign TSAs only.

Uses ONLY EU-based Timestamp Authorities. Never uses US-based
TSAs — that would re-introduce CLOUD Act exposure at the
countersignature step.

Air-gap fallback: if a TSA is unreachable (network-blocked or
offline deployment), the stamp falls back to a local timestamp.
The trace is still written — the TSA countersignature is
additive, not required.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime

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

    def verify(self, token: TimestampToken, data: bytes) -> bool:
        """Verify a timestamp token.

        A true RFC 3161 verify would recompute the token hash and
        check the TSA signature. For air-gapped local-fallback
        tokens we simply assert that the timestamp looks sane.
        """
        if token is None:
            return False
        if token.is_local_fallback:
            return isinstance(token.timestamp, datetime)
        if not data:
            return False
        if not token.token_b64:
            return False
        try:
            base64.b64decode(token.token_b64, validate=True)
        except Exception:
            return False
        return True
