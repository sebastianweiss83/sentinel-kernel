"""
tests/test_verify_purge.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for trace integrity verification and retention purge.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.storage import SQLiteStorage


def _sentinel(tmp_path: Path) -> Sentinel:
    return Sentinel(
        storage=SQLiteStorage(str(tmp_path / "verify.db")),
        project="verify-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )


# ---------------------------------------------------------------------------
# verify_integrity
# ---------------------------------------------------------------------------


def test_verify_integrity_trace_not_found(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    result = sentinel.verify_integrity("does-not-exist")
    assert result.verified is False
    assert result.found is False
    assert "not found" in result.detail


def test_verify_integrity_clean_trace_passes(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"result": x * 2}

    agent(x=1)
    trace = sentinel.query(limit=1)[0]
    result = sentinel.verify_integrity(trace.trace_id)
    assert result.verified is True
    assert result.found is True
    assert result.inputs_match is True
    assert result.output_match is True


def test_verify_integrity_detects_tampered_inputs_hash(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"y": x}

    agent(x=42)
    trace = sentinel.query(limit=1)[0]

    # Tamper with the stored trace by directly rewriting its payload
    import json as _json
    conn = sentinel.storage._connection()  # type: ignore[attr-defined]
    row = conn.execute(
        "SELECT payload FROM decision_traces WHERE trace_id = ?",
        (trace.trace_id,),
    ).fetchone()
    data = _json.loads(row["payload"])
    data["inputs"] = {"x": 999}  # changed inputs — hash no longer matches
    conn.execute(
        "UPDATE decision_traces SET payload = ? WHERE trace_id = ?",
        (_json.dumps(data), trace.trace_id),
    )
    conn.commit()

    result = sentinel.verify_integrity(trace.trace_id)
    assert result.verified is False
    assert result.inputs_match is False
    assert "inputs_hash" in result.detail


def test_verify_integrity_detects_tampered_output_hash(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"y": x}

    agent(x=1)
    trace = sentinel.query(limit=1)[0]

    import json as _json
    conn = sentinel.storage._connection()  # type: ignore[attr-defined]
    row = conn.execute(
        "SELECT payload FROM decision_traces WHERE trace_id = ?",
        (trace.trace_id,),
    ).fetchone()
    data = _json.loads(row["payload"])
    data["output"] = {"y": 999}
    conn.execute(
        "UPDATE decision_traces SET payload = ? WHERE trace_id = ?",
        (_json.dumps(data), trace.trace_id),
    )
    conn.commit()

    result = sentinel.verify_integrity(trace.trace_id)
    assert result.verified is False
    assert result.output_match is False


def test_integrity_result_to_dict() -> None:
    from sentinel import IntegrityResult

    r = IntegrityResult(
        verified=True,
        trace_id="t1",
        found=True,
        inputs_match=True,
        output_match=True,
        detail="ok",
    )
    d = r.to_dict()
    assert d["verified"] is True
    assert d["trace_id"] == "t1"


# ---------------------------------------------------------------------------
# purge_before
# ---------------------------------------------------------------------------


def test_purge_dry_run_counts_but_does_not_delete(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    for i in range(5):
        agent(x=i)

    future_cutoff = datetime.now(UTC) + timedelta(days=1)
    result = sentinel.storage.purge_before(future_cutoff, dry_run=True)
    assert result.dry_run is True
    assert result.traces_affected == 5
    # Nothing actually deleted
    assert len(sentinel.query(limit=100)) == 5


def test_purge_actually_deletes(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    for i in range(4):
        agent(x=i)

    future_cutoff = datetime.now(UTC) + timedelta(days=1)
    result = sentinel.storage.purge_before(future_cutoff, dry_run=False)
    assert result.dry_run is False
    assert result.traces_affected == 4
    assert len(sentinel.query(limit=100)) == 0
    assert result.oldest_remaining is None


def test_purge_past_cutoff_keeps_everything(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    for i in range(3):
        agent(x=i)

    past_cutoff = datetime.now(UTC) - timedelta(days=10)
    result = sentinel.storage.purge_before(past_cutoff, dry_run=False)
    assert result.traces_affected == 0
    assert result.oldest_remaining is not None
    assert len(sentinel.query(limit=100)) == 3


def test_purge_empty_trace_ids_is_noop(tmp_path: Path) -> None:
    """Lines 173-175: _delete_traces early return on empty list."""
    sentinel = _sentinel(tmp_path)
    sentinel.storage._delete_traces([])  # type: ignore[attr-defined]
    # No exception means success


def test_purge_result_to_dict() -> None:
    from sentinel.storage.base import PurgeResult

    now = datetime.now(UTC)
    result = PurgeResult(traces_affected=5, oldest_remaining=now, dry_run=True)
    d = result.to_dict()
    assert d["traces_affected"] == 5
    assert d["dry_run"] is True
    assert now.isoformat() in d["oldest_remaining"]

    result_empty = PurgeResult(traces_affected=0, oldest_remaining=None, dry_run=False)
    assert result_empty.to_dict()["oldest_remaining"] is None


def test_purge_base_class_raises_for_backend_without_delete(tmp_path: Path) -> None:
    """NotImplementedError path in StorageBackend._delete_traces."""
    from sentinel.storage.filesystem import FilesystemStorage

    storage = FilesystemStorage(str(tmp_path / "fs-no-delete"))
    with pytest.raises(NotImplementedError):
        storage._delete_traces(["t1"])


# ---------------------------------------------------------------------------
# CLI verify + purge
# ---------------------------------------------------------------------------


def test_cli_verify_all_command(tmp_path: Path, capsys) -> None:
    from sentinel import cli

    db = tmp_path / "verify-cli.db"
    sentinel = Sentinel(storage=SQLiteStorage(str(db)), project="verify-cli-test")

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    for i in range(3):
        agent(x=i)

    rc = cli.main(["verify", "--all", "--db", str(db)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Verified: 3 / 3" in out


def test_cli_verify_trace_id(tmp_path: Path, capsys) -> None:
    from sentinel import cli

    db = tmp_path / "verify-single.db"
    sentinel = Sentinel(storage=SQLiteStorage(str(db)), project="verify-single")

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    agent(x=1)
    trace_id = sentinel.query(limit=1)[0].trace_id

    rc = cli.main(["verify", "--trace-id", trace_id, "--db", str(db)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Verified: 1 / 1" in out


def test_cli_verify_json_output(tmp_path: Path, capsys) -> None:
    import json as _json

    from sentinel import cli

    db = tmp_path / "verify-json.db"
    sentinel = Sentinel(storage=SQLiteStorage(str(db)), project="verify-json")

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    agent(x=1)

    rc = cli.main(["verify", "--all", "--db", str(db), "--json"])
    assert rc == 0
    data = _json.loads(capsys.readouterr().out)
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["failed"] == 0


def test_cli_verify_without_args_fails(tmp_path: Path, capsys) -> None:
    from sentinel import cli

    rc = cli.main(["verify", "--db", str(tmp_path / "x.db")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "must pass" in err


def test_cli_purge_dry_run(tmp_path: Path, capsys) -> None:
    from sentinel import cli

    db = tmp_path / "purge.db"
    sentinel = Sentinel(storage=SQLiteStorage(str(db)), project="purge-test")

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    for i in range(3):
        agent(x=i)

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    rc = cli.main(["purge", "--before", future, "--dry-run", "--db", str(db)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "3 traces" in out


def test_cli_purge_reports_oldest_remaining(tmp_path: Path, capsys) -> None:
    """Cover the 'Oldest remaining' output line when traces remain after purge."""
    from sentinel import cli

    db = tmp_path / "purge-partial.db"
    sentinel = Sentinel(storage=SQLiteStorage(str(db)), project="purge-partial")

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    agent(x=1)

    # Use a cutoff in the distant past so nothing matches — all traces
    # remain, and oldest_remaining is emitted.
    past = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    rc = cli.main(["purge", "--before", past, "--yes", "--db", str(db)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Oldest remaining" in out


def test_cli_purge_with_yes_deletes(tmp_path: Path, capsys) -> None:
    from sentinel import cli

    db = tmp_path / "purge2.db"
    sentinel = Sentinel(storage=SQLiteStorage(str(db)), project="purge2")

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    for i in range(2):
        agent(x=i)

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    rc = cli.main(["purge", "--before", future, "--yes", "--db", str(db)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Purged 2 traces" in out


def test_cli_verify_fails_on_tampered_trace(tmp_path: Path, capsys) -> None:
    from sentinel import cli

    db = tmp_path / "tampered.db"
    sentinel = Sentinel(storage=SQLiteStorage(str(db)), project="tampered")

    @sentinel.trace
    def agent(x: int) -> dict:
        return {"x": x}

    agent(x=1)
    trace_id = sentinel.query(limit=1)[0].trace_id

    # Tamper
    import json as _json
    conn = sentinel.storage._connection()  # type: ignore[attr-defined]
    row = conn.execute(
        "SELECT payload FROM decision_traces WHERE trace_id = ?",
        (trace_id,),
    ).fetchone()
    data = _json.loads(row["payload"])
    data["output"] = {"x": "tampered"}
    conn.execute(
        "UPDATE decision_traces SET payload = ? WHERE trace_id = ?",
        (_json.dumps(data), trace_id),
    )
    conn.commit()

    rc = cli.main(["verify", "--all", "--db", str(db)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
