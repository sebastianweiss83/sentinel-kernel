"""
03 — Simple Python-callable policy.

SimpleRuleEvaluator runs any Python callable as a policy. Each rule
returns (allowed: bool, rule_triggered: str | None). ALLOW decisions
record no rule; DENY decisions record the rule name so an auditor can
reconstruct why a call was blocked.

Run:
    python examples/03_policy_simple_rule.py
"""

from sentinel import PolicyDeniedError, PolicyResult, Sentinel
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


def amount_cap(inputs: dict) -> tuple[bool, str | None]:
    request = inputs.get("request", {})
    amount = request.get("amount", 0)
    if amount > 10_000:
        return False, "amount_exceeds_cap"
    return True, None


def main() -> None:
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="simple-rule-demo",
        policy_evaluator=SimpleRuleEvaluator({"policies/approval.py": amount_cap}),
    )

    @sentinel.trace(policy="policies/approval.py")
    def approve(request: dict) -> dict:
        return {"decision": "approved", "amount": request["amount"]}

    # ALLOW — under cap
    approve(request={"amount": 3_000, "requester": "alice"})

    # DENY — over cap
    try:
        approve(request={"amount": 50_000, "requester": "bob"})
    except PolicyDeniedError as exc:
        print(f"Policy blocked: {exc}")

    allows = sentinel.query(policy_result=PolicyResult.ALLOW, limit=10)
    denies = sentinel.query(policy_result=PolicyResult.DENY, limit=10)
    print(f"\n  ALLOW traces: {len(allows)}")
    print(f"  DENY  traces: {len(denies)}")
    if denies:
        deny = denies[0]
        assert deny.policy_evaluation is not None
        print(f"  DENY rule   : {deny.policy_evaluation.rule_triggered}")


if __name__ == "__main__":
    main()
