"""
examples/smoke_test.py
~~~~~~~~~~~~~~~~~~~~~~
End-to-end smoke test for the full Sentinel v0.9 platform.

Runs every major feature and exits 0 on success. A broken step
prints which one failed and why, then exits 1.

Requires only the core package (no optional extras).

Steps:
    1.  SQLite trace written
    2.  Filesystem NDJSON trace written
    3.  Policy ALLOW recorded correctly
    4.  Policy DENY recorded with rule name
    5.  Kill switch blocks execution
    6.  Kill switch records HumanOverride
    7.  Kill switch disengage restores operation
    8.  LangChain callback handler records trace (mocked langchain_core)
    9.  OTel exporter fires (fake tracer)
   10.  Sovereignty scanner detects test deps
   11.  Manifesto check produces report
   12.  EU AI Act checker runs
   13.  HTML report generated and valid
   14.  Air-gapped cycle completes (socket.connect blocked)
   15.  NDJSON export valid
   16.  All traces queryable

Run:
    python examples/smoke_test.py
"""

from __future__ import annotations

import json
import shutil
import socket
import sys
import tempfile
from pathlib import Path
from typing import Any


def _ok(step: int, msg: str) -> None:
    print(f"  [✓] Step {step:>2}: {msg}")


def _fail(step: int, msg: str, err: Exception | None = None) -> int:
    print(f"  [✗] Step {step:>2}: {msg}")
    if err is not None:
        print(f"       {type(err).__name__}: {err}")
    return 1


