"""
tests/test_pilot_status.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit and CLI coverage for `sentinel status`.

Seeds a small SQLite trace DB directly so the tests do not depend on
the quickstart example (which exercises a different code path).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from sentinel import __version__, cli
from sentinel.dashboard import HTMLReport
from sentinel.pilot.config import (
    DEFAULT_PILOT_DIR,
    KillSwitchConfig,
    PilotConfig,
    default_pilot_paths,
    save_pilot_config,
)
from sentinel.pilot.render import render_status_text
from sentinel.pilot.status import (
    DecisionActivity,
    PilotStatus,
    compute_pilot_status,
    read_activity,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decision_traces (
                trace_id        TEXT PRIMARY KEY,
                parent_trace_id TEXT,
                project         TEXT NOT NULL DEFAULT 'default',
                agent           TEXT NOT NULL,
                started_at      TEXT NOT NULL,
                completed_at    TEXT,
                latency_ms      INTEGER,
                inputs_hash     TEXT,
                output_hash     TEXT,
                model_provider  TEXT,
                model_name      TEXT,
                policy_result   TEXT,
                data_residency  TEXT,
                sovereign_scope TEXT,
                storage_backend TEXT,
                schema_version  TEXT NOT NULL DEFAULT '1.0.0',
                payload         TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _insert_trace(
    db_path: Path,
    *,
    policy_result: str,
    started_at: datetime,
    override_by: str | None = None,
) -> None:
    payload = {
        "trace_id": str(uuid4()),
        "agent": "test",
        "policy_result": policy_result,
        "override_by": override_by,
    }
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO decision_traces
                (trace_id, agent, started_at, policy_result, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload["trace_id"],
                "test",
                started_at.isoformat(),
                policy_result,
                json.dumps(payload),
            ),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# read_activity — pure function over a SQLite file
# ---------------------------------------------------------------------------


def test_read_activity_missing_db_returns_zeros(tmp_path: Path) -> None:
    activity = read_activity(tmp_path / "nope.db")
    assert activity.total == 0
    assert activity.allow == 0
    assert activity.deny == 0
    assert activity.overrides == 0
    assert activity.window_days == 7


def test_read_activity_counts_allow_deny_exception_override(
    tmp_path: Path,
) -> None:
    db = tmp_path / "traces.db"
    _init_db(db)
    now = datetime.now(UTC)
    for _ in range(4):
        _insert_trace(db, policy_result="ALLOW", started_at=now)
    for _ in range(2):
        _insert_trace(db, policy_result="DENY", started_at=now)
    _insert_trace(db, policy_result="EXCEPTION_REQUIRED", started_at=now)
    _insert_trace(
        db, policy_result="ALLOW", started_at=now, override_by="alice"
    )

    activity = read_activity(db)
    assert activity.total == 8
    assert activity.allow == 5
    assert activity.deny == 2
    assert activity.exception == 1
    assert activity.overrides == 1


def test_read_activity_window_excludes_old_traces(tmp_path: Path) -> None:
    db = tmp_path / "traces.db"
    _init_db(db)
    now = datetime.now(UTC)
    _insert_trace(db, policy_result="ALLOW", started_at=now)
    _insert_trace(
        db, policy_result="ALLOW", started_at=now - timedelta(days=10)
    )

    activity = read_activity(db, window_days=7)
    assert activity.total == 1


def test_read_activity_ignores_non_sqlite_file(tmp_path: Path) -> None:
    bogus = tmp_path / "traces.db"
    bogus.write_text("not a database")
    activity = read_activity(bogus)
    assert activity.total == 0


def test_decision_activity_percentage_math() -> None:
    act = DecisionActivity(
        window_days=7, total=4, allow=3, deny=1, exception=0, overrides=0
    )
    assert act.allow_pct == 75
    assert act.deny_pct == 25

    blank = DecisionActivity(
        window_days=7, total=0, allow=0, deny=0, exception=0, overrides=0
    )
    assert blank.allow_pct == 0
    assert blank.deny_pct == 0


# ---------------------------------------------------------------------------
# compute_pilot_status — end-to-end composition
# ---------------------------------------------------------------------------


def test_compute_pilot_status_uninitialised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    status = compute_pilot_status(version="9.9.9")
    assert status.version == "9.9.9"
    assert status.storage_kind == "Not initialised"
    assert status.activity.total == 0
    assert status.audit_readiness == 0
    assert 0.0 <= status.sovereignty_score <= 1.0


def test_compute_pilot_status_with_config_and_traces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _, config_path, db_path = default_pilot_paths()
    save_pilot_config(
        PilotConfig(
            project="my-project",
            storage_path=str(db_path),
            kill_switch=KillSwitchConfig(registered=True),
        ),
        config_path,
    )
    _init_db(db_path)
    now = datetime.now(UTC)
    _insert_trace(db_path, policy_result="ALLOW", started_at=now)
    _insert_trace(db_path, policy_result="DENY", started_at=now)

    status = compute_pilot_status(version=__version__)
    assert status.project == "my-project"
    assert status.storage_kind == "SQLite (development)"
    assert status.activity.total == 2
    assert status.audit_readiness > 0


def test_compute_pilot_status_non_sqlite_storage_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-.db storage path renders as a generic 'Configured:' line."""
    monkeypatch.chdir(tmp_path)
    _, config_path, _ = default_pilot_paths()
    save_pilot_config(
        PilotConfig(project="x", storage_path="s3://bucket/traces"),
        config_path,
    )
    status = compute_pilot_status(version="3.1.0")
    assert status.storage_kind.startswith("Configured:")


