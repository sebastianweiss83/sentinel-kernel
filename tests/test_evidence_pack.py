"""
tests/test_evidence_pack.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Covers ``sentinel.compliance.evidence_pack`` and the
``sentinel evidence-pack`` CLI.

Strategy:
    - Pure-function unit tests for ``_iter_traces_in_window``,
      ``_build_executive_summary``, ``_hash_manifest_digest``.
    - Happy-path PDF render tests that verify the file is a real PDF
      (magic header) with non-zero size.
    - Optional DORA/NIS2/manifesto branches.
    - Import-guard test that simulates reportlab missing, using the
      established pattern from ``test_crypto_signing``.
    - CLI integration tests (text output, error paths, bad dates).
"""

from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel import Sentinel, cli
from sentinel.compliance.evidence_pack import (
    EvidencePackOptions,
    _build_executive_summary,
    _esc,
    _hash_manifest_digest,
    _iter_traces_in_window,
    render_evidence_pdf,
)
from sentinel.core.trace import (
    DecisionTrace,
    HumanOverride,
    PolicyEvaluation,
    PolicyResult,
)
from sentinel.storage import SQLiteStorage

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_sentinel() -> Sentinel:
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="test-ep",
    )


def _make_trace(
    *,
    agent: str = "agent-a",
    policy_result: PolicyResult | None = PolicyResult.ALLOW,
    policy_id: str = "policies/p1.py",
    started_at: datetime | None = None,
    has_override: bool = False,
) -> DecisionTrace:
    started = started_at or datetime.now(UTC)
    pe = None
    if policy_result is not None:
        pe = PolicyEvaluation(
            policy_id=policy_id,
            policy_version="1.0.0",
            result=policy_result,
        )
    trace = DecisionTrace(
        project="test-ep",
        agent=agent,
        started_at=started,
        inputs={"x": 1},
        output={"ok": True},
        policy_evaluation=pe,
    )
    trace.complete(output={"ok": True}, latency_ms=5)
    if has_override:
        trace.add_override(
            HumanOverride(
                approver_id="alice",
                approver_role="operator",
                justification="approved",
            )
        )
    return trace


def _seed(sentinel: Sentinel, traces: list[DecisionTrace]) -> None:
    for t in traces:
        sentinel.storage.save(t)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_build_executive_summary_mixed() -> None:
    # Note: Sentinel's add_override rewrites policy_evaluation.result to
    # EXCEPTION, so an overridden ALLOW counts as EXCEPTION in the
    # summary. This is Sentinel's domain model.
    traces = [
        _make_trace(agent="a1", policy_result=PolicyResult.ALLOW),
        _make_trace(agent="a1", policy_result=PolicyResult.DENY, policy_id="p2"),
        _make_trace(agent="a2", policy_result=PolicyResult.EXCEPTION, policy_id="p3"),
        _make_trace(agent="a2", policy_result=PolicyResult.ALLOW, has_override=True),
        _make_trace(agent="a2", policy_result=None),
    ]
    s = _build_executive_summary(traces, truncated=False)
    assert s.trace_count == 5
    assert s.allow_count == 1
    assert s.deny_count == 1
    assert s.exception_count == 2
    assert s.override_count == 1
    assert s.unique_agents == 2
    assert s.unique_policies == 3
    assert s.truncated is False


def test_build_executive_summary_empty() -> None:
    s = _build_executive_summary([], truncated=False)
    assert s.trace_count == 0
    assert s.allow_count == 0
    assert s.unique_agents == 0
    assert s.unique_policies == 0


def test_build_executive_summary_truncated_flag() -> None:
    s = _build_executive_summary([], truncated=True)
    assert s.truncated is True


def test_build_executive_summary_not_evaluated_and_empty_policy() -> None:
    # PolicyResult.NOT_EVALUATED hits the non-ALLOW/DENY/EXCEPTION branch
    # and an empty policy_id hits the false branch of the policy_id guard.
    t1 = _make_trace(policy_result=PolicyResult.NOT_EVALUATED, policy_id="")
    s = _build_executive_summary([t1], truncated=False)
    assert s.allow_count == 0
    assert s.deny_count == 0
    assert s.exception_count == 0
    assert s.unique_policies == 0