def run() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="sentinel-smoke-"))
    try:
        return _run_steps(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _run_steps(tmp: Path) -> int:  # noqa: PLR0911, PLR0915
    from sentinel import (
        DataResidency,
        KillSwitchEngaged,
        PolicyDeniedError,
        PolicyResult,
        Sentinel,
    )
    from sentinel.compliance import EUAIActChecker
    from sentinel.dashboard import HTMLReport
    from sentinel.manifesto import EUOnly, SentinelManifesto
    from sentinel.policy.evaluator import SimpleRuleEvaluator
    from sentinel.scanner import RuntimeScanner
    from sentinel.storage import FilesystemStorage, SQLiteStorage

    def policy(inputs: dict) -> tuple[bool, str | None]:
        if inputs.get("forbid"):
            return False, "forbidden"
        return True, None

    # --- 1: SQLite trace ---------------------------------------------------
    sqlite_path = tmp / "traces.db"
    try:
        sentinel = Sentinel(
            storage=SQLiteStorage(str(sqlite_path)),
            project="smoke",
            data_residency=DataResidency.EU_DE,
            sovereign_scope="EU",
            policy_evaluator=SimpleRuleEvaluator({"p.py": policy}),
        )

        @sentinel.trace
        def first_call() -> dict:
            return {"ok": 1}

        first_call()
        assert sqlite_path.exists()
        _ok(1, "SQLite trace written")
    except Exception as e:
        return _fail(1, "SQLite trace write", e)

    # --- 2: Filesystem NDJSON trace ---------------------------------------
    fs_dir = tmp / "fs"
    try:
        fs_sentinel = Sentinel(
            storage=FilesystemStorage(str(fs_dir)),
            project="smoke-fs",
            data_residency=DataResidency.AIR_GAPPED,
        )

        @fs_sentinel.trace
        def fs_call() -> dict:
            return {"ok": 2}

        fs_call()
        ndjson_files = list(fs_dir.glob("*.ndjson"))
        assert len(ndjson_files) == 1
        _ok(2, "Filesystem NDJSON trace written")
    except Exception as e:
        return _fail(2, "Filesystem NDJSON write", e)

    # --- 3: Policy ALLOW recorded correctly -------------------------------
    try:
        @sentinel.trace(policy="p.py")
        def allow_call(forbid: bool = False) -> dict:
            return {"x": 1}

        allow_call(forbid=False)
        allow_traces = sentinel.query(policy_result=PolicyResult.ALLOW, limit=10)
        assert any("allow_call" in t.agent for t in allow_traces)
        _ok(3, "Policy ALLOW recorded")
    except Exception as e:
        return _fail(3, "Policy ALLOW", e)

    # --- 4: Policy DENY with rule name ------------------------------------
    try:
        import contextlib

        with contextlib.suppress(PolicyDeniedError):
            allow_call(forbid=True)
        deny_traces = sentinel.query(policy_result=PolicyResult.DENY, limit=10)
        deny_with_rule = [
            t for t in deny_traces
            if t.policy_evaluation and t.policy_evaluation.rule_triggered == "forbidden"
        ]
        assert deny_with_rule
        _ok(4, "Policy DENY recorded with rule name")
    except Exception as e:
        return _fail(4, "Policy DENY with rule", e)

    # --- 5: Kill switch blocks execution ----------------------------------
    try:
        sentinel.engage_kill_switch("smoke test halt")
        blocked = False
        try:
            @sentinel.trace
            def after_halt() -> dict:
                return {}
            after_halt()
        except KillSwitchEngaged:
            blocked = True
        assert blocked
        _ok(5, "Kill switch blocked execution")
    except Exception as e:
        return _fail(5, "Kill switch block", e)

    # --- 6: Kill switch records HumanOverride -----------------------------
    try:
        ks_traces = sentinel.query(policy_result=PolicyResult.DENY, limit=20)
        ks_trace = next(
            (t for t in ks_traces if t.tags.get("kill_switch") == "engaged"),
            None,
        )
        assert ks_trace is not None
        assert ks_trace.human_override is not None
        assert ks_trace.human_override.approver_id == "kill-switch"
        _ok(6, "Kill switch recorded HumanOverride")
    except Exception as e:
        return _fail(6, "Kill switch HumanOverride", e)

    # --- 7: Disengage restores operation ----------------------------------
    try:
        sentinel.disengage_kill_switch("smoke resume")
        @sentinel.trace
        def after_resume() -> dict:
            return {"resumed": True}
        result = after_resume()
        assert result == {"resumed": True}
        _ok(7, "Kill switch disengage restored operation")
    except Exception as e:
        return _fail(7, "Kill switch disengage", e)

    # --- 8: LangChain callback handler ------------------------------------
    try:
        import importlib as _importlib
        import sys as _sys
        import types as _types

        fake_pkg = _types.ModuleType("langchain_core")
        fake_cb = _types.ModuleType("langchain_core.callbacks")

        class _Base:
            pass

        fake_cb.BaseCallbackHandler = _Base
        fake_pkg.callbacks = fake_cb
        _sys.modules["langchain_core"] = fake_pkg
        _sys.modules["langchain_core.callbacks"] = fake_cb

        import sentinel.integrations.langchain as lc_mod
        _importlib.reload(lc_mod)

        lc_sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="smoke-lc")
        handler = lc_mod.SentinelCallbackHandler(sentinel=lc_sentinel)

        class _G:
            def __init__(self, t: str) -> None:
                self.text = t

        class _R:
            generations = [[_G("hello")]]

        handler.on_llm_start(serialized={"name": "test-model"}, prompts=["hi"])
        handler.on_llm_end(_R())
        lc_traces = lc_sentinel.query(limit=10)
        assert any(t.agent == "langchain.llm" for t in lc_traces)

        _sys.modules.pop("langchain_core.callbacks", None)
        _sys.modules.pop("langchain_core", None)
        _importlib.reload(lc_mod)
        _ok(8, "LangChain callback handler recorded trace")
    except Exception as e:
        return _fail(8, "LangChain callback", e)

    # --- 9: OTel exporter (fake tracer) -----------------------------------
    try:
        from contextlib import contextmanager

        from sentinel.integrations.otel import OTelExporter

        class _Span:
            def __init__(self) -> None:
                self.attrs: dict[str, Any] = {}
            def set_attribute(self, k: str, v: Any) -> None:
                self.attrs[k] = v

        class _Tracer:
            def __init__(self) -> None:
                self.spans: list[_Span] = []
            @contextmanager
            def start_as_current_span(self, name: str):
                s = _Span()
                self.spans.append(s)
                yield s

        otel_sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="smoke-otel")
        tracer = _Tracer()
        exporter = OTelExporter(
            otel_sentinel, endpoint="http://fake:4317", tracer_factory=lambda: tracer
        )

        @otel_sentinel.trace
        def otel_work() -> dict:
            return {"ok": 1}

        otel_work()
        import time
        for _ in range(100):
            if tracer.spans:
                break
            time.sleep(0.01)
        assert tracer.spans, "OTel span was not emitted"
        exporter.shutdown()
        _ok(9, "OTel exporter emitted span")
    except Exception as e:
        return _fail(9, "OTel exporter", e)

    # --- 10: Sovereignty scanner ------------------------------------------
    try:
        result = RuntimeScanner().scan()
        assert result.total_packages > 0
        _ok(10, f"Sovereignty scanner: {result.total_packages} packages, score={result.sovereignty_score:.0%}")
    except Exception as e:
        return _fail(10, "Sovereignty scanner", e)

    # --- 11: Manifesto report ---------------------------------------------
    try:
        class M(SentinelManifesto):
            jurisdiction = EUOnly()

        report = M().check(sentinel=sentinel)
        assert 0.0 <= report.overall_score <= 1.0
        _ok(11, f"Manifesto report: score={report.overall_score:.0%}")
    except Exception as e:
        return _fail(11, "Manifesto report", e)

    # --- 12: EU AI Act checker --------------------------------------------
    try:
        compliance = EUAIActChecker().check(sentinel)
        assert compliance.articles["Art. 12"].status == "COMPLIANT"
        assert compliance.articles["Art. 14"].status == "COMPLIANT"
        _ok(12, f"EU AI Act checker: overall={compliance.overall}")
    except Exception as e:
        return _fail(12, "EU AI Act checker", e)

    # --- 13: HTML report --------------------------------------------------
    try:
        html_path = tmp / "report.html"
        html = HTMLReport().generate(sentinel)
        assert "<html" in html
        assert "src=\"http" not in html  # self-contained
        html_path.write_text(html)
        assert html_path.stat().st_size > 1000
        _ok(13, "HTML report generated and self-contained")
    except Exception as e:
        return _fail(13, "HTML report", e)

    # --- 14: Air-gapped cycle ---------------------------------------------
    try:
        original_connect = socket.socket.connect

        def block_connect(self: socket.socket, address: Any, *a: Any, **k: Any) -> Any:
            if getattr(self, "family", None) in (socket.AF_INET, socket.AF_INET6):
                raise RuntimeError(f"AIRGAP VIOLATION: {address!r}")
            return original_connect(self, address, *a, **k)

        socket.socket.connect = block_connect  # type: ignore[method-assign]
        try:
            airgap_sentinel = Sentinel(
                storage=FilesystemStorage(str(tmp / "airgap")),
                project="smoke-airgap",
                data_residency=DataResidency.AIR_GAPPED,
            )

            @airgap_sentinel.trace
            def airgap_call() -> dict:
                return {"ok": 1}

            airgap_call()
            traces = airgap_sentinel.query(limit=10)
            assert len(traces) == 1
        finally:
            socket.socket.connect = original_connect  # type: ignore[method-assign]
        _ok(14, "Air-gapped cycle completed")
    except Exception as e:
        return _fail(14, "Air-gapped cycle", e)

    # --- 15: NDJSON export -------------------------------------------------
    try:
        all_traces = sentinel.query(limit=1000)
        export_path = tmp / "export.ndjson"
        with open(export_path, "w", encoding="utf-8") as f:
            for t in all_traces:
                f.write(t.to_json().replace("\n", " ") + "\n")
        lines = export_path.read_text().strip().splitlines()
        for line in lines:
            data = json.loads(line)
            assert "trace_id" in data
            assert data["schema_version"] == "1.0.0"
        _ok(15, f"NDJSON export valid ({len(lines)} traces)")
    except Exception as e:
        return _fail(15, "NDJSON export", e)

    # --- 16: All traces queryable -----------------------------------------
    try:
        queried = sentinel.query(limit=1000)
        assert len(queried) >= 5
        _ok(16, f"All traces queryable ({len(queried)} found)")
    except Exception as e:
        return _fail(16, "Trace query", e)

    print()
    print("=" * 64)
    print("  ALL 16 STEPS PASSED — Sentinel v0.9 is working correctly")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(run())
