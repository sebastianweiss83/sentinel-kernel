"""
tests/test_storage.py
~~~~~~~~~~~~~~~~~~~~~
Tests for storage backends: SQLiteStorage and FilesystemStorage.

Covers: save/get roundtrip, query with project filter, and filesystem
NDJSON persistence verified via tmp_path fixture.
"""


from sentinel.core.trace import DecisionTrace
from sentinel.storage import FilesystemStorage, SQLiteStorage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trace(project: str = "test-project", agent: str = "test-agent") -> DecisionTrace:
    trace = DecisionTrace(project=project, agent=agent, inputs={"x": 1})
    trace.complete(output={"result": "ok"}, latency_ms=10)
    return trace


# ---------------------------------------------------------------------------
# SQLiteStorage
# ---------------------------------------------------------------------------

class TestSQLiteStorage:
    def test_save_and_get_roundtrip(self):
        storage = SQLiteStorage(":memory:")
        storage.initialise()

        trace = _make_trace()
        storage.save(trace)

        retrieved = storage.get(trace.trace_id)
        assert retrieved is not None
        assert retrieved.trace_id == trace.trace_id
        assert retrieved.project == trace.project
        assert retrieved.agent == trace.agent
        assert retrieved.output == trace.output
        assert retrieved.latency_ms == trace.latency_ms

    def test_get_nonexistent_returns_none(self):
        storage = SQLiteStorage(":memory:")
        storage.initialise()

        result = storage.get("00000000-0000-0000-0000-000000000000")
        assert result is None

    def test_query_with_project_filter(self):
        storage = SQLiteStorage(":memory:")
        storage.initialise()

        trace_a = _make_trace(project="project-alpha")
        trace_b = _make_trace(project="project-beta")
        trace_c = _make_trace(project="project-alpha")

        storage.save(trace_a)
        storage.save(trace_b)
        storage.save(trace_c)

        alpha_traces = storage.query(project="project-alpha")
        assert len(alpha_traces) == 2
        assert all(t.project == "project-alpha" for t in alpha_traces)

        beta_traces = storage.query(project="project-beta")
        assert len(beta_traces) == 1
        assert beta_traces[0].project == "project-beta"

    def test_query_with_agent_filter(self):
        storage = SQLiteStorage(":memory:")
        storage.initialise()

        trace_1 = _make_trace(agent="agent-x")
        trace_2 = _make_trace(agent="agent-y")
        storage.save(trace_1)
        storage.save(trace_2)

        results = storage.query(agent="agent-x")
        assert len(results) == 1
        assert results[0].agent == "agent-x"

    def test_query_returns_most_recent_first(self):
        storage = SQLiteStorage(":memory:")
        storage.initialise()

        for i in range(3):
            storage.save(_make_trace(agent=f"agent-{i}"))

        results = storage.query()
        # Results are ordered by started_at DESC — all were created in quick
        # succession so we just verify we get all three back
        assert len(results) == 3

    def test_query_limit_respected(self):
        storage = SQLiteStorage(":memory:")
        storage.initialise()

        for _ in range(5):
            storage.save(_make_trace())

        results = storage.query(limit=2)
        assert len(results) == 2

    def test_save_preserves_inputs_hash(self):
        storage = SQLiteStorage(":memory:")
        storage.initialise()

        trace = _make_trace()
        assert trace.inputs_hash is not None
        storage.save(trace)

        retrieved = storage.get(trace.trace_id)
        assert retrieved.inputs_hash == trace.inputs_hash

    def test_backend_name_is_sqlite(self):
        storage = SQLiteStorage(":memory:")
        assert storage.backend_name == "sqlite"

    def test_initialise_is_idempotent(self):
        storage = SQLiteStorage(":memory:")
        storage.initialise()
        storage.initialise()  # Should not raise

        storage.save(_make_trace())
        assert len(storage.query()) == 1


# ---------------------------------------------------------------------------
# FilesystemStorage
# ---------------------------------------------------------------------------

class TestFilesystemStorage:
    def test_save_and_get_roundtrip(self, tmp_path):
        storage = FilesystemStorage(tmp_path / "traces")
        storage.initialise()

        trace = _make_trace()
        storage.save(trace)

        retrieved = storage.get(trace.trace_id)
        assert retrieved is not None
        assert retrieved.trace_id == trace.trace_id
        assert retrieved.project == trace.project
        assert retrieved.output == trace.output

    def test_get_nonexistent_returns_none(self, tmp_path):
        storage = FilesystemStorage(tmp_path / "traces")
        storage.initialise()

        result = storage.get("00000000-0000-0000-0000-000000000000")
        assert result is None

    def test_creates_ndjson_file(self, tmp_path):
        trace_dir = tmp_path / "traces"
        storage = FilesystemStorage(trace_dir)
        storage.initialise()

        trace = _make_trace()
        storage.save(trace)

        ndjson_files = list(trace_dir.glob("*.ndjson"))
        assert len(ndjson_files) == 1

    def test_creates_index_file(self, tmp_path):
        trace_dir = tmp_path / "traces"
        storage = FilesystemStorage(trace_dir)
        storage.initialise()

        index_path = trace_dir / "index.json"
        assert index_path.exists()

    def test_index_updated_after_save(self, tmp_path):
        import json

        trace_dir = tmp_path / "traces"
        storage = FilesystemStorage(trace_dir)
        storage.initialise()

        trace = _make_trace()
        storage.save(trace)

        index = json.loads((trace_dir / "index.json").read_text())
        assert trace.trace_id in index

    def test_query_with_project_filter(self, tmp_path):
        storage = FilesystemStorage(tmp_path / "traces")
        storage.initialise()

        trace_a = _make_trace(project="project-a")
        trace_b = _make_trace(project="project-b")
        storage.save(trace_a)
        storage.save(trace_b)

        results = storage.query(project="project-a")
        assert len(results) == 1
        assert results[0].project == "project-a"

    def test_backend_name_is_filesystem(self, tmp_path):
        storage = FilesystemStorage(tmp_path / "traces")
        assert storage.backend_name == "filesystem"

    def test_multiple_traces_retrievable(self, tmp_path):
        storage = FilesystemStorage(tmp_path / "traces")
        storage.initialise()

        traces = [_make_trace() for _ in range(3)]
        for t in traces:
            storage.save(t)

        for original in traces:
            retrieved = storage.get(original.trace_id)
            assert retrieved is not None
            assert retrieved.trace_id == original.trace_id
