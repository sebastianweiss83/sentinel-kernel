"""Tests for sentinel.crypto.timestamp — network-free."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sentinel.crypto.timestamp import (
    NON_SOVEREIGN_TSAS,
    SOVEREIGN_TSAS,
    RFC3161Timestamper,
    TimestampToken,
)


def test_timestamper_defaults_to_eu_tsas() -> None:
    t = RFC3161Timestamper()
    assert t._tsa_urls == SOVEREIGN_TSAS


def test_timestamper_rejects_us_tsa_in_list() -> None:
    for forbidden in NON_SOVEREIGN_TSAS:
        with pytest.raises(ValueError, match="US-based TSA"):
            RFC3161Timestamper(tsa_urls=[forbidden])


def test_timestamper_falls_back_on_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every remote attempt fails → local fallback token."""
    t = RFC3161Timestamper(tsa_urls=["http://timestamp.dfn.de/"])

    def _fail(*_a: object, **_kw: object) -> None:
        return None

    monkeypatch.setattr(t, "_attempt_remote_stamp", _fail)
    token = t.stamp(b"data")
    assert token.is_local_fallback is True
    assert token.tsa_url == "local"
    assert t.verify(token, b"data") is True


def test_timestamper_airgap_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    monkeypatch.setattr(
        socket.socket,
        "connect",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("net")),
    )
    t = RFC3161Timestamper()
    token = t.stamp(b"x")
    assert token.is_local_fallback
    assert t.verify(token, b"x")


def test_verify_rejects_none_and_bad_tokens() -> None:
    """v3.4.1: verify performs full RFC 3161 CMS verification; any
    token that isn't a properly signed TSA-issued TimeStampToken is
    rejected — even if the base64 happens to decode to valid bytes.
    Positive verification cases are covered in test_rfc3161_verify.py.
    """
    t = RFC3161Timestamper()
    assert t.verify(None, b"x") is False  # type: ignore[arg-type]

    # Arbitrary bytes that happen to be valid base64 are not a CMS
    # structure. Pre-v3.4.1 the stub returned True here — that was
    # the overclaim the audit caught.
    arbitrary = TimestampToken(
        tsa_url="http://timestamp.dfn.de/",
        timestamp=datetime.now(UTC),
        token_b64="aGVsbG8=",  # base64 of b"hello"
    )
    assert t.verify(arbitrary, b"x") is False

    bad_b64 = TimestampToken(
        tsa_url="http://timestamp.dfn.de/",
        timestamp=datetime.now(UTC),
        token_b64="!!not base64!!",
    )
    assert t.verify(bad_b64, b"x") is False

    missing_payload = TimestampToken(
        tsa_url="http://timestamp.dfn.de/",
        timestamp=datetime.now(UTC),
        token_b64="",
    )
    assert t.verify(missing_payload, b"x") is False


def test_stamp_returns_successful_remote_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the first TSA succeeds, the token is returned unchanged."""
    t = RFC3161Timestamper()
    expected = TimestampToken(
        tsa_url="http://timestamp.dfn.de/",
        timestamp=datetime.now(UTC),
        token_b64="aGVsbG8=",
    )

    calls = {"count": 0}

    def _stamp(_url: str, _data: bytes) -> TimestampToken:
        calls["count"] += 1
        return expected

    monkeypatch.setattr(t, "_attempt_remote_stamp", _stamp)
    result = t.stamp(b"payload")
    assert result is expected
    assert calls["count"] == 1


def test_timestamp_token_to_dict() -> None:
    token = TimestampToken(
        tsa_url="http://timestamp.dfn.de/",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        token_b64="aGVsbG8=",
    )
    d = token.to_dict()
    assert d["tsa_url"] == "http://timestamp.dfn.de/"
    assert d["is_local_fallback"] is False
