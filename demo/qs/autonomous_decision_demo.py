"""
demo/qs/autonomous_decision_demo.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Quantum Systems demo — VTOL mission planning agent with full
Sentinel decision recording.

Scenario:
  An autonomous mission-planning agent receives mission parameters,
  evaluates go/no-go against a safety policy, and returns a decision.
  Sentinel wraps every call so the evidence record is produced
  automatically.

Demonstrates:
  - policy DENY (out of range, wind over limit)
  - kill switch engagement (Art. 14 human override)
  - sovereignty metadata on every trace
  - fully offline execution (no external network)

Run: python demo/qs/autonomous_decision_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sentinel import (
    DataResidency,
    KillSwitchEngaged,
    PolicyDeniedError,
    PolicyResult,
    Sentinel,
)
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import FilesystemStorage


# ---------------------------------------------------------------------------
# Safety policy
# ---------------------------------------------------------------------------

MAX_RANGE_KM = 300
MAX_WIND_KT = 25


def mission_safety_policy(inputs: dict) -> tuple[bool, str | None]:
    """Return (allow, rule_triggered)."""
    mission = inputs.get("mission", {})
    range_km = mission.get("range_km", 0)
    wind_kt = mission.get("wind_kt", 0)

    if range_km > MAX_RANGE_KM:
        return False, "out_of_range"
    if wind_kt > MAX_WIND_KT:
        return False, "wind_over_limit"
    return True, None


# ---------------------------------------------------------------------------
# Mocked mission planning "agent"
# ---------------------------------------------------------------------------


def make_agent(sentinel: Sentinel):
    @sentinel.trace(policy="policies/mission_safety.py", agent_name="vtol_mission_planner")
    def plan_mission(mission: dict) -> dict:
        # In a real deployment this would call a planning model or
        # a symbolic planner. Here we return a deterministic plan so
        # the demo is reproducible offline.
        return {
            "mission_id": mission["id"],
            "decision": "GO",
            "eta_minutes": int(mission["range_km"] / 1.5),
            "fuel_reserve_pct": 25,
        }
    return plan_mission


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------


def run_demo(traces_dir: Path) -> int:
    print("=" * 64)
    print("  QS AUTONOMOUS DECISION DEMO — VTOL mission planner")
    print("=" * 64)

    sentinel = Sentinel(
        storage=FilesystemStorage(str(traces_dir)),
        project="qs-vtol-demo",
        data_residency=DataResidency.AIR_GAPPED,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator(
            {"policies/mission_safety.py": mission_safety_policy}
        ),
    )

    plan_mission = make_agent(sentinel)

    missions = [
        {"id": "m1", "type": "transport", "range_km": 80,  "wind_kt": 12},
        {"id": "m2", "type": "transport", "range_km": 450, "wind_kt": 12},  # out_of_range
        {"id": "m3", "type": "recon",     "range_km": 120, "wind_kt": 35},  # wind_over_limit
    ]

    for m in missions:
        try:
            plan = plan_mission(mission=m)
            print(f"  {m['id']:3s} {m['type']:10s} {m['range_km']:>4d}km  "
                  f"wind {m['wind_kt']:>2d} kt  -> GO (eta {plan['eta_minutes']} min)")
        except PolicyDeniedError as exc:
            reason = str(exc).split("Rule:")[-1].strip().split(".")[0] if "Rule:" in str(exc) else "unknown"
            print(f"  {m['id']:3s} {m['type']:10s} {m['range_km']:>4d}km  "
                  f"wind {m['wind_kt']:>2d} kt  -> NO_GO ({reason})")

    print("  [human operator engages kill switch: 'ground all missions']")
    sentinel.engage_kill_switch("ground all missions — weather emergency declared")

    try:
        plan_mission(mission={"id": "m4", "type": "transport", "range_km": 80, "wind_kt": 10})
        print("  m4  BUG: kill switch did not block execution")
    except KillSwitchEngaged:
        print("  m4  transport    80km  wind 10 kt  -> BLOCKED (kill switch)")

    print("  [kill switch disengaged — weather clears]")
    sentinel.disengage_kill_switch("weather cleared, operations resume")
    plan = plan_mission(mission={"id": "m5", "type": "transport", "range_km": 80, "wind_kt": 10})
    print(f"  m5  transport    80km  wind 10 kt  -> GO (eta {plan['eta_minutes']} min)")

    # Query and report
    traces = sentinel.query(limit=100)
    deny_traces = sentinel.query(policy_result=PolicyResult.DENY, limit=100)
    allow_traces = sentinel.query(policy_result=PolicyResult.ALLOW, limit=100)

    from sentinel.scanner import RuntimeScanner
    score = RuntimeScanner().scan().sovereignty_score

    print()
    print("-" * 64)
    print(f"  Traces written       : {len(traces)}")
    print(f"    ALLOW              : {len(allow_traces)}")
    print(f"    DENY               : {len(deny_traces)}")
    print(f"  Sovereignty score    : {score:.0%}")
    print(f"  Storage              : {sentinel.storage.backend_name} ({traces_dir})")
    print(f"  Data residency       : {sentinel.data_residency.value}")
    print(f"  Sovereign scope      : {sentinel.sovereign_scope}")
    print("-" * 64)
    print()
    return 0


def main() -> int:
    traces_dir = Path("./qs-demo-traces")
    return run_demo(traces_dir)


if __name__ == "__main__":
    sys.exit(main())