def test_hash_manifest_digest_deterministic() -> None:
    a = _hash_manifest_digest(["abc", "def"])
    b = _hash_manifest_digest(["abc", "def"])
    c = _hash_manifest_digest(["abc", "xyz"])
    assert a == b
    assert a != c
    assert len(a) == 64  # SHA-256 hex


def test_hash_manifest_digest_empty() -> None:
    h = _hash_manifest_digest([])
    assert len(h) == 64


def test_esc_handles_non_strings() -> None:
    assert _esc(42) == "42"
    assert _esc("<b>hi</b>") == "&lt;b&gt;hi&lt;/b&gt;"


# ---------------------------------------------------------------------------
# Window filter
# ---------------------------------------------------------------------------


def test_iter_traces_in_window_applies_since_until() -> None:
    sentinel = _make_sentinel()
    base = datetime(2026, 1, 1, tzinfo=UTC)
    _seed(
        sentinel,
        [
            _make_trace(started_at=base + timedelta(days=i)) for i in range(5)
        ],
    )
    options = EvidencePackOptions(
        since=base + timedelta(days=1),
        until=base + timedelta(days=4),
    )
    yielded = list(_iter_traces_in_window(sentinel, options))
    # Days 1, 2, 3 (until is exclusive)
    assert len(yielded) == 3


def test_iter_traces_in_window_no_filter() -> None:
    sentinel = _make_sentinel()
    base = datetime(2026, 1, 1, tzinfo=UTC)
    _seed(
        sentinel,
        [_make_trace(started_at=base + timedelta(days=i)) for i in range(3)],
    )
    options = EvidencePackOptions()
    yielded = list(_iter_traces_in_window(sentinel, options))
    assert len(yielded) == 3


def test_iter_traces_in_window_respects_max_traces() -> None:
    sentinel = _make_sentinel()
    base = datetime(2026, 1, 1, tzinfo=UTC)
    _seed(
        sentinel,
        [_make_trace(started_at=base + timedelta(minutes=i)) for i in range(7)],
    )
    options = EvidencePackOptions(max_traces=3)
    yielded = list(_iter_traces_in_window(sentinel, options))
    assert len(yielded) == 3


def test_iter_traces_in_window_empty_store() -> None:
    sentinel = _make_sentinel()
    options = EvidencePackOptions()
    assert list(_iter_traces_in_window(sentinel, options)) == []


