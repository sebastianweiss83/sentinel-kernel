"""Branch coverage tests.

Each test targets a specific uncovered branch identified by
``pytest --cov-branch``. Tests are grouped by module.
"""

from __future__ import annotations

import asyncio
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sentinel import Sentinel
from sentinel.core.trace import (
    DecisionTrace,
    HumanOverride,
)
from sentinel.storage.sqlite import SQLiteStorage

# ── euaiact.py — diff() without human_action ────────────────────

def test_euaiact_diff_gap_without_human_action() -> None:
    """Branch: euaiact.py line 107 → False (no human_action)."""
    from sentinel.compliance.euaiact import ArticleReport, ComplianceReport

    report = ComplianceReport(
        timestamp=datetime.now(UTC),
        articles={
            "Art. 99": ArticleReport(
                article="Art. 99",
                title="Test",
                status="PARTIAL",
                automated=False,
                detail="Some gap",
                human_action=None,
            ),
        },
    )
    text = report.diff()
    assert "Art. 99" in text
    assert "ACTION" not in text


# ── unified.py — as_dict/as_text with dora + nis2 ───────────────

def test_unified_report_with_dora_and_nis2() -> None:
    """Branches: unified.py lines 49-52, 57-60 True path."""
    from sentinel.compliance.dora import DoraChecker
    from sentinel.compliance.euaiact import EUAIActChecker
    from sentinel.compliance.nis2 import NIS2Checker
    from sentinel.compliance.unified import UnifiedReport

    s = Sentinel()
    report = UnifiedReport(
        timestamp=datetime.now(UTC),
        eu_ai_act=EUAIActChecker().check(s),
        dora=DoraChecker().check(s),
        nis2=NIS2Checker().check(s),
        frameworks=["eu_ai_act", "dora", "nis2"],
    )
    d = report.as_dict()
    assert "dora" in d
    assert "nis2" in d
    text = report.as_text()
    assert len(text) > 0


def test_unified_report_without_dora_and_nis2() -> None:
    """Branches: unified.py lines 51→53, 57→59 False path (None)."""
    from sentinel.compliance.euaiact import EUAIActChecker
    from sentinel.compliance.unified import UnifiedReport

    s = Sentinel()
    report = UnifiedReport(
        timestamp=datetime.now(UTC),
        eu_ai_act=EUAIActChecker().check(s),
        dora=None,
        nis2=None,
        frameworks=["eu_ai_act"],
    )
    d = report.as_dict()
    assert "dora" not in d
    assert "nis2" not in d
    text = report.as_text()
    assert len(text) > 0


# ── attestation.py — manifesto edge cases ────────────────────────

def test_attestation_manifesto_without_check_method() -> None:
    """Branch: attestation.py line 108→117 (manifesto has no .check)."""
    from sentinel.core.attestation import generate_attestation

    class FakeManifesto:
        pass

    s = Sentinel()
    att = generate_attestation(s, manifesto=FakeManifesto())
    assert "manifesto_summary" not in att or att["manifesto_summary"] is None


def test_attestation_manifesto_check_returns_none() -> None:
    """Branch: attestation.py line 108 (report is None)."""
    from sentinel.core.attestation import generate_attestation

    class FakeManifesto:
        def check(self, **kwargs: Any) -> None:
            return None

    s = Sentinel()
    att = generate_attestation(s, manifesto=FakeManifesto())
    assert "attestation_hash" in att


def test_attestation_manifesto_check_raises() -> None:
    """Branch: attestation.py line 114 (except Exception)."""
    from sentinel.core.attestation import generate_attestation

    class FakeManifesto:
        def check(self, **kwargs: Any) -> None:
            raise RuntimeError("boom")

    s = Sentinel()
    att = generate_attestation(s, manifesto=FakeManifesto())
    assert "error" in str(att.get("manifesto_summary", {}))


# ── trace.py — from_dict minimal, add_override, link_precedent ───

def test_from_dict_minimal_fields() -> None:
    """Branches: trace.py 234→237, 241→248, 248→253
    (walrus guards False — no optional sections in dict)."""
    trace = DecisionTrace.from_dict({
        "trace_id": "test-minimal",
        "inputs": {},
        "output": {},
    })
    assert trace.trace_id == "test-minimal"
    assert trace.model_provider is None
    assert trace.policy_evaluation is None
    assert trace.human_override is None


