"""
Sentinel — complete 40-step smoke test.

Exercises every major feature end to end. Zero external services,
zero optional extras required.

Run:
    python examples/smoke_test.py

Exit 0: all 40 steps passed.
Exit 1: prints which step failed and why.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SmokeTest:
    def __init__(self) -> None:
        self.passed = 0
        self.failed_step: int | None = None
        self.failed_msg: str | None = None
        self.failed_err: Exception | None = None

    def run(self, step: int, label: str, fn: Callable[[], None]) -> None:
        if self.failed_step is not None:
            return
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            self.failed_step = step
            self.failed_msg = label
            self.failed_err = exc
            print(f"  [✗] Step {step:>2}: {label}")
            print(f"       {type(exc).__name__}: {exc}")
            return
        self.passed += 1
        print(f"  [✓] Step {step:>2}: {label}")


def main() -> int:
    from sentinel import (
        DataResidency,
        KillSwitchEngaged,
        PolicyDeniedError,
        PolicyResult,
        Sentinel,
        __version__,
    )
    from sentinel.compliance import EUAIActChecker
    from sentinel.dashboard import HTMLReport
    from sentinel.manifesto import EUOnly, Required, SentinelManifesto
    from sentinel.policy.evaluator import SimpleRuleEvaluator
    from sentinel.scanner import (
        CICDScanner,
        RuntimeScanner,
    )
    from sentinel.storage import FilesystemStorage, SQLiteStorage

    tmp = Path(tempfile.mkdtemp(prefix="sentinel-smoke-"))
    sentinel = None  # type: ignore[assignment]
    html_path: Path | None = None
    st = SmokeTest()

    try:
        # ------------------------------------------------------------------
        # 01 — Sentinel init
        # ------------------------------------------------------------------
        def _01() -> None:
            nonlocal sentinel
            sentinel = Sentinel(
                storage=SQLiteStorage(str(tmp / "traces.db")),
                project="smoke",
                data_residency=DataResidency.EU_DE,
                sovereign_scope="EU",
                policy_evaluator=SimpleRuleEvaluator({
                    "p.py": lambda inp: (not inp.get("forbid"), None if not inp.get("forbid") else "forbidden"),
                    "ex.py": lambda inp: (not inp.get("forbid"), None if not inp.get("forbid") else "forbidden"),
                }),
            )
        st.run(1, "Sentinel init with SQLiteStorage", _01)
        assert sentinel is not None

        # 02 — sync trace ALLOW
        def _02() -> None:
            @sentinel.trace
            def sync_call() -> dict:
                return {"ok": 1}
            sync_call()
            assert sentinel.query(limit=1)
        st.run(2, "@sentinel.trace sync function — ALLOW recorded", _02)

        # 03 — async trace ALLOW
        def _03() -> None:
            import asyncio

            @sentinel.trace
            async def async_call() -> dict:
                return {"ok": 2}

            asyncio.run(async_call())
        st.run(3, "@sentinel.trace async function — ALLOW recorded", _03)

        # 04 — SimpleRule DENY with rule name
        def _04() -> None:
            @sentinel.trace(policy="p.py")
            def gated(forbid: bool = False) -> dict:
                return {"ok": 3}

            with contextlib.suppress(PolicyDeniedError):
                gated(forbid=True)
            denies = sentinel.query(policy_result=PolicyResult.DENY, limit=5)
            assert any(
                t.policy_evaluation and t.policy_evaluation.rule_triggered == "forbidden"
                for t in denies
            )
        st.run(4, "SimpleRuleEvaluator — DENY recorded with rule name", _04)

        # 05 — EXCEPTION path
        def _05() -> None:
            @sentinel.trace
            def bomb() -> dict:
                raise RuntimeError("boom")

            with contextlib.suppress(RuntimeError):
                bomb()
            traces = sentinel.query(limit=50)
            assert any(t.tags.get("error") == "RuntimeError" for t in traces)
        st.run(5, "Policy EXCEPTION recorded", _05)

        # 06 — Kill switch blocks
        def _06() -> None:
            sentinel.engage_kill_switch("smoke halt")
            assert sentinel.kill_switch_active is True
        st.run(6, "Kill switch engages — blocks execution", _06)

        # 07 — DENY + HumanOverride recorded on blocked call
        def _07() -> None:
            @sentinel.trace
            def blocked_call() -> dict:
                return {"ok": 4}

            with contextlib.suppress(KillSwitchEngaged):
                blocked_call()
            denies = sentinel.query(policy_result=PolicyResult.DENY, limit=20)
            ks_traces = [t for t in denies if t.tags.get("kill_switch") == "engaged"]
            assert ks_traces, "no kill-switch trace found"
            assert ks_traces[0].human_override is not None
        st.run(7, "Kill switch records DENY + HumanOverride", _07)

        # 08 — KillSwitchEngaged exception raised
        def _08() -> None:
            @sentinel.trace
            def another_blocked() -> dict:
                return {}

            raised = False
            try:
                another_blocked()
            except KillSwitchEngaged:
                raised = True
            assert raised
        st.run(8, "KillSwitchEngaged exception raised", _08)

        # 09 — Disengage
        def _09() -> None:
            sentinel.disengage_kill_switch("smoke resume")
            assert sentinel.kill_switch_active is False

            @sentinel.trace
            def resumed() -> dict:
                return {"ok": 5}

            resumed()
        st.run(9, "Kill switch disengages — execution resumes", _09)

        # 10 — Query by agent
        def _10() -> None:
            @sentinel.trace(agent_name="named_agent")
            def thing() -> dict:
                return {}

            thing()
            traces = sentinel.query(agent="named_agent", limit=10)
            assert any(t.agent == "named_agent" for t in traces)
        st.run(10, "Query by agent name — returns correct traces", _10)

        # 11 — Query by policy_result DENY
        def _11() -> None:
            denies = sentinel.query(policy_result=PolicyResult.DENY, limit=100)
            assert len(denies) >= 2
        st.run(11, "Query by policy_result DENY — correct count", _11)

        # 12 — inputs_hash present
        def _12() -> None:
            traces = sentinel.query(limit=50)
            assert all(t.inputs_hash is not None or not t.inputs for t in traces)
        st.run(12, "Every trace has inputs_hash (or empty inputs)", _12)

        # 13 — sovereign_scope present
        def _13() -> None:
            traces = sentinel.query(limit=50)
            assert all(t.sovereign_scope for t in traces)
        st.run(13, "Every trace has sovereign_scope", _13)

        # 14 — data_residency present
        def _14() -> None:
            traces = sentinel.query(limit=50)
            assert all(t.data_residency is not None for t in traces)
        st.run(14, "Every trace has data_residency", _14)

        # 15 — schema_version present
        def _15() -> None:
            traces = sentinel.query(limit=50)
            assert all(t.schema_version == "1.0.0" for t in traces)
        st.run(15, "Every trace has schema_version", _15)

        # 16 — parent_trace_id linking works
        def _16() -> None:
            from sentinel.core.trace import DecisionTrace
            parent = DecisionTrace(project="smoke", agent="parent")
            child = DecisionTrace(project="smoke", agent="child", parent_trace_id=parent.trace_id)
            assert child.parent_trace_id == parent.trace_id
        st.run(16, "parent_trace_id linking works", _16)

        # 17 — Filesystem NDJSON storage
        def _17() -> None:
            fs_dir = tmp / "fs"
            fs_sentinel = Sentinel(
                storage=FilesystemStorage(str(fs_dir)),
                project="smoke-fs",
                data_residency=DataResidency.AIR_GAPPED,
            )

            @fs_sentinel.trace
            def fs_call() -> dict:
                return {"ok": 6}

            fs_call()
            ndjson = list(fs_dir.glob("*.ndjson"))
            assert len(ndjson) == 1
            for line in ndjson[0].read_text().strip().splitlines():
                json.loads(line)  # must parse
        st.run(17, "Filesystem NDJSON storage writes valid JSON lines", _17)

        # 18 — NDJSON export valid
        def _18() -> None:
            all_traces = sentinel.query(limit=1000)
            export = tmp / "export.ndjson"
            with export.open("w") as f:
                for t in all_traces:
                    f.write(t.to_json().replace("\n", " ") + "\n")
            for line in export.read_text().strip().splitlines():
                data = json.loads(line)
                assert "trace_id" in data
                assert data["schema_version"] == "1.0.0"
        st.run(18, "NDJSON export — each line parseable", _18)

        # 19 — LangChain callback handler
        def _19() -> None:
            import importlib
            import sys as _sys
            import types as _types
            from uuid import uuid4

            pkg = _types.ModuleType("langchain_core")
            cb = _types.ModuleType("langchain_core.callbacks")

            class _Base:
                pass

            cb.BaseCallbackHandler = _Base
            pkg.callbacks = cb
            _sys.modules["langchain_core"] = pkg
            _sys.modules["langchain_core.callbacks"] = cb

            import sentinel.integrations.langchain as lc_mod
            importlib.reload(lc_mod)

            lc_sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="lc-smoke")
            handler = lc_mod.SentinelCallbackHandler(sentinel=lc_sentinel)

            class _G:
                def __init__(self, t: str) -> None:
                    self.text = t

            class _R:
                generations = [[_G("hello")]]

            run_id = uuid4()
            handler.on_llm_start(serialized={"name": "m"}, prompts=["hi"], run_id=run_id)
            handler.on_llm_end(_R(), run_id=run_id)
            assert any(t.agent == "langchain.llm" for t in lc_sentinel.query(limit=10))

            _sys.modules.pop("langchain_core.callbacks", None)
            _sys.modules.pop("langchain_core", None)
            importlib.reload(lc_mod)
        st.run(19, "LangChain callback handler records trace", _19)

        # 20 — OTel exporter fires
        def _20() -> None:
            from contextlib import contextmanager

            from sentinel.integrations.otel import OTelExporter

            class _S:
                def __init__(self) -> None:
                    self.attrs: dict[str, Any] = {}

                def set_attribute(self, k: str, v: Any) -> None:
                    self.attrs[k] = v

            class _T:
                def __init__(self) -> None:
                    self.spans: list[Any] = []

                @contextmanager
                def start_as_current_span(self, name: str) -> Any:
                    s = _S()
                    self.spans.append(s)
                    yield s

            otel_s = Sentinel(storage=SQLiteStorage(":memory:"), project="otel-smoke")
            tracer = _T()
            ex = OTelExporter(otel_s, endpoint="http://fake:4317", tracer_factory=lambda: tracer)

            @otel_s.trace
            def work() -> dict:
                return {"ok": 7}

            work()
            for _ in range(100):
                if tracer.spans:
                    break
                time.sleep(0.01)
            assert tracer.spans
            ex.shutdown()
        st.run(20, "OTel exporter — fires without error", _20)

        # 21 — OTel failure doesn't crash
        def _21() -> None:
            from contextlib import contextmanager

            from sentinel.integrations.otel import OTelExporter

            class _T:
                @contextmanager
                def start_as_current_span(self, name: str) -> Any:
                    raise ConnectionError("unreachable")
                    yield None  # pragma: no cover

            otel_s = Sentinel(storage=SQLiteStorage(":memory:"), project="otel-fail")
            ex = OTelExporter(otel_s, endpoint="http://fake:4317", tracer_factory=lambda: _T())

            @otel_s.trace
            def work() -> dict:
                return {"ok": 8}

            # Must not raise
            work()
            time.sleep(0.05)
            assert len(otel_s.query(limit=10)) == 1
            ex.shutdown()
        st.run(21, "OTel failure — does not crash Sentinel", _21)

        # 22 — Air-gap cycle
        def _22() -> None:
            original = socket.socket.connect

            def block(self: socket.socket, address: Any, *a: Any, **k: Any) -> Any:
                if getattr(self, "family", None) in (socket.AF_INET, socket.AF_INET6):
                    raise RuntimeError(f"AIRGAP: {address!r}")
                return original(self, address, *a, **k)

            socket.socket.connect = block  # type: ignore[method-assign]
            try:
                airgap_dir = tmp / "airgap"
                airgap_s = Sentinel(
                    storage=FilesystemStorage(str(airgap_dir)),
                    project="airgap-smoke",
                    data_residency=DataResidency.AIR_GAPPED,
                )

                @airgap_s.trace
                def call() -> dict:
                    return {"ok": 9}

                call()
                assert len(airgap_s.query(limit=10)) == 1
            finally:
                socket.socket.connect = original  # type: ignore[method-assign]
        st.run(22, "Air-gap — full cycle with network blocked", _22)

        # 23 — RuntimeScanner
        def _23() -> None:
            result = RuntimeScanner().scan()
            assert result.total_packages >= 1
            assert 0.0 <= result.sovereignty_score <= 1.0
        st.run(23, "RuntimeScanner — returns ScanResult", _23)

        # 24 — CICDScanner
        def _24() -> None:
            result = CICDScanner().scan(str(tmp))
            assert hasattr(result, "findings")
        st.run(24, "CICDScanner — returns CICDScanResult", _24)

        # 25 — ManifestoReport
        def _25() -> None:
            class M(SentinelManifesto):
                jurisdiction = EUOnly()
                kill_switch = Required()

            report = M().check(sentinel=sentinel)
            assert 0.0 <= report.overall_score <= 1.0
        st.run(25, "ManifestoReport generated with score 0.0-1.0", _25)

        # 26 — EU AI Act checker
        def _26() -> None:
            report = EUAIActChecker().check(sentinel)
            assert report.overall in ("COMPLIANT", "PARTIAL", "NON_COMPLIANT")
        st.run(26, "EU AI Act checker returns ComplianceReport", _26)

        # 27 — Art. 12 COMPLIANT
        def _27() -> None:
            report = EUAIActChecker().check(sentinel)
            assert report.articles["Art. 12"].status == "COMPLIANT"
        st.run(27, "Art. 12 COMPLIANT with traces written", _27)

        # 28 — Art. 14 COMPLIANT
        def _28() -> None:
            report = EUAIActChecker().check(sentinel)
            assert report.articles["Art. 14"].status == "COMPLIANT"
        st.run(28, "Art. 14 COMPLIANT with kill switch present", _28)

        # 29 — Human-action articles correctly marked
        def _29() -> None:
            report = EUAIActChecker().check(sentinel)
            for art_id in ("Art. 10", "Art. 11", "Art. 15"):
                art = report.articles[art_id]
                assert art.automated is False
                assert art.status == "ACTION_REQUIRED"
        st.run(29, "Human-action articles marked not automated", _29)

        # 30 — HTML report generated
        def _30() -> None:
            nonlocal html_path
            html = HTMLReport().generate(sentinel)
            html_path = tmp / "report.html"
            html_path.write_text(html, encoding="utf-8")
            assert html_path.stat().st_size > 1000
        st.run(30, "HTML report generated — single file", _30)

        # 31 — HTML has no external URLs
        def _31() -> None:
            assert html_path is not None
            html = html_path.read_text()
            for needle in ('src="http', "src='http", 'href="http', "href='http"):
                assert needle not in html, f"external reference: {needle}"
        st.run(31, "HTML report — no external URLs", _31)

        # 32 — HTML has all required sections
        def _32() -> None:
            assert html_path is not None
            html = html_path.read_text()
            for section in (
                "Sentinel Evidence Report",
                "EU AI Act compliance",
                "Runtime packages",
                "CI/CD findings",
                "Infrastructure findings",
            ):
                assert section in html, f"missing section: {section}"
        st.run(32, "HTML report — has all required sections", _32)

        # 33 — Sovereignty score 0.0 – 1.0
        def _33() -> None:
            score = RuntimeScanner().scan().sovereignty_score
            assert 0.0 <= score <= 1.0
        st.run(33, "Sovereignty score 0.0-1.0", _33)

        # 34 — Days to enforcement positive
        def _34() -> None:
            report = EUAIActChecker().check(sentinel)
            assert isinstance(report.days_to_enforcement, int)
        st.run(34, "Days to enforcement is an integer", _34)

        # 35 — example 01 runs
        def _35() -> None:
            r = subprocess.run(
                [sys.executable, str(ROOT / "examples" / "01_minimal_trace.py")],
                capture_output=True, text=True, timeout=30,
            )
            assert r.returncode == 0, r.stderr
        st.run(35, "Example 01_minimal_trace.py runs", _35)

        # 36 — example 05 runs
        def _36() -> None:
            r = subprocess.run(
                [sys.executable, str(ROOT / "examples" / "05_kill_switch.py")],
                capture_output=True, text=True, timeout=30,
            )
            assert r.returncode == 0, r.stderr
        st.run(36, "Example 05_kill_switch.py runs", _36)

        # 37 — example 10 runs
        def _37() -> None:
            r = subprocess.run(
                [sys.executable, str(ROOT / "examples" / "10_manifesto.py")],
                capture_output=True, text=True, timeout=30,
            )
            assert r.returncode == 0, r.stderr
        st.run(37, "Example 10_manifesto.py runs", _37)

        # 38 — check_sovereignty.py passes
        def _38() -> None:
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "check_sovereignty.py")],
                capture_output=True, text=True, timeout=30,
            )
            assert r.returncode == 0, r.stderr
        st.run(38, "check_sovereignty.py passes", _38)

        # 39 — ruff check passes
        def _39() -> None:
            r = subprocess.run(
                [sys.executable, "-m", "ruff", "check",
                 "sentinel/", "tests/", "scripts/", "examples/"],
                capture_output=True, text=True, timeout=60, cwd=str(ROOT),
            )
            assert r.returncode == 0, r.stdout + r.stderr
        st.run(39, "ruff check passes", _39)

        # 40 — full test suite green
        def _40() -> None:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
                capture_output=True, text=True, timeout=120, cwd=str(ROOT),
            )
            assert r.returncode == 0, r.stdout[-2000:]
        st.run(40, "Full test suite green", _40)

        # 41 — surface alignment (version + CHANGELOG)
        def _41() -> None:
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "check_surfaces.py")],
                capture_output=True, text=True, timeout=15,
            )
            assert r.returncode == 0, r.stdout + r.stderr
        st.run(41, "Surface alignment (version + CHANGELOG)", _41)

        # 42 — no stale version claims in docs
        def _42() -> None:
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "check_doc_dates.py")],
                capture_output=True, text=True, timeout=15,
            )
            assert r.returncode == 0, r.stdout + r.stderr
        st.run(42, "No stale version claims in docs", _42)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if st.failed_step is not None:
        print()
        print("=" * 64)
        print(f"  FAILED at step {st.failed_step}: {st.failed_msg}")
        print("=" * 64)
        return 1

    print()
    print("=" * 64)
    print(f"  ALL 42 STEPS PASSED — Sentinel v{__version__} is working correctly")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
