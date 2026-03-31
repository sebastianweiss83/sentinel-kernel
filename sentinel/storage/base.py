"""
sentinel.storage.base
~~~~~~~~~~~~~~~~~~~~~
Abstract base for all Sentinel storage backends.
Swap SQLite for D1, Postgres, or filesystem with one line.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace, PolicyResult


class StorageBackend(ABC):
    """
    Base class for all Sentinel storage backends.

    Implementing a new backend requires only these four methods.
    The rest of Sentinel doesn't care which backend is running.
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
    def save(self, trace: "DecisionTrace") -> None:
        """Persist a decision trace. Must be synchronous — called in hot path."""
        ...

    @abstractmethod
    def query(
        self,
        project: str | None = None,
        agent: str | None = None,
        policy_result: "PolicyResult | None" = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list["DecisionTrace"]:
        """Query stored traces with basic filters."""
        ...

    @abstractmethod
    def get(self, trace_id: str) -> "DecisionTrace | None":
        """Retrieve a single trace by ID."""
        ...
