"""
tests/test_coverage_100.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Targeted tests to bring every module to 100% coverage.

Each test block names the file and the specific uncovered line(s)
it is hitting, so future refactors can reason about whether the
test is still load-bearing.
"""

from __future__ import annotations

import builtins
from pathlib import Path
from types import SimpleNamespace

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


def _sentinel(tmp_path: Path) -> Sentinel:
    return Sentinel(
        storage=SQLiteStorage(str(tmp_path / "cov100.db")),
        project="cov100",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator(
            {"p.py": lambda inputs: (True, None)}
        ),
    )


# ===========================================================================
# sentinel/core/tracer.py — lines 66, 68
# ===========================================================================


def test_tracer_default_storage_is_sqlite(tmp_path: Path, monkeypatch) -> None:
    """No storage argument → SQLiteStorage('./sentinel-traces.db')."""
    monkeypatch.chdir(tmp_path)
    sentinel = Sentinel(project="default-storage-test")
    assert sentinel.storage.backend_name == "sqlite"
    # Clean up the default db file
    Path(tmp_path / "sentinel-traces.db").unlink(missing_ok=True)


def test_tracer_string_storage_is_sqlite(tmp_path: Path) -> None:
    """storage=str → SQLiteStorage(path)."""
    db_path = str(tmp_path / "explicit.db")
    sentinel = Sentinel(storage=db_path, project="string-storage-test")
    assert sentinel.storage.backend_name == "sqlite"


# ===========================================================================
# sentinel/core/trace.py — line 137
# ===========================================================================


def test_trace_post_init_hashes_output_when_provided() -> None:
    """DecisionTrace constructed with `output` but no `output_hash` → auto-hash."""
    from sentinel.core.trace import DecisionTrace

    trace = DecisionTrace(
        project="hash-test",
        agent="t",
        inputs={"x": 1},
        output={"y": 2},
    )
    assert trace.output_hash is not None
    assert len(trace.output_hash) == 64  # sha256 hex


# ===========================================================================
# sentinel/scanner/runtime.py — lines 64, 152
# ===========================================================================


def test_scan_result_sovereignty_score_empty_is_one() -> None:
    from sentinel.scanner.runtime import ScanResult

    result = ScanResult()
    assert result.sovereignty_score == 1.0


def test_runtime_scanner_skips_dist_with_no_name(monkeypatch) -> None:
    """_iter_installed() skips distributions whose metadata has no Name."""
    import sentinel.scanner.runtime as rt_mod

    class _FakeDist:
        def __init__(self, name_value, version="1.0"):
            self.metadata = {"Name": name_value}
            self.version = version

    def fake_distributions():
        return [
            _FakeDist(""),          # no name → skipped
            _FakeDist("realpkg"),
            _FakeDist(None),        # also no name → skipped
        ]

    monkeypatch.setattr(
        rt_mod.importlib_metadata, "distributions", fake_distributions
    )
    scanner = rt_mod.RuntimeScanner()
    # installed list is None → real _iter_installed path
    result = scanner.scan()
    names = {p.name for p in result.packages}
    assert "realpkg" in names
    assert "" not in names


# ===========================================================================
# sentinel/compliance/euaiact.py — lines 69, 81, 95
# ===========================================================================


def test_compliance_automated_coverage_empty_articles() -> None:
    from datetime import datetime

    from sentinel.compliance.euaiact import ComplianceReport

    report = ComplianceReport(timestamp=datetime.now())
    assert report.automated_coverage == 0.0
    assert report.overall == "UNKNOWN"


def test_compliance_diff_returns_no_gaps_for_clean_report() -> None:
    from datetime import datetime

    from sentinel.compliance.euaiact import ArticleReport, ComplianceReport

    report = ComplianceReport(timestamp=datetime.now())
    report.articles["Art. 12"] = ArticleReport(
        article="Art. 12",
        title="Automatic logging",
        status="COMPLIANT",
        automated=True,
        detail="ok",
    )
    assert report.diff() == "No gaps. All automated checks pass."


# ===========================================================================
# sentinel/storage/base.py — lines 106, 111, 136
# ===========================================================================


