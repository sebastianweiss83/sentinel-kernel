"""
sentinel.storage.sqlite
~~~~~~~~~~~~~~~~~~~~~~~
SQLite storage backend. Zero dependencies, works everywhere.
The default for local development and single-node deployments.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from sentinel.storage.base import StorageBackend

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace, PolicyResult


class SQLiteStorage(StorageBackend):
    """
    SQLite-backed decision trace storage.

    Usage::

        storage = SQLiteStorage("./decisions.db")
        storage = SQLiteStorage(":memory:")  # For testing
    """

    def __init__(self, path: str | Path = "./sentinel-traces.db"):
        self.path = str(path)
        self._conn: sqlite3.Connection | None = None

    @property
    def backend_name(self) -> str:
        return "sqlite"

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def initialise(self) -> None:
        conn = self._connection()
        conn.executescript("""
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
            );

            CREATE INDEX IF NOT EXISTS idx_traces_project
                ON decision_traces(project);

            CREATE INDEX IF NOT EXISTS idx_traces_agent
                ON decision_traces(agent);

            CREATE INDEX IF NOT EXISTS idx_traces_policy_result
                ON decision_traces(policy_result);

            CREATE INDEX IF NOT EXISTS idx_traces_started_at
                ON decision_traces(started_at DESC);
        """)
        conn.commit()

    def save(self, trace: "DecisionTrace") -> None:
        from sentinel.core.trace import DecisionTrace as DT
        conn = self._connection()
        policy_result = None
        if trace.policy_evaluation:
            policy_result = trace.policy_evaluation.result.value

        conn.execute(
            """
            INSERT INTO decision_traces
                (trace_id, parent_trace_id, project, agent, started_at,
                 completed_at, latency_ms, inputs_hash, output_hash,
                 model_provider, model_name, policy_result,
                 data_residency, sovereign_scope, storage_backend,
                 schema_version, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace.trace_id,
                trace.parent_trace_id,
                trace.project,
                trace.agent,
                trace.started_at.isoformat(),
                trace.completed_at.isoformat() if trace.completed_at else None,
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
        policy_result: "PolicyResult | None" = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list["DecisionTrace"]:
        from sentinel.core.trace import DecisionTrace

        conditions = []
        params: list = []

        if project:
            conditions.append("project = ?")
            params.append(project)
        if agent:
            conditions.append("agent = ?")
            params.append(agent)
        if policy_result:
            conditions.append("policy_result = ?")
            params.append(policy_result.value)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        conn = self._connection()
        rows = conn.execute(
            f"""
            SELECT payload FROM decision_traces
            {where}
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()

        return [DecisionTrace.from_dict(json.loads(row["payload"])) for row in rows]

    def get(self, trace_id: str) -> "DecisionTrace | None":
        from sentinel.core.trace import DecisionTrace

        conn = self._connection()
        row = conn.execute(
            "SELECT payload FROM decision_traces WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()

        if row is None:
            return None
        return DecisionTrace.from_dict(json.loads(row["payload"]))

    def count(self, project: str | None = None) -> int:
        conn = self._connection()
        where = "WHERE project = ?" if project else ""
        params = [project] if project else []
        row = conn.execute(
            f"SELECT COUNT(*) as n FROM decision_traces {where}", params
        ).fetchone()
        return row["n"]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __repr__(self) -> str:
        return f"SQLiteStorage(path={self.path!r})"
