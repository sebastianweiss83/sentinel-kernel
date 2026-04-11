"""
tests/test_storage_filesystem.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Direct unit tests for FilesystemStorage — the air-gapped reference
backend. Exercises save, query, get, index rebuild, and every error
branch (missing file, missing index, corrupt JSON line, path traversal).

These tests pin every branch of the air-gap code path at 100% so any
regression in the classified storage backend is caught immediately.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.core.trace import (
    DataResidency,
    DecisionTrace,
    PolicyEvaluation,
    PolicyResult,
)
from sentinel.storage.filesystem import FilesystemStorage


def _trace(
    *,
    project: str = "test",
    agent: str = "unit",
    result: PolicyResult = PolicyResult.ALLOW,
) -> DecisionTrace:
    t = DecisionTrace(
        project=project,
        agent=agent,
        inputs={"x": 1},
        data_residency=DataResidency.LOCAL,
    )
    t.policy_evaluation = PolicyEvaluation(
        policy_id="p",
        policy_version="v1",
        result=result,
    )
    return t


# ---------------------------------------------------------------------------
# initialise
# ---------------------------------------------------------------------------


def test_initialise_creates_base_path(tmp_path: Path) -> None:
    target = tmp_path / "subdir" / "traces"
    storage = FilesystemStorage(target)
    storage.initialise()
    assert target.exists()
    assert (target / "index.json").exists()
    assert json.loads((target / "index.json").read_text()) == {}


def test_initialise_idempotent_with_existing_index(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    (tmp_path / "index.json").write_text('{"existing": "2026-04-01.ndjson"}')
    storage.initialise()  # must not overwrite
    assert json.loads((tmp_path / "index.json").read_text()) == {
        "existing": "2026-04-01.ndjson"
    }


def test_backend_name_is_filesystem(tmp_path: Path) -> None:
    assert FilesystemStorage(tmp_path).backend_name == "filesystem"


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------


def test_save_writes_ndjson_line(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    t = _trace()
    storage.save(t)

    ndjson_files = list(tmp_path.glob("*.ndjson"))
    assert len(ndjson_files) == 1
    line = ndjson_files[0].read_text().strip()
    payload = json.loads(line)
    assert payload["trace_id"] == t.trace_id
    assert payload["project"] == "test"


def test_save_appends_multiple_lines(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    for i in range(5):
        storage.save(_trace(agent=f"agent-{i}"))

    ndjson_files = list(tmp_path.glob("*.ndjson"))
    assert len(ndjson_files) == 1
    lines = [
        line for line in ndjson_files[0].read_text().splitlines() if line.strip()
    ]
    assert len(lines) == 5


def test_save_updates_index(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    t = _trace()
    storage.save(t)

    index = json.loads((tmp_path / "index.json").read_text())
    assert t.trace_id in index
    assert index[t.trace_id].endswith(".ndjson")


def test_save_rebuilds_index_if_corrupt(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    (tmp_path / "index.json").write_text("not-valid-json{{")

    t = _trace()
    storage.save(t)

    index = json.loads((tmp_path / "index.json").read_text())
    assert t.trace_id in index


def test_save_rebuilds_index_if_missing(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    (tmp_path / "index.json").unlink()

    t = _trace()
    storage.save(t)

    index = json.loads((tmp_path / "index.json").read_text())
    assert t.trace_id in index


def test_save_strips_newlines_from_trace_json(tmp_path: Path) -> None:
    """to_json() produces pretty JSON with embedded newlines; save()
    flattens each record to a single NDJSON line."""
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    storage.save(_trace())

    ndjson = next(tmp_path.glob("*.ndjson")).read_text()
    # Every non-empty line must parse as a complete JSON object
    lines = [line for line in ndjson.splitlines() if line.strip()]
    for line in lines:
        json.loads(line)


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------


def test_query_returns_most_recent_first(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    ids = []
    for i in range(3):
        t = _trace(agent=f"agent-{i}")
        ids.append(t.trace_id)
        storage.save(t)

    results = storage.query()
    assert len(results) == 3
    # File is iterated in reverse — newest first
    assert results[0].trace_id == ids[-1]


def test_query_filter_by_project(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    storage.save(_trace(project="alpha"))
    storage.save(_trace(project="beta"))
    storage.save(_trace(project="alpha"))

    alpha = storage.query(project="alpha")
    assert len(alpha) == 2
    assert all(t.project == "alpha" for t in alpha)


def test_query_filter_by_agent(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    storage.save(_trace(agent="a"))
    storage.save(_trace(agent="b"))

    only_a = storage.query(agent="a")
    assert len(only_a) == 1
    assert only_a[0].agent == "a"


def test_query_filter_by_policy_result(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    storage.save(_trace(result=PolicyResult.ALLOW))
    storage.save(_trace(result=PolicyResult.DENY))
    storage.save(_trace(result=PolicyResult.ALLOW))

    denies = storage.query(policy_result=PolicyResult.DENY)
    assert len(denies) == 1
    assert denies[0].policy_evaluation.result == PolicyResult.DENY


def test_query_limit_and_offset(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    for i in range(10):
        storage.save(_trace(agent=f"a{i}"))

    page1 = storage.query(limit=3, offset=0)
    page2 = storage.query(limit=3, offset=3)
    assert len(page1) == 3
    assert len(page2) == 3
    assert {t.trace_id for t in page1}.isdisjoint({t.trace_id for t in page2})


def test_query_skips_blank_lines(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    storage.save(_trace())

    # Inject blank lines into the NDJSON file
    ndjson_file = next(tmp_path.glob("*.ndjson"))
    ndjson_file.write_text("\n\n" + ndjson_file.read_text() + "\n\n   \n")

    assert len(storage.query()) == 1


def test_query_skips_corrupt_json_lines(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    storage.save(_trace(agent="valid"))

    ndjson_file = next(tmp_path.glob("*.ndjson"))
    with ndjson_file.open("a") as f:
        f.write("this is not json\n")
        f.write("{{ also not json\n")

    results = storage.query()
    assert len(results) == 1
    assert results[0].agent == "valid"


def test_query_returns_empty_on_fresh_storage(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    assert storage.query() == []


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_get_by_id_returns_matching_trace(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    t = _trace(agent="target")
    storage.save(t)
    storage.save(_trace(agent="other"))

    loaded = storage.get(t.trace_id)
    assert loaded is not None
    assert loaded.trace_id == t.trace_id
    assert loaded.agent == "target"


def test_get_unknown_id_returns_none(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    assert storage.get("does-not-exist") is None


def test_get_with_missing_index_returns_none(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    (tmp_path / "index.json").unlink()
    assert storage.get("anything") is None


def test_get_with_corrupt_index_returns_none(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    (tmp_path / "index.json").write_text("not valid json")
    assert storage.get("anything") is None


def test_get_rejects_path_traversal_via_index(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    (tmp_path / "index.json").write_text(
        json.dumps({"evil": "../../etc/passwd"})
    )
    assert storage.get("evil") is None


def test_get_rejects_absolute_path_via_index(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    (tmp_path / "index.json").write_text(
        json.dumps({"evil": "/etc/passwd"})
    )
    assert storage.get("evil") is None


def test_get_when_indexed_file_missing_returns_none(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    (tmp_path / "index.json").write_text(
        json.dumps({"ghost": "2000-01-01.ndjson"})
    )
    assert storage.get("ghost") is None


def test_get_when_file_exists_but_trace_id_not_found_returns_none(
    tmp_path: Path,
) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    # Create a real ndjson file but no matching record
    target = tmp_path / "2026-04-01.ndjson"
    target.write_text('{"trace_id": "other-id"}\n')
    (tmp_path / "index.json").write_text(
        json.dumps({"looking-for-this": target.name})
    )
    assert storage.get("looking-for-this") is None


def test_get_skips_corrupt_lines_and_finds_match(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    storage.initialise()
    t = _trace(agent="needle")
    storage.save(t)

    ndjson_file = next(tmp_path.glob("*.ndjson"))
    original = ndjson_file.read_text()
    # Prepend a corrupt line then the real one
    ndjson_file.write_text("garbage not json\n" + original)

    loaded = storage.get(t.trace_id)
    assert loaded is not None
    assert loaded.agent == "needle"


# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------


def test_accepts_string_path(tmp_path: Path) -> None:
    storage = FilesystemStorage(str(tmp_path))
    storage.initialise()
    assert storage.base_path == tmp_path


def test_current_file_uses_today(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    current = storage._current_file()
    # Format: YYYY-MM-DD.ndjson
    assert current.name.endswith(".ndjson")
    assert len(current.name) == len("YYYY-MM-DD.ndjson")


# ---------------------------------------------------------------------------
# Sovereignty guarantees — regression guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["FilesystemStorage"],
)
def test_api_surface_stable(name: str) -> None:
    """Regression guard: the public API of the reference air-gap
    backend must not change without an RFC."""
    cls = getattr(
        __import__("sentinel.storage.filesystem", fromlist=[name]), name
    )
    for method in ("initialise", "save", "query", "get", "backend_name"):
        assert hasattr(cls, method), f"FilesystemStorage missing {method}"
