"""
examples/policy_deny.py
~~~~~~~~~~~~~~~~~~~~~~~
Shows ALLOW and DENY outcomes from SimpleRuleEvaluator.

Run: python examples/policy_deny.py
"""

import asyncio
import json

from sentinel import DataResidency, PolicyDeniedError, Sentinel
from sentinel.policy import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage

POLICY = "policies/discount"


def discount_policy(inputs: dict) -> tuple[bool, str | None]:
    """Deny discounts above 25%."""
    if inputs.get("discount_pct", 0) > 25:
        return False, "discount_exceeds_cap"
    return True, None


sentinel = Sentinel(
    storage=SQLiteStorage(":memory:"),
    project="policy-demo",
    data_residency=DataResidency.EU_DE,
    policy_evaluator=SimpleRuleEvaluator({POLICY: discount_policy}),
)


@sentinel.trace(policy=POLICY, tags={"env": "demo"})
async def apply_discount(deal_id: str, discount_pct: int) -> dict:
    return {"deal_id": deal_id, "discount_pct": discount_pct, "approved": True}


async def main():
    print("--- ALLOW: 15% discount ---")
    result = await apply_discount(deal_id="deal-001", discount_pct=15)
    print(f"Result: {result}\n")

    print("--- DENY: 40% discount ---")
    try:
        await apply_discount(deal_id="deal-002", discount_pct=40)
    except PolicyDeniedError as exc:
        print(f"Blocked: {exc}\n")

    print("--- Stored traces (raw payload) ---")
    conn = sentinel.storage._connection()
    rows = conn.execute(
        "SELECT payload, policy_result FROM decision_traces ORDER BY started_at DESC"
    ).fetchall()
    for row in rows:
        payload = json.loads(row["payload"])
        summary = {
            "trace_id": payload["trace_id"][:8] + "...",
            "agent": payload["agent"],
            "policy_result": row["policy_result"],
            "rule_triggered": (payload.get("policy") or {}).get("rule_triggered"),
        }
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
