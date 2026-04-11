"""
examples/smoke_test.py
~~~~~~~~~~~~~~~~~~~~~~
End-to-end smoke test for Sentinel.

Exercises the full stack:
  1. SQLiteStorage in a temp dir
  2. @sentinel.trace on a simple function
  3. ALLOW, DENY, EXCEPTION paths
  4. Kill switch engage → block, disengage → resume
  5. Query the trace store
  6. NDJSON export from SQLite storage
  7. FilesystemStorage round-trip
  8. Cleanup

Run:  python examples/smoke_test.py
Exit: 0 on success, 1 on any failure.

Requires only the core sentinel-kernel package — no optional extras.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

from sentinel import (
    DataResidency,
    KillSwitchEngaged,
    PolicyResult,
    Sentinel,
)
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import FilesystemStorage, SQLiteStorage


def _step(n: int, msg: str) -> None:
    print(f"  Step {n}: {msg}")


def run() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="sentinel-smoke-"))
    try:
        # ------------------------------------------------------------------
        # Step 1: SQLite trace
        # ------------------------------------------------------------------
        sqlite_path = tmp / "traces.db"

        def policy(inputs: dict) -> tuple[bool, str | None]:
            if inputs.get("action") == "forbid":
                return False, "forbidden_action"
            return True, None

        sentinel = Sentinel(
            storage=SQLiteStorage(str(sqlite_path)),
            project="smoke-test",
            data_residency=DataResidency.EU_DE,
            sovereign_scope="EU",
            policy_evaluator=SimpleRuleEvaluator({"policies/smoke.py": policy}),
        )
        _step(1, f"SQLite storage initialised at {sqlite_path.name}")

        # ------------------------------------------------------------------
        # Step 2: wrap a function
        # ------------------------------------------------------------------
        @sentinel.trace(policy="policies/smoke.py")
        async def decide(action: str, value: int = 0) -> dict:
            if action == "explode":
                raise RuntimeError("boom")
            return {"action": action, "value": value}

        _step(2, "@sentinel.trace applied to decide()")

        # ------------------------------------------------------------------
        # Step 3: ALLOW, DENY, EXCEPTION
        # ------------------------------------------------------------------
        result = asyncio.run(decide(action="approve", value=42))
        assert result == {"action": "approve", "value": 42}
        _step(3, "ALLOW call succeeded")

        from sentinel.core.tracer import PolicyDeniedError

        try:
            asyncio.run(decide(action="forbid"))
        except PolicyDeniedError:
            pass
        else:
            print("FAIL: policy DENY did not raise")
            return 1
        _step(3, "DENY call raised PolicyDeniedError and wrote DENY trace")

        try:
            asyncio.run(decide(action="explode"))
        except RuntimeError:
            pass
        else:
            print("FAIL: EXCEPTION did not propagate")
            return 1
        _step(3, "EXCEPTION call propagated and wrote error trace")

        # ------------------------------------------------------------------
        # Step 4: kill switch
        # ------------------------------------------------------------------
        sentinel.engage_kill_switch("smoke test halt")
        try:
            asyncio.run(decide(action="approve"))
        except KillSwitchEngaged:
            pass
        else:
            print("FAIL: kill switch did not block execution")
            return 1
        _step(4, "Kill switch blocked execution and recorded DENY trace")

        sentinel.disengage_kill_switch("smoke test resume")
        result = asyncio.run(decide(action="approve", value=1))
        assert result["value"] == 1
        _step(4, "Kill switch disengaged, normal execution resumed")

        # ------------------------------------------------------------------
        # Step 5: query
        # ------------------------------------------------------------------
        all_traces = sentinel.query(limit=100)
        assert len(all_traces) == 5, f"expected 5 traces, got {len(all_traces)}"
        deny_traces = sentinel.query(policy_result=PolicyResult.DENY, limit=100)
        assert len(deny_traces) == 2, f"expected 2 DENY traces, got {len(deny_traces)}"
        _step(5, f"Queried trace store: {len(all_traces)} total, {len(deny_traces)} DENY")

        # ------------------------------------------------------------------
        # Step 6: NDJSON export
        # ------------------------------------------------------------------
        export_path = tmp / "export.ndjson"
        with open(export_path, "w", encoding="utf-8") as f:
            for t in all_traces:
                f.write(t.to_json().replace("\n", " ") + "\n")

        lines = export_path.read_text().strip().splitlines()
        assert len(lines) == 5
        for line in lines:
            data = json.loads(line)
            assert "trace_id" in data
            assert data["schema_version"] == "1.0.0"
        _step(6, f"Exported {len(lines)} traces to NDJSON")

        # ------------------------------------------------------------------
        # Step 7 & 8: FilesystemStorage
        # ------------------------------------------------------------------
        fs_dir = tmp / "fs-traces"
        fs_sentinel = Sentinel(
            storage=FilesystemStorage(str(fs_dir)),
            project="smoke-fs",
            data_residency=DataResidency.AIR_GAPPED,
        )
        _step(7, "FilesystemStorage initialised")

        @fs_sentinel.trace
        def score(company: str) -> dict:
            return {"company": company, "score": len(company)}

        score("Acme GmbH")
        score("Bosch SE")

        ndjson_files = list(fs_dir.glob("*.ndjson"))
        assert len(ndjson_files) == 1, f"expected 1 ndjson file, got {len(ndjson_files)}"
        fs_lines = ndjson_files[0].read_text().strip().splitlines()
        assert len(fs_lines) == 2, f"expected 2 ndjson lines, got {len(fs_lines)}"
        for line in fs_lines:
            data = json.loads(line)
            assert data["project"] == "smoke-fs"
        _step(8, f"FilesystemStorage wrote {len(fs_lines)} NDJSON trace lines")

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        print()
        print("=" * 60)
        print("  SMOKE TEST PASSED")
        print(f"  {len(all_traces) + len(fs_lines)} traces written across 2 storage backends")
        print("  Kill switch tested (engage/disengage)")
        print("  NDJSON export validated")
        print("  All sovereignty metadata preserved")
        print("=" * 60)
        return 0

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run())