def test_storage_export_ndjson_empty_query_breaks_pagination(tmp_path: Path) -> None:
    """No traces in storage → query() returns empty → pagination break."""
    sentinel = _sentinel(tmp_path)  # no traces recorded
    out = tmp_path / "empty.ndjson"
    count = sentinel.storage.export_ndjson(out)
    assert count == 0
    assert out.exists()
    assert out.read_text() == ""


def test_storage_export_ndjson_respects_end_filter(tmp_path: Path) -> None:
    """end filter skips traces with started_at >= end."""
    from datetime import UTC, datetime, timedelta

    sentinel = _sentinel(tmp_path)

    @sentinel.trace(agent_name="a")
    def agent(x: int) -> dict:
        return {"x": x}

    for i in range(3):
        agent(x=i)

    # end = now - 1 day → all traces are in the future → all skipped
    out = tmp_path / "filtered.ndjson"
    end = datetime.now(UTC) - timedelta(days=1)
    count = sentinel.storage.export_ndjson(out, end=end)
    assert count == 0


def test_storage_import_ndjson_skips_blank_lines(tmp_path: Path) -> None:
    """Blank lines in the NDJSON input are skipped silently."""
    sentinel = _sentinel(tmp_path)
    out = tmp_path / "with_blanks.ndjson"

    @sentinel.trace(agent_name="a")
    def agent(x: int) -> dict:
        return {"x": x}

    agent(x=1)
    sentinel.storage.export_ndjson(out)

    # Inject blank lines
    content = out.read_text()
    out.write_text("\n\n" + content + "\n\n")

    dst = Sentinel(
        storage=SQLiteStorage(str(tmp_path / "dst.db")),
        project="dst",
    )
    imported, skipped = dst.storage.import_ndjson(out)
    assert imported == 1
    assert skipped == 0


# ===========================================================================
# sentinel/integrations/otel.py — lines 49-53, 56, 198
# ===========================================================================


def test_otel_import_guard_raises_helpful_error(monkeypatch) -> None:
    """Force import error on the real opentelemetry packages."""
    import sentinel.integrations.otel as otel_mod

    original_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError("blocked for test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ImportError) as excinfo:
        otel_mod._import_otel()
    assert "sentinel-kernel[otel]" in str(excinfo.value)


def test_otel_import_returns_modules_when_available() -> None:
    """The import helper returns the real opentelemetry modules when installed."""
    import sentinel.integrations.otel as otel_mod

    try:
        result = otel_mod._import_otel()
    except ImportError:
        pytest.skip("opentelemetry not installed in this environment")
    otel_trace, provider_tuple, exporter = result
    assert otel_trace is not None
    assert provider_tuple is not None
    assert exporter is not None


def test_otel_exporter_flush_placeholder(tmp_path: Path) -> None:
    """Exercise the flush() method's wait loop (otel.py:198).

    Stops the background worker first so the queue cannot drain, then
    enqueues traces and calls flush with a short timeout. The wait loop
    is guaranteed to execute at least once before the deadline fires.
    """
    import sentinel.integrations.otel as otel_mod
    from sentinel.core.trace import DecisionTrace

    sentinel = _sentinel(tmp_path)

    class _FakeTracer:
        def start_as_current_span(self, name):  # noqa: ARG002
            class _Span:
                def __enter__(self_inner):
                    return SimpleNamespace(set_attribute=lambda *a, **kw: None)

                def __exit__(self_inner, *a):
                    return False

            return _Span()

    exporter = otel_mod.OTelExporter(
        sentinel=sentinel,
        endpoint="http://unused",
        tracer_factory=lambda: _FakeTracer(),
    )
    # Stop the worker so the queue doesn't drain.
    exporter._stop.set()
    exporter._worker.join(timeout=1.0)

    # Load the queue with a pile of traces.
    for i in range(50):
        trace = DecisionTrace(
            project="flush-test",
            agent=f"a{i}",
            inputs={"x": i},
        )
        exporter._enqueue(trace)

    # Flush runs the wait loop because queue is non-empty; deadline expires.
    exporter.flush(timeout=0.05)


def test_langchain_callback_init_raises_without_extra(monkeypatch) -> None:
    """Line 77: SentinelCallbackHandler() raises ImportError when _HAS_LANGCHAIN is False."""
    import sentinel.integrations.langchain as lc_mod

    monkeypatch.setattr(lc_mod, "_HAS_LANGCHAIN", False)
    with pytest.raises(ImportError) as excinfo:
        lc_mod.SentinelCallbackHandler(sentinel=None)  # type: ignore[arg-type]
    assert "sentinel-kernel[langchain]" in str(excinfo.value)


# ===========================================================================
# sentinel/integrations/langchain.py — line 40
# ===========================================================================


def test_langchain_import_guard_raises(monkeypatch) -> None:
    import sentinel.integrations.langchain as lc_mod

    original_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "langchain_core.callbacks":
            raise ImportError("blocked")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ImportError) as excinfo:
        lc_mod._import_base_callback_handler()
    assert "sentinel-kernel[langchain]" in str(excinfo.value)


