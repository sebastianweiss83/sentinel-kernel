"""
sentinel.storage.base
~~~~~~~~~~~~~~~~~~~~~
Abstract base for all Sentinel storage backends.
Swap SQLite for Postgres or filesystem with one line.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace, PolicyResult


class StorageBackend(ABC):
    """
    Base class for all Sentinel storage backends.

    Implementing a new backend requires only these four abstract
    methods. Export/import helpers are provided by this base class
    and work across every backend.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Human-readable name for this backend, stored in traces."""
        ...

    @abstractmethod
    def initialise(self) -> None:
        """Create tables / ensure schema exists. Safe to call multiple times."""
        ...

    @abstractmethod
    def save(self, trace: DecisionTrace) -> None:
        """Persist a decision trace. Must be synchronous — called in hot path."""
        ...

    @abstractmethod
    def query(
        self,
        project: str | None = None,
        agent: str | None = None,
        policy_result: PolicyResult | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DecisionTrace]:
        """Query stored traces with basic filters."""
        ...

    @abstractmethod
    def get(self, trace_id: str) -> DecisionTrace | None:
        """Retrieve a single trace by ID."""
        ...

    # ------------------------------------------------------------------
    # Export / Import — shared across all backends
    # ------------------------------------------------------------------

    def export_ndjson(
        self,
        path: str | Path,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        agent: str | None = None,
        project: str | None = None,
    ) -> int:
        """
        Export traces to an NDJSON file.

        Filters:
            start:   include only traces with ``started_at >= start``
            end:     include only traces with ``started_at < end``
            agent:   include only traces from this agent name
            project: include only traces from this project

        Returns the number of traces written.

        NDJSON is the canonical interchange format — one JSON object
        per line, no surrounding array. Human-readable, streaming-
        friendly, and tool-independent.
        """
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with out_path.open("w", encoding="utf-8") as fh:
            # Page through results using offset to handle large tables.
            page_size = 500
            offset = 0
            while True:
                traces = self.query(
                    project=project,
                    agent=agent,
                    limit=page_size,
                    offset=offset,
                )
                if not traces:
                    break
                for trace in traces:
                    if start and trace.started_at and trace.started_at < start:
                        continue
                    if end and trace.started_at and trace.started_at >= end:
                        continue
                    fh.write(json.dumps(trace.to_dict(), default=str))
                    fh.write("\n")
                    count += 1
                offset += page_size
                if len(traces) < page_size:
                    break
        return count

    def import_ndjson(self, path: str | Path) -> tuple[int, int]:
        """
        Import traces from an NDJSON file.

        Skips traces with a ``trace_id`` that already exists in this
        backend. Returns ``(imported, skipped_duplicates)``.
        """
        from sentinel.core.trace import DecisionTrace

        in_path = Path(path)
        imported = 0
        skipped = 0
        with in_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                trace_id = data.get("trace_id")
                if trace_id and self.get(trace_id) is not None:
                    skipped += 1
                    continue
                trace = DecisionTrace.from_dict(data)
                self.save(trace)
                imported += 1
        return imported, skipped