def test_compute_pilot_status_tolerates_corrupt_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A corrupt trace DB must not crash `sentinel status`."""
    monkeypatch.chdir(tmp_path)
    _, _, db_path = default_pilot_paths()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text("not a database file")
    status = compute_pilot_status(version="3.1.0")
    assert status.activity.total == 0


def test_render_status_text_reports_exception_and_override_lines() -> None:
    """EXCEPTION and Override lines are rendered when non-zero."""
    status = PilotStatus(
        project="demo",
        version="3.1.0",
        storage_kind="SQLite (development)",
        storage_path="/tmp/x.db",
        activity=DecisionActivity(
            window_days=7, total=3, allow=1, deny=0, exception=1, overrides=1
        ),
        sovereignty_score=1.0,
        audit_readiness=40,
        days_to_enforcement=100,
        audit_report=compute_pilot_status(version="3.1.0").audit_report,
    )
    text = render_status_text(status)
    assert "EXCEPTION       1" in text
    assert "Override        1" in text


def test_render_status_text_post_enforcement_countdown() -> None:
    """Negative days_to_enforcement reads cleanly, not '-5 days'."""
    status = PilotStatus(
        project="demo",
        version="3.1.0",
        storage_kind="SQLite (development)",
        storage_path="/tmp/x.db",
        activity=DecisionActivity(
            window_days=7, total=0, allow=0, deny=0, exception=0, overrides=0
        ),
        sovereignty_score=1.0,
        audit_readiness=10,
        days_to_enforcement=-5,
        audit_report=compute_pilot_status(version="3.1.0").audit_report,
    )
    text = render_status_text(status)
    assert "EU AI Act is now enforced" in text


def test_compute_pilot_status_frozen_date() -> None:
    """days_to_enforcement uses the provided `now` deterministically."""
    frozen = datetime(2026, 4, 1, tzinfo=UTC)
    status = compute_pilot_status(version="9.9.9", now=frozen)
    assert status.days_to_enforcement == 123


# ---------------------------------------------------------------------------
# renderer
# ---------------------------------------------------------------------------


def test_render_status_text_fresh_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    status = compute_pilot_status(version="3.1.0")
    text = render_status_text(status)
    assert "Sentinel status" in text
    assert "Version           3.1.0" in text
    assert "no traces yet" in text
    assert "Run: sentinel audit-gap" in text


def test_render_status_text_includes_activity_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _, _, db_path = default_pilot_paths()
    _init_db(db_path)
    now = datetime.now(UTC)
    for _ in range(3):
        _insert_trace(db_path, policy_result="ALLOW", started_at=now)
    _insert_trace(db_path, policy_result="DENY", started_at=now)

    status = compute_pilot_status(version="3.1.0")
    text = render_status_text(status)
    assert "ALLOW           3" in text
    assert "DENY            1" in text


def test_render_status_text_production_ready_path() -> None:
    """When readiness ≥ 80 %, no nudge, no scary countdown."""
    status = PilotStatus(
        project="demo",
        version="3.1.0",
        storage_kind="SQLite (development)",
        storage_path="/tmp/x.db",
        activity=DecisionActivity(
            window_days=7, total=0, allow=0, deny=0, exception=0, overrides=0
        ),
        sovereignty_score=1.0,
        audit_readiness=90,
        days_to_enforcement=100,
        audit_report=compute_pilot_status(version="3.1.0").audit_report,
    )
    text = render_status_text(status)
    assert "Run: sentinel audit-gap" not in text
    assert "Production-ready" in text


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_status_text_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Sentinel status" in out
    assert "Audit readiness" in out


def test_cli_status_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["status", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == __version__
    assert payload["activity"]["total"] == 0
    assert 0 <= payload["audit_readiness"] <= 100


def test_cli_status_invalid_config_surfaces_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    pilot_dir = tmp_path / DEFAULT_PILOT_DIR
    pilot_dir.mkdir()
    (pilot_dir / "config.json").write_text("{ not json")
    rc = cli.main(["status"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "not valid JSON" in err


# ---------------------------------------------------------------------------
# HTML report commercial footer
# ---------------------------------------------------------------------------


def test_html_report_contains_commercial_footer() -> None:
    from sentinel import Sentinel

    sentinel = Sentinel(project="demo-project")
    html = HTMLReport().generate(sentinel)
    assert "sentinel@swentures.com" in html
    assert "commercial-footer" in html
    assert "BSI pre-certification" in html
    # Air-gapped invariant — no external http(s) references.
    assert 'href="http' not in html
    assert "src=\"http" not in html


# ---------------------------------------------------------------------------
# Demo `Next steps` surface audit-gap
# ---------------------------------------------------------------------------


def test_cli_demo_next_steps_surface_audit_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["demo", "--no-kill-switch"])
    assert rc == 0
    out = capsys.readouterr().out
    # audit-gap must lead the Next-steps block so new users find it first.
    idx_next = out.find("Next steps:")
    assert idx_next != -1
    nxt = out[idx_next:]
    assert "audit-gap" in nxt
    assert nxt.index("audit-gap") < nxt.index("attestation generate")