def test_langchain_import_returns_base_handler_when_installed() -> None:
    """Hit the happy-path `return BaseCallbackHandler` line (langchain.py:40)."""
    import sentinel.integrations.langchain as lc_mod

    try:
        import langchain_core  # noqa: F401
    except ImportError:
        pytest.skip("langchain-core not installed")

    base = lc_mod._import_base_callback_handler()
    assert base is not None
    assert hasattr(base, "__name__")


# ===========================================================================
# sentinel/integrations/langfuse.py — line 39
# ===========================================================================


def test_langfuse_import_guard_raises(monkeypatch) -> None:
    import sentinel.integrations.langfuse as lf_mod

    original_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "langfuse":
            raise ImportError("blocked")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ImportError) as excinfo:
        lf_mod._import_langfuse_client()
    assert "sentinel-kernel[langfuse]" in str(excinfo.value)


def test_langfuse_import_returns_client_when_installed() -> None:
    """Hit the happy-path return line in _import_langfuse_client."""
    import sentinel.integrations.langfuse as lf_mod

    try:
        import langfuse  # noqa: F401
    except ImportError:
        pytest.skip("langfuse not installed")

    client = lf_mod._import_langfuse_client()
    assert client is not None


# ===========================================================================
# sentinel/storage/postgres.py — line 37
# ===========================================================================


def test_postgres_import_guard_raises(monkeypatch) -> None:
    import sentinel.storage.postgres as pg_mod

    original_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "psycopg2":
            raise ImportError("blocked")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ImportError) as excinfo:
        pg_mod._import_psycopg2()
    assert "sentinel-kernel[postgres]" in str(excinfo.value)


def test_postgres_import_returns_module_when_installed() -> None:
    """Hit the happy-path return line in _import_psycopg2."""
    import sentinel.storage.postgres as pg_mod

    try:
        import psycopg2  # noqa: F401
    except ImportError:
        pytest.skip("psycopg2 not installed")

    module = pg_mod._import_psycopg2()
    assert module is not None
    assert hasattr(module, "connect")


# ===========================================================================
# sentinel/manifesto/base.py — lines 626, 675, 679, 685, 688
# ===========================================================================


def test_audit_trail_integrity_no_sentinel() -> None:
    """Line 626: AuditTrailIntegrity.check with sentinel=None."""
    from sentinel.manifesto import AuditTrailIntegrity, SentinelManifesto

    class M(SentinelManifesto):
        audit = AuditTrailIntegrity()

    report = M().check(sentinel=None)
    assert report.sovereignty_dimensions["audit"].satisfied is False
    assert "No Sentinel instance" in report.sovereignty_dimensions["audit"].detail


