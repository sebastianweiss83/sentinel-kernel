"""
tests/test_export_import.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Round-trip tests for the NDJSON export/import on StorageBackend.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sentinel import Sentinel
from sentinel.storage import SQLiteStorage


def _populate(sentinel: Sentinel) -> None:
    @sentinel.trace(agent_name="alpha_agent")
    def alpha(x: int) -> dict:
        return {"result": x * 2}

    @sentinel.trace(agent_name="beta_agent")
    def beta(x: int) -> dict:
        return {"result": x + 100}

    for i in range(3):
        alpha(x=i)
        beta(x=i)


def test_export_ndjson_writes_all_traces(tmp_path: Path) -> None:
    sentinel = Sentinel(
        storage=SQLiteStorage(str(tmp_path / "src.db")),
        project="export-test",
    )
    _populate(sentinel)

    out_file = tmp_path / "out.ndjson"
    count = sentinel.storage.export_ndjson(out_file)
    assert count == 6
    lines = out_file.read_text().strip().split("\n")
    assert len(lines) == 6


def test_export_ndjson_filters_by_agent(tmp_path: Path) -> None:
    sentinel = Sentinel(
        storage=SQLiteStorage(str(tmp_path / "src.db")),
        project="export-test",
    )
    _populate(sentinel)

    out_file = tmp_path / "alpha.ndjson"
    count = sentinel.storage.export_ndjson(out_file, agent="alpha_agent")
    assert count == 3


def test_export_ndjson_filters_by_time(tmp_path: Path) -> None:
    sentinel = Sentinel(
        storage=SQLiteStorage(str(tmp_path / "src.db")),
        project="export-test",
    )
    _populate(sentinel)

    # Narrow window well in the future — should match nothing
    future = datetime.now(UTC) + timedelta(days=10)
    out_file = tmp_path / "empty.ndjson"
    count = sentinel.storage.export_ndjson(
        out_file, start=future, end=future + timedelta(days=1)
    )
    assert count == 0


def test_import_ndjson_round_trip(tmp_path: Path) -> None:
    src = Sentinel(
        storage=SQLiteStorage(str(tmp_path / "src.db")),
        project="export-test",
    )
    _populate(src)
    out_file = tmp_path / "round.ndjson"
    src.storage.export_ndjson(out_file)

    dst = Sentinel(
        storage=SQLiteStorage(str(tmp_path / "dst.db")),
        project="export-test",
    )
    imported, skipped = dst.storage.import_ndjson(out_file)
    assert imported == 6
    assert skipped == 0

    round_trip = dst.storage.query(limit=100)
    assert len(round_trip) == 6


def test_import_ndjson_skips_duplicates(tmp_path: Path) -> None:
    src = Sentinel(
        storage=SQLiteStorage(str(tmp_path / "src.db")),
        project="export-test",
    )
    _populate(src)
    out_file = tmp_path / "dup.ndjson"
    src.storage.export_ndjson(out_file)

    dst = Sentinel(
        storage=SQLiteStorage(str(tmp_path / "dst.db")),
        project="export-test",
    )
    first_imported, first_skipped = dst.storage.import_ndjson(out_file)
    assert first_imported == 6
    assert first_skipped == 0

    second_imported, second_skipped = dst.storage.import_ndjson(out_file)
    assert second_imported == 0
    assert second_skipped == 6


def test_cli_export_and_import_round_trip(tmp_path: Path, capsys) -> None:
    from sentinel import cli

    db = tmp_path / "source.db"
    sentinel = Sentinel(
        storage=SQLiteStorage(str(db)),
        project="cli-export-test",
    )
    _populate(sentinel)

    out_file = tmp_path / "exported.ndjson"
    rc = cli.main(["export", "--output", str(out_file), "--db", str(db)])
    assert rc == 0
    export_out = capsys.readouterr().out
    assert f"Exported 6 traces to {out_file}" in export_out
    # v3.1.x — every file-writing command prints a cross-platform open hint.
    assert f"  → {cli._open_hint(str(out_file))}" in export_out
    assert out_file.exists()

    dst_db = tmp_path / "dest.db"
    rc = cli.main(["import", "--input", str(out_file), "--db", str(dst_db)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Imported 6 traces" in out
    assert "skipped 0" in out


def test_export_ndjson_filesystem_backend(tmp_path: Path) -> None:
    from sentinel.storage.filesystem import FilesystemStorage

    src_dir = tmp_path / "fs"
    storage = FilesystemStorage(str(src_dir))
    sentinel = Sentinel(storage=storage, project="fs-test")
    _populate(sentinel)

    out_file = tmp_path / "fs.ndjson"
    count = storage.export_ndjson(out_file)
    assert count == 6