def test_from_dict_policy_without_evaluated_at() -> None:
    """Branch: trace.py 262→265 False (no evaluated_at in policy)."""
    trace = DecisionTrace.from_dict({
        "trace_id": "test-policy-no-ts",
        "policy": {
            "policy_id": "test",
            "policy_version": "1",
            "result": "ALLOW",
        },
    })
    assert trace.policy_evaluation is not None
    assert trace.policy_evaluation.policy_id == "test"


def test_from_dict_override_without_approved_at() -> None:
    """Branch: trace.py 272→275 False (no approved_at in override)."""
    trace = DecisionTrace.from_dict({
        "trace_id": "test-override-no-ts",
        "human_override": {
            "approver_id": "admin",
            "approver_role": "operator",
            "justification": "test",
        },
    })
    assert trace.human_override is not None
    assert trace.human_override.approver_id == "admin"


def test_add_override_without_policy_evaluation() -> None:
    """Branch: trace.py line 156→exit (policy_evaluation is None)."""
    trace = DecisionTrace(trace_id="no-policy")
    assert trace.policy_evaluation is None
    trace.add_override(HumanOverride(
        approver_id="admin",
        approver_role="operator",
        justification="test",
    ))
    assert trace.human_override is not None
    assert trace.policy_evaluation is None  # unchanged


def test_link_precedent_duplicate() -> None:
    """Branch: trace.py line 161 → False (already linked)."""
    trace = DecisionTrace(trace_id="dup-test")
    trace.link_precedent("abc")
    trace.link_precedent("abc")  # duplicate — should not append
    assert trace.precedent_trace_ids == ["abc"]


# ── tracer.py — span with early complete, verify_integrity edges ─

def test_span_with_explicit_complete() -> None:
    """Branch: tracer.py line 307→309 (completed_at already set)."""
    s = Sentinel()

    async def _run() -> None:
        async with s.span("test-span") as trace:
            trace.complete(output={"done": True}, latency_ms=5)
            assert trace.completed_at is not None

    asyncio.run(_run())