def test_vsnfd_ready_rejects_unknown_storage_backend(tmp_path: Path) -> None:
    """Line 675: VSNfDReady flags a non-approved storage backend name."""
    from sentinel.manifesto import SentinelManifesto, VSNfDReady
    from sentinel.storage.base import StorageBackend

    class _CustomStorage(StorageBackend):
        @property
        def backend_name(self):
            return "unknown-backend"

        def initialise(self):
            pass

        def save(self, trace):
            pass

        def query(self, **kwargs):
            return []

        def get(self, trace_id):
            return None

    class M(SentinelManifesto):
        vsnfd = VSNfDReady()

    sentinel = Sentinel(
        storage=_CustomStorage(),
        project="unknown-backend",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator({"p.py": lambda i: (True, None)}),
    )
    report = M().check(sentinel=sentinel)
    dim = report.sovereignty_dimensions["vsnfd"]
    assert dim.satisfied is False
    assert "not approved for VS-NfD" in dim.detail


def test_vsnfd_ready_rejects_non_eu_residency(tmp_path: Path) -> None:
    """Line 679: residency 'LOCAL' is accepted; arbitrary value is rejected."""
    from sentinel.manifesto import SentinelManifesto, VSNfDReady
    from sentinel.storage.filesystem import FilesystemStorage

    class _FakeResidency:
        value = "us-west"

    class M(SentinelManifesto):
        vsnfd = VSNfDReady()

    sentinel = Sentinel(
        storage=FilesystemStorage(str(tmp_path / "fs")),
        project="non-eu",
        data_residency=DataResidency.EU_DE,  # real enum, we'll override below
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator({"p.py": lambda i: (True, None)}),
    )
    sentinel.data_residency = _FakeResidency()  # type: ignore[assignment]
    report = M().check(sentinel=sentinel)
    dim = report.sovereignty_dimensions["vsnfd"]
    assert dim.satisfied is False
    assert "data_residency" in dim.detail


def test_vsnfd_ready_rejects_custom_sovereign_scope(tmp_path: Path) -> None:
    """Line 685: sovereign_scope='CUSTOM' is not EU or LOCAL."""
    from sentinel.manifesto import SentinelManifesto, VSNfDReady
    from sentinel.storage.filesystem import FilesystemStorage

    class M(SentinelManifesto):
        vsnfd = VSNfDReady()

    sentinel = Sentinel(
        storage=FilesystemStorage(str(tmp_path / "fs2")),
        project="custom-scope",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="CUSTOM",
        policy_evaluator=SimpleRuleEvaluator({"p.py": lambda i: (True, None)}),
    )
    report = M().check(sentinel=sentinel)
    dim = report.sovereignty_dimensions["vsnfd"]
    assert dim.satisfied is False
    assert "sovereign_scope 'CUSTOM'" in dim.detail


def test_vsnfd_ready_rejects_missing_kill_switch(tmp_path: Path) -> None:
    """Line 688: a Sentinel-like object with no engage_kill_switch attribute."""
    from sentinel.manifesto import SentinelManifesto, VSNfDReady
    from sentinel.policy.evaluator import SimpleRuleEvaluator
    from sentinel.storage.filesystem import FilesystemStorage

    class _NoKillSwitch:
        storage = FilesystemStorage(str(tmp_path / "nks"))
        data_residency = DataResidency.EU_DE
        sovereign_scope = "EU"
        policy_evaluator = SimpleRuleEvaluator({"p.py": lambda i: (True, None)})

    class M(SentinelManifesto):
        vsnfd = VSNfDReady()

    report = M().check(sentinel=_NoKillSwitch())  # type: ignore[arg-type]
    dim = report.sovereignty_dimensions["vsnfd"]
    assert dim.satisfied is False
    assert "kill switch API missing" in dim.detail


# ===========================================================================
# sentinel/cli.py — lines 243, 258-259, 310-314, 326-328, 467, 482
# ===========================================================================


