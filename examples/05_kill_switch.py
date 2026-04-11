"""
05 — Kill switch (EU AI Act Art. 14).

A human operator can halt all traced agent calls at runtime. No
restart. Every blocked call produces a DENY trace with a linked
HumanOverride entry naming the reason.

Run:
    python examples/05_kill_switch.py
"""

from sentinel import KillSwitchEngaged, PolicyResult, Sentinel
from sentinel.storage import SQLiteStorage


def main() -> None:
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="kill-switch-demo")

    @sentinel.trace
    def process(item: dict) -> dict:
        return {"processed": item["id"]}

    # Normal operation
    process({"id": 1})
    process({"id": 2})
    print("2 calls processed normally")

    # Operator halts the system
    sentinel.engage_kill_switch("Suspicious pattern — halt pending review")
    assert sentinel.kill_switch_active is True
    print("\n[kill switch ENGAGED]")

    # All subsequent calls are blocked
    blocked = 0
    for i in range(3):
        try:
            process({"id": i + 100})
        except KillSwitchEngaged:
            blocked += 1
    print(f"{blocked} calls blocked")

    # Review complete, operator resumes
    sentinel.disengage_kill_switch("Review complete, cleared")
    assert sentinel.kill_switch_active is False
    print("\n[kill switch DISENGAGED]")

    process({"id": 999})
    print("1 call processed normally")

    # Audit summary
    all_traces = sentinel.query(limit=100)
    deny_traces = sentinel.query(policy_result=PolicyResult.DENY, limit=100)
    print(f"\nTotal traces : {len(all_traces)}")
    print(f"DENY traces  : {len(deny_traces)}")
    for t in deny_traces:
        override = t.human_override
        assert override is not None
        print(f"  blocked by {override.approver_id}: {override.justification}")


if __name__ == "__main__":
    main()