def test_iter_traces_in_window_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the ``offset += page_size`` multi-page branch."""
    from sentinel.compliance import evidence_pack as ep_module

    monkeypatch.setattr(ep_module, "_PAGE_SIZE", 1)
    sentinel = _make_sentinel()
    base = datetime(2026, 1, 1, tzinfo=UTC)
    _seed(
        sentinel,
        [_make_trace(started_at=base + timedelta(minutes=i)) for i in range(3)],
    )
    yielded = list(_iter_traces_in_window(sentinel, EvidencePackOptions()))
    assert len(yielded) == 3


# ---------------------------------------------------------------------------
# PDF render happy path
# ---------------------------------------------------------------------------


def _assert_is_pdf(path: Path) -> None:
    assert path.exists()
    data = path.read_bytes()
    assert data.startswith(b"%PDF-")
    assert len(data) > 500


def test_render_pdf_with_traces(tmp_path: Path) -> None:
    sentinel = _make_sentinel()
    _seed(
        sentinel,
        [
            _make_trace(agent=f"a{i}", policy_result=PolicyResult.ALLOW)
            for i in range(3)
        ],
    )
    out = tmp_path / "pack.pdf"
    path = render_evidence_pdf(
        sentinel=sentinel,
        options=EvidencePackOptions(),
        output=out,
    )
    assert path == out
    _assert_is_pdf(out)


def test_render_pdf_empty_window(tmp_path: Path) -> None:
    sentinel = _make_sentinel()
    out = tmp_path / "empty.pdf"
    render_evidence_pdf(
        sentinel=sentinel,
        options=EvidencePackOptions(),
        output=out,
    )
    _assert_is_pdf(out)


def test_render_pdf_many_traces_truncates_display(tmp_path: Path) -> None:
    sentinel = _make_sentinel()
    # More than 200 to exercise the hash-manifest truncation branch
    # and more than 10 to exercise the "tail" trace-samples branch.
    base = datetime(2026, 1, 1, tzinfo=UTC)
    _seed(
        sentinel,
        [
            _make_trace(
                agent=f"a{i % 3}",
                policy_result=PolicyResult.ALLOW,
                started_at=base + timedelta(minutes=i),
            )
            for i in range(205)
        ],
    )
    out = tmp_path / "big.pdf"
    render_evidence_pdf(
        sentinel=sentinel,
        options=EvidencePackOptions(),
        output=out,
    )
    _assert_is_pdf(out)


def test_render_pdf_with_dora_and_nis2(tmp_path: Path) -> None:
    sentinel = _make_sentinel()
    _seed(sentinel, [_make_trace()])
    out = tmp_path / "full.pdf"
    render_evidence_pdf(
        sentinel=sentinel,
        options=EvidencePackOptions(
            financial_sector=True,
            critical_infrastructure=True,
            since=datetime(2026, 1, 1, tzinfo=UTC),
            until=datetime(2027, 1, 1, tzinfo=UTC),
        ),
        output=out,
    )
    _assert_is_pdf(out)


def test_render_pdf_with_manifesto(tmp_path: Path) -> None:
    from sentinel.manifesto import (
        AcknowledgedGap,
        EUOnly,
        OnPremiseOnly,
        Required,
        SentinelManifesto,
        ZeroExposure,
    )

    class _MyManifesto(SentinelManifesto):
        jurisdiction = EUOnly()
        kill_switch = Required()
        airgap = Required()
        cloud_act = ZeroExposure()
        storage = OnPremiseOnly(country="EU")
        ci_cd = AcknowledgedGap(
            provider="GitHub (Microsoft)",
            migrating_to="Self-hosted Forgejo",
            by="2027-Q2",
            reason="no production-ready EU alternative yet",
        )

    sentinel = _make_sentinel()
    _seed(sentinel, [_make_trace()])
    out = tmp_path / "mani.pdf"
    render_evidence_pdf(
        sentinel=sentinel,
        options=EvidencePackOptions(),
        output=out,
        manifesto=_MyManifesto(),
    )
    _assert_is_pdf(out)


def test_render_pdf_head_tail_overlap_dedup(tmp_path: Path) -> None:
    """Seed 15 traces so head[:10] and tail[-10:] overlap, exercising
    the ``if t.trace_id in seen: continue`` dedup branch."""
    sentinel = _make_sentinel()
    base = datetime(2026, 1, 1, tzinfo=UTC)
    _seed(
        sentinel,
        [
            _make_trace(
                agent=f"a{i}",
                policy_result=PolicyResult.ALLOW,
                started_at=base + timedelta(minutes=i),
            )
            for i in range(15)
        ],
    )
    out = tmp_path / "dedup.pdf"
    render_evidence_pdf(
        sentinel=sentinel,
        options=EvidencePackOptions(),
        output=out,
    )
    _assert_is_pdf(out)


def test_render_pdf_trace_without_policy_evaluation(tmp_path: Path) -> None:
    """Cover the ``result = '—'`` fallback when a trace has no policy."""
    sentinel = _make_sentinel()
    _seed(sentinel, [_make_trace(policy_result=None)])
    out = tmp_path / "nopolicy.pdf"
    render_evidence_pdf(
        sentinel=sentinel,
        options=EvidencePackOptions(),
        output=out,
    )
    _assert_is_pdf(out)


def test_render_pdf_with_critical_path_violation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover the sovereignty-scan violation branch in the PDF."""
    from sentinel.compliance import evidence_pack as ep_module
    from sentinel.scanner.runtime import RuntimeScanner, ScanResult

    def fake_scan(self: RuntimeScanner) -> ScanResult:
        return ScanResult(
            packages=[],
            critical_path_violations=["boto3 (Amazon, US)"],
        )

    monkeypatch.setattr(ep_module.RuntimeScanner, "scan", fake_scan)
    sentinel = _make_sentinel()
    _seed(sentinel, [_make_trace()])
    out = tmp_path / "violation.pdf"
    render_evidence_pdf(
        sentinel=sentinel,
        options=EvidencePackOptions(),
        output=out,
    )
    _assert_is_pdf(out)


# ---------------------------------------------------------------------------
# Import-guard (simulates reportlab missing)
# ---------------------------------------------------------------------------


