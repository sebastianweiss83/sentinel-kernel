"""
sentinel.storage.postgres
~~~~~~~~~~~~~~~~~~~~~~~~~
PostgreSQL storage backend.

Append-only. Indexed on trace_id, agent, started_at, policy_result.
Optional dependency: psycopg2-binary (install with sentinel-kernel[postgres]).

Sovereignty note: PostgreSQL is a community-owned project (PGDG).
Core psycopg2 is BSD-licensed and has no vendor phone-home. A
PostgreSQL instance operated on EU-sovereign infrastructure satisfies
the critical path rule.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sentinel.storage.base import StorageBackend

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace, PolicyResult


_MISSING_DEP_MESSAGE = (
    "PostgresStorage requires psycopg2. Install the optional extra:\n"
    "    pip install sentinel-kernel[postgres]"
)


def _import_psycopg2() -> Any:
    try:
        import psycopg2  # pragma: no cover
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc
    return psycopg2  # pragma: no cover


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS decision_traces (
    trace_id        TEXT PRIMARY KEY,
    parent_trace_id TEXT,
    project         TEXT NOT NULL DEFAULT 'default',
    agent           TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
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
    payload         JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pg_traces_trace_id      ON decision_traces(trace_id);
CREATE INDEX IF NOT EXISTS idx_pg_traces_agent         ON decision_traces(agent);
CREATE INDEX IF NOT EXISTS idx_pg_traces_started_at    ON decision_traces(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pg_traces_policy_result ON decision_traces(policy_result);
CREATE INDEX IF NOT EXISTS idx_pg_traces_project       ON decision_traces(project);
"""


class PostgresStorage(StorageBackend):
    """
    PostgreSQL storage backend for decision traces.

    Append-only: the ``save()`` path uses INSERT only. This class intentionally
    exposes no UPDATE or DELETE helpers. Corrections or overrides are written
    as new traces linked by ``parent_trace_id`` (see docs/schema.md).

    Usage::

        from sentinel.storage.postgres import PostgresStorage
        storage = PostgresStorage("postgresql://user:pass@host:5432/traces")
        sentinel = Sentinel(storage=storage)
    """

    def __init__(self, dsn: str, *, connect_fn: Any = None) -> None:
        """
        :param dsn: PostgreSQL connection string (postgresql://...).
        :param connect_fn: Optional override for psycopg2.connect — used in
            tests to inject a fake connection without installing psycopg2.
        """
        self.dsn = dsn
        if connect_fn is None:
            psycopg2 = _import_psycopg2()
            self._connect_fn: Any = psycopg2.connect
        else:
            self._connect_fn = connect_fn
        self._conn: Any = None

    @property
    def backend_name(self) -> str:
        return "postgres"

    def _connection(self) -> Any:
        if self._conn is None:
            self._conn = self._connect_fn(self.dsn)
        return self._conn

    def initialise(self) -> None:
        conn = self._connection()
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
        conn.commit()

    def save(self, trace: DecisionTrace) -> None:
        """Append-only insert. Never UPDATE, never DELETE."""
        policy_result = None
        if trace.policy_evaluation:
            policy_result = trace.policy_evaluation.result.value

        conn = self._connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO decision_traces (
                    trace_id, parent_trace_id, project, agent, started_at,
                    completed_at, latency_ms, inputs_hash, output_hash,
                    model_provider, model_name, policy_result,
                    data_residency, sovereign_scope, storage_backend,
                    schema_version, payload
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                """,
                (
                    trace.trace_id,
                    trace.parent_trace_id,
                    trace.project,
                    trace.agent,
                    trace.started_at,
                    trace.completed_at,
                    trace.latency_ms,
                    trace.inputs_hash,
                    trace.output_hash,
                    trace.model_provider,
                    trace.model_name,
                    policy_result,
                    trace.data_residency.value,
                    trace.sovereign_scope,
                    trace.storage_backend,
                    trace.schema_version,
                    trace.to_json(),
                ),
            )
        conn.commit()

    def query(
        self,
        project: str | None = None,
        agent: str | None = None,
        policy_result: PolicyResult | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DecisionTrace]:
        from sentinel.core.trace import DecisionTrace

        conditions: list[str] = []
        params: list[Any] = []
        if project:
            conditions.append("project = %s")
            params.append(project)
        if agent:
            conditions.append("agent = %s")
            params.append(agent)
        if policy_result:
            conditions.append("policy_result = %s")
            params.append(policy_result.value)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        conn = self._connection()
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT payload FROM decision_traces
                {where}
                ORDER BY started_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            rows = cur.fetchall()

        return [DecisionTrace.from_dict(_coerce_payload(row[0])) for row in rows]

    def get(self, trace_id: str) -> DecisionTrace | None:
        from sentinel.core.trace import DecisionTrace

        conn = self._connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM decision_traces WHERE trace_id = %s",
                (trace_id,),
            )
            row = cur.fetchone()

        if row is None:
            return None
        return DecisionTrace.from_dict(_coerce_payload(row[0]))

    # export_ndjson / import_ndjson inherited from StorageBackend base class.
    # The base implementation pages through query() and handles filters.

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __repr__(self) -> str:
        return f"PostgresStorage(dsn={self.dsn!r})"


def _coerce_payload(payload: Any) -> dict[str, Any]:
    """psycopg2 returns JSONB as dict, but mock cursors may return str."""
    if isinstance(payload, dict):
        return payload
    return json.loads(payload)  # type: ignore[no-any-return]
