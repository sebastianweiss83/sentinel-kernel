"""
tests/test_pilot.py
~~~~~~~~~~~~~~~~~~~
Unit and CLI coverage for the self-serve pilot surface.

These tests cover quickstart, audit-gap, and the two fix commands
end-to-end. All tests run offline and use ``tmp_path`` / monkeypatch
to stay hermetic.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from sentinel import cli
from sentinel.pilot.audit_gap import (
    CATEGORIES,
    TOTAL_WEIGHT,
    GapCategory,
    compute_audit_gap,
)
from sentinel.pilot.config import (
    DEFAULT_CONFIG_FILENAME,
    DEFAULT_PILOT_DIR,
    KillSwitchConfig,
    PilotConfig,
    RetentionConfig,
    SigningConfig,
    default_pilot_paths,
    load_pilot_config,
    save_pilot_config,
)
from sentinel.pilot.fixes import fix_kill_switch, fix_retention
from sentinel.pilot.quickstart import EXAMPLE_FILENAME, run_quickstart
from sentinel.pilot.render import render_audit_gap_text

# ---------------------------------------------------------------------------
# PilotConfig round-trip
# ---------------------------------------------------------------------------


def test_pilot_config_round_trip(tmp_path: Path) -> None:
    cfg = PilotConfig(
        project="test",
        storage_path="./.sentinel/traces.db",
        data_residency="EU_DE",
        sovereign_scope="EU",
        kill_switch=KillSwitchConfig(registered=True, handler_path="/tmp/ks.py"),
        retention=RetentionConfig(days=2555, policy_name="default"),
        signing=SigningConfig(key_type="long_lived", key_path="/tmp/k.key"),
        annex_iv_doc_path="/tmp/annex_iv.md",
        production_backend=True,
    )
    path = tmp_path / "config.json"
    save_pilot_config(cfg, path)
    loaded = load_pilot_config(path)
    assert loaded is not None
    assert loaded.project == "test"
    assert loaded.kill_switch.registered is True
    assert loaded.retention.days == 2555
    assert loaded.signing.key_type == "long_lived"
    assert loaded.annex_iv_doc_path == "/tmp/annex_iv.md"
    assert loaded.production_backend is True
    # Round-trip preserves created_at/updated_at
    assert loaded.created_at != ""
    assert loaded.updated_at != ""


def test_pilot_config_load_missing_returns_none(tmp_path: Path) -> None:
    assert load_pilot_config(tmp_path / "missing.json") is None


def test_pilot_config_load_invalid_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_pilot_config(bad)


def test_pilot_config_preserves_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    raw = {
        "schema_version": "1.0",
        "project": "fwd-compat",
        "some_future_key": {"enabled": True},
    }
    path.write_text(json.dumps(raw))
    loaded = load_pilot_config(path)
    assert loaded is not None
    assert "some_future_key" in loaded.extra


# ---------------------------------------------------------------------------
# compute_audit_gap — the scoring engine
# ---------------------------------------------------------------------------


def test_categories_sum_to_100() -> None:
    assert TOTAL_WEIGHT == 100
    assert sum(c.weight for c in CATEGORIES) == 100


def test_audit_gap_empty_pilot_scores_zero() -> None:
    report = compute_audit_gap(
        config=None,
        trace_count=0,
        storage_path="./.sentinel/traces.db",
    )
    assert report.score == 0
    # All library items missing => every library category is a gap
    assert len(report.library_gaps) >= 5
    assert report.config_present is False


def test_audit_gap_fresh_quickstart_scores_in_the_60s() -> None:
    """
    After quickstart + 10 traces, a new user should land around 60 %.
    The exact value depends on weighting but the design target is
    "high enough to feel like progress, low enough to still feel
    unfinished." Anything outside 55..70 means the weighting drifted.
    """
    cfg = PilotConfig(
        project="sentinel-pilot",
        storage_path="./.sentinel/traces.db",
        data_residency="EU_DE",
        sovereign_scope="EU",
    )
    report = compute_audit_gap(
        config=cfg,
        trace_count=10,
        storage_path="./.sentinel/traces.db",
    )
    assert 55 <= report.score <= 70, f"score drifted to {report.score}"
    # Library fixes still open
    library_fix_keys = {g.key for g in report.library_gaps}
    assert "art14_kill_switch" in library_fix_keys
    assert "retention_policy" in library_fix_keys
    # Deployment + organisational gaps present
    assert len(report.deployment_gaps) >= 1
    assert len(report.organisational_gaps) >= 1


def test_audit_gap_after_library_fixes_scores_higher() -> None:
    base = PilotConfig(
        project="sentinel-pilot",
        storage_path="./.sentinel/traces.db",
        data_residency="EU_DE",
        sovereign_scope="EU",
    )
    base_report = compute_audit_gap(
        config=base,
        trace_count=10,
        storage_path="./.sentinel/traces.db",
    )

    fixed = replace(
        base,
        kill_switch=KillSwitchConfig(registered=True),
        retention=RetentionConfig(days=2555, policy_name="default"),
    )
    fixed_report = compute_audit_gap(
        config=fixed,
        trace_count=10,
        storage_path="./.sentinel/traces.db",
    )
    assert fixed_report.score == base_report.score + 20
    # The two library gaps are now closed
    remaining_library = {g.key for g in fixed_report.library_gaps}
    assert "art14_kill_switch" not in remaining_library
    assert "retention_policy" not in remaining_library


def test_audit_gap_remote_backend_misses_offline_points() -> None:
    cfg = PilotConfig(
        project="p",
        storage_path="s3://bucket/traces",
        data_residency="EU_DE",
        sovereign_scope="EU",
    )
    report = compute_audit_gap(
        config=cfg,
        trace_count=10,
        storage_path="s3://bucket/traces",
    )
    offline_items = [i for i in report.items if i.key == "offline_verified"]
    assert offline_items[0].status == "missing"
    assert offline_items[0].points_awarded == 0


def test_audit_gap_production_backend_flag_awards_points() -> None:
    cfg = PilotConfig(
        project="p",
        storage_path="/var/lib/sentinel/traces.db",
        data_residency="EU_DE",
        sovereign_scope="EU",
        production_backend=True,
    )
    report = compute_audit_gap(
        config=cfg,
        trace_count=10,
        storage_path="/var/lib/sentinel/traces.db",
    )
    prod_items = [i for i in report.items if i.key == "production_backend"]
    assert prod_items[0].status == "complete"
    assert prod_items[0].points_awarded == 5


def test_audit_gap_annex_iv_doc_existing_awards_points(tmp_path: Path) -> None:
    annex = tmp_path / "annex_iv.md"
    annex.write_text("# Annex IV")
    cfg = PilotConfig(
        project="p",
        sovereign_scope="EU",
        data_residency="EU_DE",
        annex_iv_doc_path=str(annex),
    )
    report = compute_audit_gap(
        config=cfg,
        trace_count=10,
        storage_path="./.sentinel/traces.db",
    )
    annex_items = [i for i in report.items if i.key == "annex_iv_documentation"]
    assert annex_items[0].status == "complete"


def test_audit_gap_annex_iv_missing_file_stays_gap(tmp_path: Path) -> None:
    cfg = PilotConfig(
        project="p",
        sovereign_scope="EU",
        data_residency="EU_DE",
        annex_iv_doc_path=str(tmp_path / "does-not-exist.md"),
    )
    report = compute_audit_gap(
        config=cfg,
        trace_count=10,
        storage_path="./.sentinel/traces.db",
    )
    annex_items = [i for i in report.items if i.key == "annex_iv_documentation"]
    assert annex_items[0].status == "missing"
    assert "missing" in annex_items[0].detail


def test_audit_gap_score_never_exceeds_100() -> None:
    cfg = PilotConfig(
        project="max",
        storage_path="/var/lib/sentinel/traces.db",
        data_residency="EU_DE",
        sovereign_scope="EU",
        kill_switch=KillSwitchConfig(registered=True),
        retention=RetentionConfig(days=2555),
        signing=SigningConfig(key_type="long_lived", key_path="/k.key"),
        annex_iv_doc_path=None,  # will still be a gap
        production_backend=True,
    )
    report = compute_audit_gap(
        config=cfg,
        trace_count=100,
        storage_path="/var/lib/sentinel/traces.db",
    )
    assert 0 <= report.score <= 100


def test_render_audit_gap_text_contains_conversion_trigger() -> None:
    cfg = PilotConfig(
        project="p",
        sovereign_scope="EU",
        data_residency="EU_DE",
    )
    report = compute_audit_gap(
        config=cfg,
        trace_count=5,
        storage_path="./.sentinel/traces.db",
    )
    text = render_audit_gap_text(report)
    assert "Audit readiness" in text
    assert "github.com/sebastianweiss83/sentinel-kernel" in text
    assert "pilot enquiry" in text.lower()
    assert "Or close the gaps yourself" in text


# ---------------------------------------------------------------------------
# quickstart — scaffolds and is idempotent
# ---------------------------------------------------------------------------


def test_quickstart_creates_scaffold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = run_quickstart()
    assert result.config_was_created is True
    assert result.example_was_created is True
    assert result.pilot_dir == (tmp_path / DEFAULT_PILOT_DIR).resolve()
    assert result.config_path == (tmp_path / DEFAULT_PILOT_DIR / DEFAULT_CONFIG_FILENAME).resolve()
    assert result.example_path == (tmp_path / EXAMPLE_FILENAME).resolve()
    # Files actually exist
    assert result.pilot_dir.exists()
    assert result.config_path.exists()
    assert result.example_path.exists()
    # Example file is runnable Python with the decorator we promised
    example_src = result.example_path.read_text()
    assert "from sentinel import" in example_src
    assert "@sentinel.trace" in example_src
    assert "approve_expense" in example_src


def test_quickstart_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    run_quickstart()
    second = run_quickstart()
    assert second.already_initialized is True
    assert second.config_was_created is False
    assert second.example_was_created is False
    assert second.example_was_overwritten is False


def test_quickstart_force_overwrites_example(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    run_quickstart()
    (tmp_path / EXAMPLE_FILENAME).write_text("# user edits")
    second = run_quickstart(force=True)
    assert second.example_was_overwritten is True
    content = (tmp_path / EXAMPLE_FILENAME).read_text()
    assert "@sentinel.trace" in content


def _run_example_in_cwd(tmp_path: Path) -> None:
    """
    Import, execute, and explicitly close the generated example's
    Sentinel instance. Closing avoids ResourceWarning noise from the
    SQLite connection that stays open until GC collects the module.
    """
    import importlib.util
    import sys as _sys

    example = tmp_path / EXAMPLE_FILENAME
    spec = importlib.util.spec_from_file_location("hello_sentinel_under_test", example)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        if hasattr(module, "approve_expense"):
            for amount in [120, 450, 1500]:
                module.approve_expense(amount=amount, category="travel")
    finally:
        sentinel_obj = getattr(module, "sentinel", None)
        if sentinel_obj is not None:
            storage = getattr(sentinel_obj, "storage", None)
            close = getattr(storage, "close", None)
            if callable(close):
                close()
        _sys.modules.pop("hello_sentinel_under_test", None)


def test_generated_example_runs_and_traces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    The scaffolded example file must actually work: running it
    produces traces in the pilot DB. This is the golden-path
    invariant — if this breaks, the wow moment breaks.
    """
    monkeypatch.chdir(tmp_path)
    run_quickstart()
    _run_example_in_cwd(tmp_path)

    _, _, db_path = default_pilot_paths()
    assert db_path.exists()
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM decision_traces").fetchone()[0]
    assert count >= 3