def test_render_pdf_import_error_when_reportlab_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    saved = sys.modules.get("reportlab")
    monkeypatch.setitem(sys.modules, "reportlab", None)
    sys.modules.pop("sentinel.compliance.evidence_pack", None)
    try:
        module = importlib.import_module("sentinel.compliance.evidence_pack")
        sentinel = _make_sentinel()
        with pytest.raises(ImportError, match=r"sentinel-kernel\[pdf\]"):
            module.render_evidence_pdf(
                sentinel=sentinel,
                options=module.EvidencePackOptions(),
                output=tmp_path / "x.pdf",
            )
    finally:
        if saved is not None:
            sys.modules["reportlab"] = saved
        sys.modules.pop("sentinel.compliance.evidence_pack", None)
        importlib.import_module("sentinel.compliance.evidence_pack")


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_evidence_pack_happy_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "cli.pdf"
    rc = cli.main(
        [
            "evidence-pack",
            "--output",
            str(out),
            "--financial-sector",
            "--critical-infrastructure",
        ]
    )
    assert rc == 0
    assert out.exists()
    assert "Wrote" in capsys.readouterr().out
    _assert_is_pdf(out)


def test_cli_evidence_pack_with_db_and_window(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "traces.db"
    sentinel = Sentinel(storage=SQLiteStorage(str(db)), project="test-ep")
    sentinel.storage.save(_make_trace())
    out = tmp_path / "win.pdf"
    rc = cli.main(
        [
            "evidence-pack",
            "--output",
            str(out),
            "--db",
            str(db),
            "--since",
            "2020-01-01T00:00:00+00:00",
            "--until",
            "2099-01-01T00:00:00+00:00",
            "--project",
            "test-ep",
            "--max-traces",
            "50",
            "--title",
            "Q1 2026 audit pack",
        ]
    )
    assert rc == 0
    assert out.exists()


def test_cli_evidence_pack_bad_since_returns_2(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    rc = cli.main(
        ["evidence-pack", "--output", str(tmp_path / "x.pdf"), "--since", "not-a-date"]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "--since" in err


def test_cli_evidence_pack_bad_until_returns_2(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    rc = cli.main(
        ["evidence-pack", "--output", str(tmp_path / "x.pdf"), "--until", "not-a-date"]
    )
    assert rc == 2


def test_cli_evidence_pack_invalid_manifesto_returns_2(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    ghost = tmp_path / "ghost.py"
    rc = cli.main(
        [
            "evidence-pack",
            "--output",
            str(tmp_path / "x.pdf"),
            "--manifesto",
            f"{ghost}:NoClass",
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "Could not resolve manifesto" in err


def test_cli_evidence_pack_with_valid_manifesto_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Cover the ``manifesto_instance = cls()`` branch in _cmd_evidence_pack."""
    manifesto_file = tmp_path / "m.py"
    manifesto_file.write_text(
        "from sentinel.manifesto import (\n"
        "    AcknowledgedGap, EUOnly, OnPremiseOnly, Required,\n"
        "    SentinelManifesto, ZeroExposure,\n"
        ")\n"
        "class MyManifesto(SentinelManifesto):\n"
        "    jurisdiction = EUOnly()\n"
        "    kill_switch = Required()\n"
        "    airgap = Required()\n"
        "    cloud_act = ZeroExposure()\n"
        "    storage = OnPremiseOnly(country='EU')\n"
        "    ci_cd = AcknowledgedGap(\n"
        "        provider='GitHub',\n"
        "        migrating_to='Forgejo',\n"
        "        by='2027',\n"
        "        reason='no EU alternative',\n"
        "    )\n",
        encoding="utf-8",
    )
    out = tmp_path / "cli-mani.pdf"
    rc = cli.main(
        [
            "evidence-pack",
            "--output",
            str(out),
            "--manifesto",
            f"{manifesto_file}:MyManifesto",
        ]
    )
    assert rc == 0
    assert out.exists()


def test_cli_evidence_pack_import_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Cover the CLI's ImportError fallback when reportlab missing."""
    from sentinel.compliance import evidence_pack as ep_module

    def _raise(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise ImportError("sentinel-kernel[pdf]")

    monkeypatch.setattr(ep_module, "render_evidence_pdf", _raise)
    rc = cli.main(["evidence-pack", "--output", str(tmp_path / "x.pdf")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "sentinel-kernel[pdf]" in err
