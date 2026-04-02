"""
sentinel.storage.filesystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Filesystem-based storage backend.
Writes NDJSON to disk. No network. No database. 
Works in air-gapped and VS-NfD classified environments.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sentinel.storage.base import StorageBackend

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace, PolicyResult


class FilesystemStorage(StorageBackend):
    """
    Air-gapped storage backend. Writes one NDJSON file per day.

    Designed for classified environments where no network connection
    is available and audit logs must remain on local storage.

    File structure::

        /mnt/traces/
        ├── 2026-04-01.ndjson
        ├── 2026-04-02.ndjson
        └── index.json          # Trace ID → filename index

    Usage::

        storage = FilesystemStorage("/mnt/classified/traces/")
    """

    def __init__(self, path: str | Path, rotate: str = "daily"):
        self.base_path = Path(path)
        self.rotate = rotate

    @property
    def backend_name(self) -> str:
        return "filesystem"

    def initialise(self) -> None:
        self.base_path.mkdir(parents=True, exist_ok=True)
        index = self.base_path / "index.json"
        if not index.exists():
            index.write_text("{}")

    def _current_file(self) -> Path:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return self.base_path / f"{today}.ndjson"

    def save(self, trace: DecisionTrace) -> None:
        line = trace.to_json().replace("\n", " ") + "\n"
        with open(self._current_file(), "a", encoding="utf-8") as f:
            f.write(line)

        # Update index
        index_path = self.base_path / "index.json"
        try:
            index = json.loads(index_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            index = {}
        index[trace.trace_id] = self._current_file().name
        index_path.write_text(json.dumps(index, indent=2))

    def query(
        self,
        project: str | None = None,
        agent: str | None = None,
        policy_result: PolicyResult | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DecisionTrace]:
        from sentinel.core.trace import DecisionTrace

        results = []
        ndjson_files = sorted(self.base_path.glob("*.ndjson"), reverse=True)

        for ndjson_file in ndjson_files:
            for line in reversed(ndjson_file.read_text().splitlines()):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if project and data.get("project") != project:
                    continue
                if agent and data.get("agent") != agent:
                    continue
                if policy_result:
                    pr = data.get("policy", {}) or {}
                    if pr.get("result") != policy_result.value:
                        continue

                results.append(DecisionTrace.from_dict(data))
                if len(results) >= limit + offset:
                    return results[offset:offset + limit]

        return results[offset:offset + limit]

    def get(self, trace_id: str) -> DecisionTrace | None:
        from sentinel.core.trace import DecisionTrace

        index_path = self.base_path / "index.json"
        try:
            index = json.loads(index_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return None

        filename = index.get(trace_id)
        if not filename:
            return None

        file_path = self.base_path / filename
        if not file_path.exists():
            return None

        for line in file_path.read_text().splitlines():
            try:
                data = json.loads(line)
                if data.get("trace_id") == trace_id:
                    return DecisionTrace.from_dict(data)
            except json.JSONDecodeError:
                continue

        return None