# ---------------------------------------------------------------------------
# fix commands — idempotent and update audit-gap score
# ---------------------------------------------------------------------------


def test_fix_kill_switch_writes_handler_and_updates_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = fix_kill_switch()
    assert result.succeeded is True
    assert result.points_delta == 10
    assert result.artefact_path is not None
    assert result.artefact_path.exists()
    cfg = load_pilot_config()
    assert cfg is not None
    assert cfg.kill_switch.registered is True


def test_fix_kill_switch_second_run_awards_no_points(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    fix_kill_switch()
    second = fix_kill_switch()
    assert second.succeeded is True
    assert second.points_delta == 0


def test_fix_retention_writes_days(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = fix_retention(days=2555)
    assert result.succeeded is True
    assert result.points_delta == 10
    cfg = load_pilot_config()
    assert cfg is not None
    assert cfg.retention.days == 2555


def test_fix_retention_rejects_zero_or_negative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = fix_retention(days=0)
    assert result.succeeded is False
    assert result.points_delta == 0


def test_fix_retention_second_run_awards_no_points(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    fix_retention(days=2555)
    second = fix_retention(days=2555)
    assert second.succeeded is True
    assert second.points_delta == 0


# ---------------------------------------------------------------------------
# CLI end-to-end — the full golden path
# ---------------------------------------------------------------------------


def test_cli_quickstart_writes_scaffold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["quickstart"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Sentinel quickstart" in out
    assert EXAMPLE_FILENAME in out
    assert "Next" in out
    assert (tmp_path / EXAMPLE_FILENAME).exists()
    assert (tmp_path / DEFAULT_PILOT_DIR / DEFAULT_CONFIG_FILENAME).exists()


def test_cli_quickstart_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    cli.main(["quickstart"])
    capsys.readouterr()  # drain
    rc = cli.main(["quickstart"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Already initialised" in out


def test_cli_audit_gap_on_empty_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["audit-gap"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Audit readiness" in out
    assert "github.com/sebastianweiss83/sentinel-kernel" in out
    # No config, no traces => score is 0
    assert "0 %" in out


def test_cli_audit_gap_after_quickstart_and_traces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    cli.main(["quickstart"])
    capsys.readouterr()
    _run_example_in_cwd(tmp_path)

    rc = cli.main(["audit-gap"])
    assert rc == 0
    out = capsys.readouterr().out
    # Score is in the "real progress" band
    assert "Audit readiness" in out
    # Extract just the score line to assert numerically
    score_line = [ln for ln in out.splitlines() if "Audit readiness" in ln][0]
    # " ... 62 %" (or similar two-digit value)
    import re
    match = re.search(r"(\d+)\s*%", score_line)
    assert match is not None
    score = int(match.group(1))
    assert 55 <= score <= 70
    # Conversion trigger present (tracked-on-GitHub intake)
    assert "pilot enquiry" in out.lower()


def test_cli_audit_gap_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    cli.main(["quickstart"])
    capsys.readouterr()
    rc = cli.main(["audit-gap", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "score" in payload
    assert "items" in payload
    assert "gaps" in payload
    assert "library" in payload["gaps"]
    assert "github.com/sebastianweiss83/sentinel-kernel" in payload["contact"]["url"]
    assert "pilot" in payload["contact"]["url"].lower()


def test_cli_fix_kill_switch_moves_score(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    cli.main(["quickstart"])
    capsys.readouterr()

    # Baseline score
    cli.main(["audit-gap", "--json"])
    baseline = json.loads(capsys.readouterr().out)["score"]

    # Apply fix
    rc = cli.main(["fix", "kill-switch"])
    assert rc == 0
    fix_out = capsys.readouterr().out
    assert "audit-gap" in fix_out
    assert "+10" in fix_out

    # New score
    cli.main(["audit-gap", "--json"])
    after = json.loads(capsys.readouterr().out)["score"]
    assert after == baseline + 10


def test_cli_fix_retention_moves_score(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    cli.main(["quickstart"])
    capsys.readouterr()
    cli.main(["audit-gap", "--json"])
    baseline = json.loads(capsys.readouterr().out)["score"]

    rc = cli.main(["fix", "retention", "--days", "2555"])
    assert rc == 0
    capsys.readouterr()

    cli.main(["audit-gap", "--json"])
    after = json.loads(capsys.readouterr().out)["score"]
    assert after == baseline + 10


def test_cli_fix_rejects_bad_subcommand(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["fix"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "kill-switch" in out
    assert "retention" in out


def test_cli_fix_retention_rejects_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["fix", "retention", "--days", "0"])
    assert rc == 1


def test_cli_fix_kill_switch_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["fix", "kill-switch", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["fix_id"] == "kill_switch"
    assert payload["succeeded"] is True
    assert payload["points_delta"] == 10
    assert payload["artefact_path"] is not None
    assert payload["config_path"] is not None


def test_cli_fix_retention_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["fix", "retention", "--json", "--days", "2555"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["fix_id"] == "retention"
    assert payload["succeeded"] is True
    assert payload["points_delta"] == 10
    assert payload["config_path"] is not None


def test_cli_fix_retention_json_rejects_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["fix", "retention", "--json", "--days", "0"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["succeeded"] is False


def test_resolve_evidence_pack_db_uses_pilot_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    run_quickstart()
    _run_example_in_cwd(tmp_path)
    resolved = cli._resolve_evidence_pack_db(None)
    _, _, db_path = default_pilot_paths()
    assert resolved == str(db_path)


def test_resolve_evidence_pack_db_honours_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli._resolve_evidence_pack_db("/tmp/explicit.db") == "/tmp/explicit.db"


def test_resolve_evidence_pack_db_falls_back_to_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli._resolve_evidence_pack_db(None) == ":memory:"


def test_resolve_evidence_pack_output_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    resolved = cli._resolve_evidence_pack_output(None)
    assert resolved == tmp_path / "audit.pdf"


def test_resolve_evidence_pack_output_honours_explicit(
    tmp_path: Path,
) -> None:
    explicit = tmp_path / "custom.pdf"
    resolved = cli._resolve_evidence_pack_output(str(explicit))
    assert resolved == explicit


def test_render_audit_gap_no_gaps_branch() -> None:
    """
    Render path for a fully-closed pilot — exercises the "(none)"
    branches in render.py so the report handles the happy end-state.
    """
    from sentinel.pilot.audit_gap import AuditGapReport, GapItem
    from sentinel.pilot.render import render_audit_gap_text

    complete_items = tuple(
        GapItem(
            key=c.key,
            label=c.label,
            status="complete",
            detail="ok",
            weight=c.weight,
            points_awarded=c.weight,
            bucket=c.bucket,
            fix_hint=c.fix_hint,
            article_ref=c.article_ref,
        )
        for c in CATEGORIES
    )
    report = AuditGapReport(
        score=100,
        items=complete_items,
        trace_count=1,
        config_present=True,
        storage_path="/var/lib/sentinel/traces.db",
    )
    text = render_audit_gap_text(report)
    # All three "(none)" buckets should be rendered
    assert text.count("(none)") == 3
    assert "100 %" in text


def test_render_audit_gap_partial_status_mark() -> None:
    """Partial-status items render with the '~' mark."""
    from sentinel.pilot.audit_gap import AuditGapReport, GapItem
    from sentinel.pilot.render import render_audit_gap_text

    partial = GapItem(
        key="art12_logging",
        label="Art. 12   Automatic logging",
        status="partial",
        detail="some traces",
        weight=20,
        points_awarded=10,
        bucket=GapCategory.LIBRARY,
        fix_hint=None,
        article_ref="Art. 12",
    )
    report = AuditGapReport(
        score=10,
        items=(partial,),
        trace_count=1,
        config_present=True,
        storage_path="./.sentinel/traces.db",
    )
    text = render_audit_gap_text(report)
    assert " ~  " in text or "~  Art. 12" in text


def test_cli_audit_gap_invalid_config_file_surfaces_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    pilot_dir = tmp_path / DEFAULT_PILOT_DIR
    pilot_dir.mkdir()
    (pilot_dir / DEFAULT_CONFIG_FILENAME).write_text("{ not json")
    rc = cli.main(["audit-gap"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "not valid JSON" in err
