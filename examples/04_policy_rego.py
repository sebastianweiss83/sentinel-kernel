"""
04 — OPA / Rego policy.

LocalRegoEvaluator runs an OPA binary in-process. No network, no OPA
server. Suitable for air-gapped deployments.

Prerequisites:
    - OPA binary on PATH. Install: https://www.openpolicyagent.org/docs/
      Pre-built binaries are available for Linux, macOS, Windows.

This example skips itself gracefully if OPA is not installed, so it
is safe in CI environments without the binary.

Run:
    python examples/04_policy_rego.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from sentinel import PolicyDeniedError, Sentinel
from sentinel.policy.evaluator import LocalRegoEvaluator
from sentinel.storage import SQLiteStorage


def main() -> int:
    if shutil.which("opa") is None:
        print("OPA binary not found on PATH. Install OPA to run this example:")
        print("  https://www.openpolicyagent.org/docs/latest/#running-opa")
        print("Skipping.")
        return 0

    policy_path = Path(__file__).parent / "policies" / "procurement_approval.rego"
    if not policy_path.exists():
        print(f"Policy not found: {policy_path}")
        return 1

    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="rego-demo",
        policy_evaluator=LocalRegoEvaluator(opa_binary="opa"),
    )

    @sentinel.trace(policy=str(policy_path))
    async def approve(request: dict) -> dict:
        return {"decision": "approved", "amount": request["amount"]}

    import asyncio

    async def run() -> None:
        # Under the cap
        result = await approve(request={"amount": 5_000, "requester_level": 3})
        print(f"ALLOW: {result}")

        # Over the cap
        try:
            await approve(request={"amount": 500_000, "requester_level": 3})
        except PolicyDeniedError as exc:
            print(f"DENY: {exc}")

    asyncio.run(run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