def test_cli_demo_default_output_uses_cwd(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """
    `sentinel demo` with no --output writes the report into the
    current working directory. Covers the CWD branch of
    _resolve_demo_output and the printed open command.
    """
    from sentinel import cli

    monkeypatch.chdir(tmp_path)
    rc = cli.main(["demo", "--no-kill-switch"])
    assert rc == 0
    out = capsys.readouterr().out
    default_path = (tmp_path / "sentinel_demo_report.html").resolve()
    assert default_path.exists()
    assert f"Report saved: {default_path}" in out
    assert f"open '{default_path}'" in out


def test_cli_demo_falls_back_to_tempdir_when_cwd_read_only(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """
    When the CWD is not writable, `sentinel demo` must fall back to
    the tempdir and announce the fallback. Covers the tempdir branch
    of _resolve_demo_output.
    """
    import os as _os
    import tempfile as _tempfile

    from sentinel import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_tempfile, "gettempdir", lambda: str(tmp_path))

    real_access = _os.access

    def fake_access(path, mode):
        try:
            if Path(str(path)).resolve() == tmp_path.resolve() and mode & _os.W_OK:
                return False
        except Exception:
            pass
        return real_access(path, mode)

    monkeypatch.setattr(_os, "access", fake_access)

    rc = cli.main(["demo", "--no-kill-switch"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CWD not writable" in out
    # Fallback path is under the patched gettempdir (== tmp_path)
    assert (tmp_path / "sentinel_demo_report.html").exists()


def test_cli_demo_dashboard_render_failure_is_swallowed(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Lines 258-259: dashboard render exception is caught and logged."""
    from sentinel import cli
    from sentinel.dashboard import terminal

    def boom(self):  # noqa: ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr(terminal.TerminalDashboard, "render_once", boom)
    out_path = tmp_path / "report.html"
    rc = cli.main(["demo", "--output", str(out_path), "--no-kill-switch"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "dashboard render skipped" in out


def test_cli_scan_text_suggest_alternatives_nonempty(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Lines 310-314: scan --suggest-alternatives with real results triggers the print loop."""
    from sentinel import cli
    from sentinel.scanner.runtime import PackageReport, RuntimeScanner, ScanResult

    # Inject a runtime result with an openai package so alternatives are produced
    def fake_scan(self):
        return ScanResult(
            packages=[
                PackageReport(
                    name="openai",
                    version="1.0",
                    parent_company="OpenAI",
                    jurisdiction="US",
                    cloud_act_exposure=True,
                    in_critical_path=True,
                    is_optional=False,
                ),
            ],
            critical_path_violations=["openai"],
        )

    monkeypatch.setattr(RuntimeScanner, "scan", fake_scan)
    rc = cli.main(
        ["scan", "--runtime", "--suggest-alternatives", "--repo", str(tmp_path)]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "EU-SOVEREIGN ALTERNATIVES" in out
    assert "openai →" in out


def test_cli_print_scan_text_shows_critical_path_violations(
    capsys, monkeypatch
) -> None:
    """Lines 326-328: _print_scan_text prints the critical-path violation block."""
    from sentinel import cli
    from sentinel.scanner.runtime import PackageReport, RuntimeScanner, ScanResult

    def fake_scan(self):
        return ScanResult(
            packages=[
                PackageReport(
                    name="boto3",
                    version="1.34",
                    parent_company="Amazon",
                    jurisdiction="US",
                    cloud_act_exposure=True,
                    in_critical_path=True,
                    is_optional=False,
                ),
            ],
            critical_path_violations=["boto3 (Amazon, US)"],
        )

    monkeypatch.setattr(RuntimeScanner, "scan", fake_scan)
    rc = cli.main(["scan", "--runtime"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CRITICAL PATH VIOLATIONS" in out
    assert "boto3" in out


def test_cli_load_manifesto_bad_spec_returns_none(
    tmp_path: Path, monkeypatch
) -> None:
    """Line 467: _load_manifesto with spec_from_file_location returning None."""
    import importlib.util as iu

    from sentinel.cli import _load_manifesto

    valid_file = tmp_path / "empty_module.py"
    valid_file.write_text("# empty\n")

    original = iu.spec_from_file_location

    def returns_none(*args, **kwargs):  # noqa: ARG001
        return None

    monkeypatch.setattr(iu, "spec_from_file_location", returns_none)
    try:
        result = _load_manifesto(f"{valid_file}:SomeClass")
        assert result is None
    finally:
        monkeypatch.setattr(iu, "spec_from_file_location", original)
