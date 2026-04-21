"""Write-once filesystem storage backend — v3.5 Item 4.

Application-layer tamper **prevention** for regulated environments
where detection after the fact is not sufficient: the backend rejects
any ``save()`` of a ``trace_id`` already on disk, and applies the
POSIX user-immutable flag (``chflags uchg`` on macOS, ``chattr +i``
on Linux) as defense in depth.

See :doc:`docs/architecture/v3.5-item-4-writeonce-storage` for the
full design rationale.

Sovereignty guarantees
----------------------
- No network calls. Works air-gapped.
- OS-level immutability is best-effort; software-level rejection is
  the primary guarantee.
- One NDJSON file per trace — easy to back up, easy to audit, easy
  to cryptographically hash the directory tree.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from sentinel.storage.base import StorageBackend

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace, PolicyResult


log = logging.getLogger(__name__)


class WriteOnceViolation(RuntimeError):
    """Raised when a write-once backend rejects an attempt to overwrite a
    stored trace.

    Write-once violations surface as exceptions rather than silent
    no-ops because they always indicate something an operator needs
    to know about — either a uuid4 collision (vanishingly unlikely,
    but worth flagging) or an overwrite attempt by downstream code or
    a threat actor.
    """

    def __init__(self, trace_id: str) -> None:
        super().__init__(
            f"trace {trace_id!r} is already stored; "
            f"write-once backend refuses to overwrite"
        )
        self.trace_id = trace_id


def _apply_immutable_flag(path: Path) -> bool:
    """Best-effort OS-level user-immutable flag.

    Returns True when the flag was applied, False when skipped
    (unsupported platform / filesystem / permission). Failure is
    logged at debug level — the software-level write-once rejection
    in :meth:`WriteOnceFilesystemStorage.save` is the primary
    guarantee; this is defense in depth.
    """
    try:
        if sys.platform == "darwin":
            subprocess.run(
                ["chflags", "uchg", str(path)],
                check=True,
                capture_output=True,
                timeout=5,
            )
            return True
        if sys.platform.startswith("linux"):
            subprocess.run(
                ["chattr", "+i", str(path)],
                check=True,
                capture_output=True,
                timeout=5,
            )
            return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        log.debug(
            "immutable flag application skipped on %s: %s",
            path,
            exc,
        )
        return False
    return False


def _clear_immutable_flag(path: Path) -> None:
    """Clear the OS-level immutable flag — used only by tests / admin tools.

    Production code never calls this. Tests use it to clean up between
    assertions; admin tooling would use it for legal-hold expiry.
    """
    try:
        if sys.platform == "darwin":
            subprocess.run(
                ["chflags", "nouchg", str(path)],
                check=False,
                capture_output=True,
                timeout=5,
            )
        elif sys.platform.startswith("linux"):
            subprocess.run(
                ["chattr", "-i", str(path)],
                check=False,
                capture_output=True,
                timeout=5,
            )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


class WriteOnceFilesystemStorage(StorageBackend):
    """Filesystem backend that refuses to overwrite traces.

    File layout: one ``<trace_id>.ndjson`` file per trace in the
    configured directory. On first save:

    1. Set ``trace.storage_mode = "writeonce_fs"``.
    2. Write the file atomically via temp-file + os.replace.
    3. Apply OS immutable flag (best effort).

    Second and subsequent ``save()`` calls for the same trace_id
    raise :class:`WriteOnceViolation`.
    """

    def __init__(self, path: str | Path, *, apply_immutable: bool = True) -> None:
        """Initialise.

        ``apply_immutable=False`` is available for tests and for
        scenarios where OS-level immutability is enforced elsewhere
        (e.g., a read-only mount).
        """
        self.path = Path(path).expanduser()
        self._apply_immutable = apply_immutable

    @property
    def backend_name(self) -> str:
        return "writeonce_fs"

    def initialise(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)

    def _path_for(self, trace_id: str) -> Path:
        # Sanitise: trace_id comes from uuid4 but we never want to let
        # a caller traverse out of the storage root.
        if "/" in trace_id or ".." in trace_id or trace_id.startswith("."):
            raise ValueError(
                f"invalid trace_id for filesystem storage: {trace_id!r}"
            )
        return self.path / f"{trace_id}.ndjson"

    def save(self, trace: DecisionTrace) -> None:
        target = self._path_for(trace.trace_id)
        if target.exists():
            raise WriteOnceViolation(trace.trace_id)

        # Claim storage discipline on the trace itself so the signature
        # covers the claim (matters when the trace is verified offline).
        trace.storage_mode = "writeonce_fs"

        line = trace.to_json().replace("\n", " ") + "\n"

        # Atomic write: write to .tmp, then os.replace to target.
        tmp = target.with_suffix(".ndjson.tmp")
        tmp.write_text(line, encoding="utf-8")
        os.replace(tmp, target)

        if self._apply_immutable:
            _apply_immutable_flag(target)

    def query(
        self,
        project: str | None = None,
        agent: str | None = None,
        policy_result: PolicyResult | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DecisionTrace]:
        from sentinel.core.trace import DecisionTrace

        results: list[DecisionTrace] = []

        # Newest-first: sort by mtime descending so query() returns
        # recent traces in recent-first order, matching the default
        # FilesystemStorage contract.
        files = sorted(
            self.path.glob("*.ndjson"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for f in files:
            try:
                data = json.loads(f.read_text())
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
                break

        return results[offset:offset + limit]

    def get(self, trace_id: str) -> DecisionTrace | None:
        from sentinel.core.trace import DecisionTrace

        try:
            target = self._path_for(trace_id)
        except ValueError:
            return None
        if not target.exists():
            return None
        try:
            data = json.loads(target.read_text())
        except json.JSONDecodeError:
            return None
        return DecisionTrace.from_dict(data)


__all__ = [
    "WriteOnceFilesystemStorage",
    "WriteOnceViolation",
    "_apply_immutable_flag",
    "_clear_immutable_flag",
]
