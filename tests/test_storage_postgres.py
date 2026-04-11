"""
tests/test_storage_postgres.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for PostgresStorage using a fake psycopg2-style connection.
No real PostgreSQL required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sentinel import DataResidency, PolicyResult, Sentinel
from sentinel.core.trace import DecisionTrace, PolicyEvaluation
from sentinel.storage.postgres import PostgresStorage


class FakeCursor:
    def __init__(self, store: FakePgConnection) -> None:
        self._store = store
        self._result: list[tuple[Any, ...]] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self._store.executed.append((sql, list(params) if params else []))
        s = sql.strip().upper()
        if s.startswith("CREATE TABLE") or "CREATE INDEX" in s:
            return
        if s.startswith("INSERT"):
            assert params is not None
            (
                trace_id,
                parent_trace_id,
                project,
                agent,
                started_at,
                completed_at,
                latency_ms,
                inputs_hash,
                output_hash,
                model_provider,
                model_name,
                policy_result,
                data_residency,
                sovereign_scope,
                storage_backend,
                schema_version,
                payload,
            ) = params
            row = {
                "trace_id": trace_id,
                "project": project,
                "agent": agent,
                "started_at": started_at,
                "policy_result": policy_result,
                "payload": payload,
            }
            self._store.rows.append(row)
            return
        if s.startswith("SELECT PAYLOAD FROM DECISION_TRACES WHERE TRACE_ID"):
            assert params is not None
            trace_id = params[0]
            self._result = [
                (r["payload"],) for r in self._store.rows if r["trace_id"] == trace_id
            ]
            return
        if s.startswith("SELECT PAYLOAD FROM DECISION_TRACES"):
            rows = list(self._store.rows)
            # handle ORDER BY started_at (asc for export, desc for query)
            if "ORDER BY STARTED_AT DESC" in s:
                rows = sorted(rows, key=lambda r: r["started_at"], reverse=True)
            else:
                rows = sorted(rows, key=lambda r: r["started_at"])

            params = params or []
            # Apply filters based on WHERE clause captured in the SQL text
            conditions_sql = s.split("FROM DECISION_TRACES", 1)[1]
            filter_params = list(params[:-2]) if "LIMIT" in s else list(params)
            limit_params = list(params[-2:]) if "LIMIT" in s else []

            idx = 0
            if "PROJECT = %S" in conditions_sql:
                val = filter_params[idx]
                idx += 1
                rows = [r for r in rows if r["project"] == val]
            if "AGENT = %S" in conditions_sql:
                val = filter_params[idx]
                idx += 1
                rows = [r for r in rows if r["agent"] == val]
            if "POLICY_RESULT = %S" in conditions_sql:
                val = filter_params[idx]
                idx += 1
                rows = [r for r in rows if r["policy_result"] == val]

            if limit_params:
                limit, offset = limit_params
                rows = rows[offset : offset + limit]

            self._result = [(r["payload"],) for r in rows]
            return
        raise AssertionError(f"unexpected SQL: {sql}")

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._result

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._result[0] if self._result else None


class FakePgConnection:
    """Minimal psycopg2-style connection for tests."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.executed: list[tuple[str, list[Any]]] = []
        self.commits = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closed = True


def _fake_connect_factory() -> tuple[FakePgConnection, Any]:
    conn = FakePgConnection()

    def connect(dsn: str) -> FakePgConnection:
        return conn

    return conn, connect


def _make_sample_trace(agent: str = "approver", result: PolicyResult = PolicyResult.ALLOW) -> DecisionTrace:
    trace = DecisionTrace(
        project="pg-test",
        agent=agent,
        inputs={"amount": 100},
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        storage_backend="postgres",
    )
    trace.policy_evaluation = PolicyEvaluation(
        policy_id="policies/approve.py",
        policy_version="v1",
        result=result,
        rule_triggered=None if result == PolicyResult.ALLOW else "over_cap",
    )
    trace.complete(output={"decision": result.value}, latency_ms=2)
    return trace


def test_postgres_storage_write_trace() -> None:
    fake, connect = _fake_connect_factory()
    storage = PostgresStorage("postgresql://fake/db", connect_fn=connect)
    storage.initialise()

    trace = _make_sample_trace()
    storage.save(trace)

    fetched = storage.get(trace.trace_id)
    assert fetched is not None
    assert fetched.trace_id == trace.trace_id
    assert fetched.agent == "approver"
    assert fake.commits >= 2  # initialise + save


def test_postgres_storage_append_only() -> None:
    """Verify no UPDATE or DELETE SQL ever issued, and backend has no such API."""
    fake, connect = _fake_connect_factory()
    storage = PostgresStorage("postgresql://fake/db", connect_fn=connect)
    storage.initialise()

    for i in range(3):
        storage.save(_make_sample_trace(agent=f"agent_{i}"))

    # No UPDATE or DELETE in the SQL log
    for sql, _ in fake.executed:
        upper = sql.strip().upper()
        assert not upper.startswith("UPDATE"), f"UPDATE issued: {sql}"
        assert not upper.startswith("DELETE"), f"DELETE issued: {sql}"

    # No public mutator methods
    assert not hasattr(storage, "update")
    assert not hasattr(storage, "delete")


def test_postgres_storage_query_by_agent() -> None:
    fake, connect = _fake_connect_factory()
    storage = PostgresStorage("postgresql://fake/db", connect_fn=connect)
    storage.initialise()

    storage.save(_make_sample_trace(agent="alpha"))
    storage.save(_make_sample_trace(agent="beta"))
    storage.save(_make_sample_trace(agent="alpha"))

    alphas = storage.query(agent="alpha")
    betas = storage.query(agent="beta")

    assert len(alphas) == 2
    assert len(betas) == 1
    assert all(t.agent == "alpha" for t in alphas)


def test_postgres_storage_export_ndjson(tmp_path: Path) -> None:
    fake, connect = _fake_connect_factory()
    storage = PostgresStorage("postgresql://fake/db", connect_fn=connect)
    storage.initialise()

    for i in range(5):
        storage.save(_make_sample_trace(agent=f"agent_{i}"))

    out = tmp_path / "export.ndjson"
    count = storage.export_ndjson(str(out))
    assert count == 5

    lines = out.read_text().strip().splitlines()
    assert len(lines) == 5
    # every line is valid JSON and has the required fields
    for line in lines:
        data = json.loads(line)
        assert "trace_id" in data
        assert "agent" in data
        assert data["schema_version"] == "1.0.0"


def test_postgres_missing_dep_helpful_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """When psycopg2 is not installed, the error names the pip extra."""
    import sentinel.storage.postgres as pg_mod

    def fake_import() -> Any:
        raise ImportError(pg_mod._MISSING_DEP_MESSAGE)

    monkeypatch.setattr(pg_mod, "_import_psycopg2", fake_import)

    with pytest.raises(ImportError, match="sentinel-kernel\\[postgres\\]"):
        PostgresStorage("postgresql://fake/db")


def test_postgres_via_sentinel_facade() -> None:
    """Sentinel() accepts PostgresStorage and full trace cycle works."""
    fake, connect = _fake_connect_factory()
    storage = PostgresStorage("postgresql://fake/db", connect_fn=connect)

    sentinel = Sentinel(
        storage=storage,
        project="pg-facade-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )

    @sentinel.trace
    def score(company: str) -> dict[str, int]:
        return {"score": len(company)}

    score("Acme GmbH")
    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    assert traces[0].data_residency == DataResidency.EU_DE
    assert traces[0].sovereign_scope == "EU"
