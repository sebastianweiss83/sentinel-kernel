"""
sentinel.pilot.status
~~~~~~~~~~~~~~~~~~~~~
Pilot status snapshot — fast, read-only view of a local pilot.

Answers three questions a first-time user has after a few days:
    1. Is Sentinel doing anything? (decision activity)
    2. Is my setup sovereign? (sovereignty score)
    3. Am I audit-ready? (gap score)

Design principles
-----------------
- **Read-only.** Never opens the DB for write, never creates it.
- **No network.** Pure inspection of ``./.sentinel/*`` plus the
  in-process sovereignty scanner.
- **Fast.** Budgets one SQLite roundtrip. Target: well under a second
  on a developer laptop.
- **Composable.** Returns a plain dataclass so tests can inspect the
  numbers without parsing rendered text.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sentinel.pilot.audit_gap import AuditGapReport, compute_audit_gap
from sentinel.pilot.config import (
    PilotConfig,
    default_pilot_paths,
    load_pilot_config,
)

EU_AI_ACT_ENFORCEMENT_DATE = date(2026, 8, 2)


@dataclass(frozen=True)
class DecisionActivity:
    """Counts of decisions over a rolling window."""

    window_days: int
    total: int
    allow: int
    deny: int
    exception: int
    overrides: int

    @property
    def allow_pct(self) -> int:
        return int(round(100 * self.allow / self.total)) if self.total else 0

    @property
    def deny_pct(self) -> int:
        return int(round(100 * self.deny / self.total)) if self.total else 0


@dataclass(frozen=True)
class PilotStatus:
    """Everything `sentinel status` needs to render."""

    project: str
    version: str
    storage_kind: str
    storage_path: str
    activity: DecisionActivity
    sovereignty_score: float  # 0.0..1.0
    audit_readiness: int  # 0..100
    days_to_enforcement: int
    audit_report: AuditGapReport

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "version": self.version,
            "storage_kind": self.storage_kind,
            "storage_path": self.storage_path,
            "activity": {
                "window_days": self.activity.window_days,
                "total": self.activity.total,
                "allow": self.activity.allow,
                "deny": self.activity.deny,
                "exception": self.activity.exception,
                "overrides": self.activity.overrides,
                "allow_pct": self.activity.allow_pct,
                "deny_pct": self.activity.deny_pct,
            },
            "sovereignty_score": self.sovereignty_score,
            "audit_readiness": self.audit_readiness,
            "days_to_enforcement": self.days_to_enforcement,
        }


def _blank_activity(window_days: int) -> DecisionActivity:
    return DecisionActivity(
        window_days=window_days,
        total=0,
        allow=0,
        deny=0,
        exception=0,
        overrides=0,
    )


def read_activity(
    db_path: Path, *, window_days: int = 7, now: datetime | None = None
) -> DecisionActivity:
    """
    Read decision activity from a SQLite trace DB.

    Uses a read-only connection so the function is safe on missing or
    empty databases — a fresh directory reports zeros rather than
    accidentally creating the database.
    """
    if not db_path.exists():
        return _blank_activity(window_days)

    cutoff = (now or datetime.now(UTC)) - timedelta(days=window_days)
    cutoff_iso = cutoff.isoformat()

    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*),
                    SUM(CASE WHEN policy_result = 'ALLOW' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN policy_result = 'DENY' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN policy_result = 'EXCEPTION_REQUIRED'
                             THEN 1 ELSE 0 END)
                FROM decision_traces
                WHERE started_at >= ?
                """,
                (cutoff_iso,),
            ).fetchone()
            total, allow, deny, exception = (int(v or 0) for v in row)

            overrides_row = conn.execute(
                """
                SELECT COUNT(*)
                FROM decision_traces
                WHERE started_at >= ?
                  AND payload LIKE '%"override_by":%'
                  AND payload NOT LIKE '%"override_by": null%'
                """,
                (cutoff_iso,),
            ).fetchone()
            overrides = int(overrides_row[0]) if overrides_row else 0
    except sqlite3.DatabaseError:
        return _blank_activity(window_days)

    return DecisionActivity(
        window_days=window_days,
        total=total,
        allow=allow,
        deny=deny,
        exception=exception,
        overrides=overrides,
    )


def _sovereignty_score() -> float:
    """Query the runtime scanner. Returns 1.0 if the scan fails."""
    try:
        from sentinel.scanner import RuntimeScanner

        return float(RuntimeScanner().scan().sovereignty_score)
    except Exception:  # pragma: no cover - defensive
        return 1.0


def _storage_kind(config: PilotConfig | None, db_path: Path) -> str:
    """Human-readable storage descriptor."""
    if config is not None and config.storage_path:
        suffix = Path(config.storage_path).suffix.lower()
        if suffix in (".db", ".sqlite", ".sqlite3"):
            return "SQLite (development)"
        return f"Configured: {config.storage_path}"
    if db_path.exists():
        return "SQLite (development)"
    return "Not initialised"


def _project_name(config: PilotConfig | None) -> str:
    if config is not None and config.project:
        return config.project
    return Path.cwd().name or "sentinel"


def compute_pilot_status(
    *,
    version: str,
    base: Path | str | None = None,
    now: datetime | None = None,
) -> PilotStatus:
    """
    Compose the full `sentinel status` snapshot.

    Deliberately tolerant of missing state — a user who has never run
    ``sentinel quickstart`` sees zeros everywhere, not errors. The
    audit-readiness number still computes honestly against an empty
    config.
    """
    _, config_path, db_path = default_pilot_paths(base)
    config = load_pilot_config(config_path)

    activity = read_activity(db_path, now=now)

    trace_count = 0
    if db_path.exists():
        try:
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                trace_count = int(
                    conn.execute(
                        "SELECT COUNT(*) FROM decision_traces"
                    ).fetchone()[0]
                )
        except sqlite3.DatabaseError:
            trace_count = 0

    storage_path = (
        config.storage_path if config and config.storage_path else str(db_path)
    )
    audit_report = compute_audit_gap(
        config=config,
        trace_count=trace_count,
        storage_path=storage_path,
    )

    today = (now.date() if now else date.today())
    days_to = (EU_AI_ACT_ENFORCEMENT_DATE - today).days

    return PilotStatus(
        project=_project_name(config),
        version=version,
        storage_kind=_storage_kind(config, db_path),
        storage_path=storage_path,
        activity=activity,
        sovereignty_score=_sovereignty_score(),
        audit_readiness=audit_report.score,
        days_to_enforcement=days_to,
        audit_report=audit_report,
    )
