"""CLI tests for the v3.4.1 additions.

- ``sentinel audit list / show / verify`` — brings the CLI to parity
  with the Trace/Attest/Audit/Comply canonical formula.
- ``sentinel comply export`` — canonical v3.4 alias for the legacy
  ``sentinel evidence-pack`` command.
- ``sentinel evidence-pack`` now emits a DeprecationWarning.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel import Sentinel, cli
from sentinel.storage import SQLiteStorage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def approve_request(ctx: dict) -> dict:  # noqa: RUF029
    """Module-level agent function so trace.agent captures a stable name."""
    return {"decision": "approved", "amount": ctx.get("amount", 0)}


@pytest.fixture
def traces_db(tmp_path: Path) -> Path:
    """Build a small SQLite database on disk with a few decision traces."""
    db_path = tmp_path / "traces.db"
    storage = SQLiteStorage(str(db_path))
    storage.initialise()
    sentinel_obj = Sentinel(
        storage=storage,
        project="audit-cli-test",
        signer=None,
    )
    traced = sentinel_obj.trace(approve_request)

    async def _populate() -> None:
        for i in range(5):
            await traced({"amount": (i + 1) * 100})

    asyncio.run(_populate())
    return db_path


def _first_trace_id(db: Path) -> str:
    storage = SQLiteStorage(str(db))
    storage.initialise()
    return storage.query(limit=1)[0].trace_id


# ---------------------------------------------------------------------------
# sentinel audit list
# ---------------------------------------------------------------------------


def test_audit_list_renders_table(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(["audit", "list", "--db", str(traces_db)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "TRACE ID" in out
    assert "approve_request" in out
    # 5 rows of data plus the header
    assert out.count("approve_request") == 5


def test_audit_list_filters_and_json(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(
        [
            "audit",
            "list",
            "--db",
            str(traces_db),
            "--agent",
            "approve_request",
            "--limit",
            "2",
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert isinstance(payload, list)
    assert len(payload) == 2
    assert all(t["agent"] == "approve_request" for t in payload)


def test_audit_list_empty_match(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(
        [
            "audit",
            "list",
            "--db",
            str(traces_db),
            "--agent",
            "nonexistent_agent",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "no traces matched" in out


def test_audit_list_invalid_iso(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(
        ["audit", "list", "--db", str(traces_db), "--since", "not-a-date"]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "invalid ISO date" in err


def test_audit_list_policy_result_filter(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # NullPolicyEvaluator leaves policy_evaluation as None → no
    # traces should match an explicit ALLOW filter.
    rc = cli.main(
        [
            "audit",
            "list",
            "--db",
            str(traces_db),
            "--policy-result",
            "ALLOW",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "no traces matched" in out


def test_audit_list_renders_policy_result_column(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When the traced function ran under a real policy evaluator,
    the RESULT column shows ALLOW/DENY rather than '?'."""
    from sentinel.policy.evaluator import SimpleRuleEvaluator

    db = tmp_path / "policy.db"
    storage = SQLiteStorage(str(db))
    storage.initialise()
    sentinel_obj = Sentinel(
        storage=storage,
        project="audit-cli-policy",
        policy_evaluator=SimpleRuleEvaluator(
            {"policies/allow.py": lambda _ctx: (True, None)}
        ),
        signer=None,
    )

    @sentinel_obj.trace(policy="policies/allow.py")
    async def allow_fn(ctx: dict) -> dict:  # noqa: RUF029
        return {"handled": True}

    asyncio.run(allow_fn({"x": 1}))

    rc = cli.main(["audit", "list", "--db", str(db)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ALLOW" in out


def test_audit_list_iso_date_windowing(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    rc = cli.main(
        ["audit", "list", "--db", str(traces_db), "--since", future]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "no traces matched" in out


# ---------------------------------------------------------------------------
# sentinel audit show
# ---------------------------------------------------------------------------


def test_audit_show_prints_full_json(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tid = _first_trace_id(traces_db)
    rc = cli.main(["audit", "show", tid, "--db", str(traces_db)])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["trace_id"] == tid
    assert payload["agent"] == "approve_request"


def test_audit_show_missing_trace(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(
        ["audit", "show", "does-not-exist", "--db", str(traces_db)]
    )
    err = capsys.readouterr().err
    assert rc == 1
    assert "no trace with id" in err


# ---------------------------------------------------------------------------
# sentinel audit verify
# ---------------------------------------------------------------------------


def test_audit_verify_passes_for_unmodified_trace(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tid = _first_trace_id(traces_db)
    rc = cli.main(["audit", "verify", tid, "--db", str(traces_db)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "verified" in out
    assert tid in out


def test_audit_verify_json_output(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tid = _first_trace_id(traces_db)
    rc = cli.main(
        ["audit", "verify", tid, "--db", str(traces_db), "--json"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["verified"] is True
    assert payload["trace_id"] == tid


def test_audit_verify_unknown_trace_exits_nonzero(
    traces_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(["audit", "verify", "no-such-id", "--db", str(traces_db)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "failed" in out or "not found" in out


def test_audit_no_subcommand_prints_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli.main(["audit"])
    capsys.readouterr()
    assert rc == 1


# ---------------------------------------------------------------------------
# sentinel comply export
# ---------------------------------------------------------------------------


def test_comply_export_writes_pdf(
    traces_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("reportlab")
    out_path = tmp_path / "pack.pdf"
    rc = cli.main(
        [
            "comply",
            "export",
            "--db",
            str(traces_db),
            "--output",
            str(out_path),
        ]
    )
    capsys.readouterr()
    assert rc == 0
    assert out_path.exists()
    assert out_path.read_bytes().startswith(b"%PDF-")


def test_comply_export_short_output_flag(
    traces_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``-o`` must be a valid short form for ``--output`` (the pre-v3.4
    `evidence-pack` command only accepted the long form)."""
    pytest.importorskip("reportlab")
    out_path = tmp_path / "pack_short.pdf"
    rc = cli.main(
        ["comply", "export", "--db", str(traces_db), "-o", str(out_path)]
    )
    capsys.readouterr()
    assert rc == 0
    assert out_path.exists()


# ---------------------------------------------------------------------------
# sentinel evidence-pack — backward-compat alias with DeprecationWarning
# ---------------------------------------------------------------------------


def test_evidence_pack_still_works(
    traces_db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("reportlab")
    out_path = tmp_path / "old_style.pdf"
    rc = cli.main(
        [
            "evidence-pack",
            "--db",
            str(traces_db),
            "--output",
            str(out_path),
        ]
    )
    capsys.readouterr()
    assert rc == 0
    assert out_path.exists()


def test_evidence_pack_emits_deprecation_warning(
    traces_db: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("reportlab")
    out_path = tmp_path / "warn.pdf"
    with pytest.warns(DeprecationWarning, match="comply export"):
        cli.main(
            [
                "evidence-pack",
                "--db",
                str(traces_db),
                "--output",
                str(out_path),
            ]
        )
    capsys.readouterr()
    assert out_path.exists()