def test_verify_integrity_empty_inputs_and_output() -> None:
    """Branches: tracer.py 497→501, 502→506 (empty inputs/output skip hash check)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    s = Sentinel(storage=SQLiteStorage(db), store_inputs=False, store_outputs=False)

    @s.trace
    def agent(x: int) -> dict:
        return {"x": x}

    agent(x=1)
    tid = s.query(limit=1)[0].trace_id
    result = s.verify_integrity(tid)
    assert result.verified
    assert result.inputs_match
    assert result.output_match
    Path(db).unlink(missing_ok=True)


# ── signing.py — install_memory_keys partial args ────────────────────────

def test_install_memory_keys_private_only() -> None:
    """Branch: signing.py line 166→exit (public_key is None)."""
    from sentinel.crypto.signing import QuantumSafeSigner

    # Bypass __init__ oqs check — install_memory_keys is pure attribute assignment
    signer = QuantumSafeSigner.__new__(QuantumSafeSigner)
    signer._private_key = None
    signer._public_key = None
    signer.install_memory_keys(private_key=b"fake-private", public_key=None)
    assert signer._private_key == b"fake-private"
    assert signer._public_key is None


def test_install_memory_keys_public_only() -> None:
    """Branch: signing.py line 164→166 (private_key is None)."""
    from sentinel.crypto.signing import QuantumSafeSigner

    signer = QuantumSafeSigner.__new__(QuantumSafeSigner)
    signer._private_key = None
    signer._public_key = None
    signer.install_memory_keys(private_key=None, public_key=b"fake-public")
    assert signer._private_key is None
    assert signer._public_key == b"fake-public"


# ── langchain.py — _extract_model_name edge cases ───────────────

def test_extract_model_name_empty_list() -> None:
    """Branch: langchain.py line 188 → value is empty list."""
    from sentinel.integrations.langchain import _extract_model_name

    result = _extract_model_name({"name": []}, {})
    assert result == "unknown"


def test_extract_model_name_non_string_model() -> None:
    """Branch: langchain.py line 192/195/197 — non-string model values."""
    from sentinel.integrations.langchain import _extract_model_name

    # kwargs model is non-string via serialized
    result = _extract_model_name({"kwargs": {"model": 42}}, {})
    assert result == "unknown"

    # invocation_params model is non-string
    result = _extract_model_name(None, {"invocation_params": {"model": 42}})
    assert result == "unknown"

    # invocation_params is not a dict
    result = _extract_model_name(None, {"invocation_params": "not-a-dict"})
    assert result == "unknown"


# ── langfuse.py — _build_metadata without policy ────────────────

def test_build_metadata_no_policy() -> None:
    """Branch: langfuse.py line 228 → False (no policy_evaluation)."""
    from sentinel.integrations.langfuse import _build_metadata

    trace = DecisionTrace(trace_id="no-policy")
    meta = _build_metadata(trace)
    assert meta["sentinel.policy"] is None
    assert meta["sentinel.policy_result"] is None


# ── infrastructure.py — non-cloud storage class, non-matching env ─

def test_k8s_neutral_storage_class(tmp_path: Path) -> None:
    """Branch: infrastructure.py line 299→275 (no cloud match)."""
    from sentinel.scanner.infrastructure import InfrastructureScanner

    k8s = tmp_path / "k8s"
    k8s.mkdir()
    (k8s / "pvc.yaml").write_text(
        "apiVersion: v1\n"
        "kind: PersistentVolumeClaim\n"
        "spec:\n"
        "  storageClassName: local-path\n"
    )
    result = InfrastructureScanner().scan(repo_root=str(tmp_path))
    storage_findings = [
        f for f in result.findings if f.component == "kubernetes_storage_class"
    ]
    assert len(storage_findings) == 0


def test_env_file_non_matching_key(tmp_path: Path) -> None:
    """Branch: infrastructure.py line 327→325 (key doesn't match prefix)."""
    from sentinel.scanner.infrastructure import InfrastructureScanner

    (tmp_path / ".env").write_text("DATABASE_URL=postgres://localhost\nPORT=8080\n")
    result = InfrastructureScanner().scan(repo_root=str(tmp_path))
    env_findings = [
        f for f in result.findings if f.component == "env_var_prefix"
    ]
    assert len(env_findings) == 0


# ── runtime.py — cloud-exposed package with no alternative ───────

def test_suggest_alternatives_no_alternative() -> None:
    """Branch: runtime.py line 78→74 (alt is falsy)."""
    from sentinel.scanner.runtime import PackageReport, ScanResult

    result = ScanResult(
        packages=[
            PackageReport(
                name="obscure-us-package",
                version="1.0",
                parent_company="SomeUS Corp",
                jurisdiction="US",
                cloud_act_exposure=True,
                in_critical_path=False,
                is_optional=True,
            ),
        ],
        critical_path_violations=[],
    )
    alts = result.sovereign_alternatives()
    assert "obscure-us-package" not in alts


# ── base.py — purge_before with dry_run=False ───────────────────

def test_export_ndjson_partial_page(tmp_path: Path) -> None:
    """Branch: base.py line 141→123 (traces < page_size, early break)."""
    s = Sentinel(storage=SQLiteStorage(str(tmp_path / "export.db")))

    @s.trace
    def agent(x: int) -> dict:
        return {"x": x}

    agent(x=1)
    out = str(tmp_path / "traces.ndjson")
    count = s.storage.export_ndjson(out)
    assert count == 1
    assert Path(out).exists()


def test_purge_before_real_delete(tmp_path: Path) -> None:
    """Branch: base.py line 169 → True (dry_run=False)."""
    db = str(tmp_path / "purge.db")
    s = Sentinel(storage=SQLiteStorage(db))

    @s.trace
    def agent(x: int) -> dict:
        return {"x": x}

    agent(x=1)
    assert len(s.query(limit=10)) == 1

    # Purge with a future cutoff — should delete everything
    result = s.storage.purge_before(
        datetime(2099, 1, 1, tzinfo=UTC),
        dry_run=False,
    )
    assert result.traces_affected == 1
    assert len(s.query(limit=10)) == 0
