"""
Sentinel Quickstart
===================

This is the magic moment: run this script and see your first
sovereign decision trace appear.

No cloud account. No API key. No configuration.
Just: python examples/quickstart.py

Time to first trace: under 5 minutes.
"""

import asyncio
import json

from sentinel import Sentinel, DataResidency
from sentinel.storage import SQLiteStorage


# 1. Initialise Sentinel with local storage
sentinel = Sentinel(
    storage=SQLiteStorage(":memory:"),       # In-memory for the demo
    project="quickstart",
    data_residency=DataResidency.LOCAL,
)


# 2. Decorate any function that makes an AI decision
@sentinel.trace
async def classify_support_ticket(ticket: str, customer_tier: str) -> dict:
    """
    In a real system, this would call an LLM.
    For the quickstart, we simulate the response.
    """
    # Simulated LLM response
    if "password" in ticket.lower():
        classification = "auth/password-reset"
        priority = "medium"
    elif any(w in ticket.lower() for w in ["billing", "charged", "invoice", "payment"]):
        classification = "billing/charge-dispute"
        priority = "high"
    else:
        classification = "general/enquiry"
        priority = "low"

    return {
        "classification": classification,
        "priority": priority,
        "requires_escalation": customer_tier == "enterprise" and priority == "high",
    }


async def main():
    print("🛡️  Sentinel Quickstart\n")
    print("Running three classified support tickets...\n")

    # 3. Call your agent as normal — Sentinel captures everything
    tickets = [
        ("I can't log in after resetting my password", "standard"),
        ("I was charged twice this month", "enterprise"),
        ("How do I export my data?", "standard"),
    ]

    for ticket_text, tier in tickets:
        result = await classify_support_ticket(ticket_text, customer_tier=tier)
        print(f"Ticket: '{ticket_text[:50]}'")
        print(f"Result: {result}\n")

    # 4. Query the decision traces
    print("=" * 60)
    print("Sovereign Decision Traces\n")

    traces = sentinel.query(project="quickstart", limit=10)

    for trace in traces:
        print(f"Trace ID:    {trace.trace_id}")
        print(f"Agent:       {trace.agent}")
        print(f"Latency:     {trace.latency_ms}ms")
        print(f"Residency:   {trace.data_residency.value}")
        print(f"Output:      {json.dumps(trace.output, indent=14)[1:-1].strip()}")
        print(f"Inputs hash: {trace.inputs_hash[:16]}...")
        print()

    print(f"✅  {len(traces)} decision traces captured and stored.")
    print(f"    Every AI decision your agent makes is now sovereign,")
    print(f"    auditable, and queryable — without leaving your infrastructure.")
    print()
    print("Next steps:")
    print("  • Replace the simulated LLM with a real model provider call")
    print("  • Add a policy: @sentinel.trace(policy='policies/my_policy.rego')")
    print("  • Switch to persistent storage: SQLiteStorage('./decisions.db')")
    print("  • Read the docs: https://github.com/sebastianweiss83/sentinel-kernel")


if __name__ == "__main__":
    asyncio.run(main())
