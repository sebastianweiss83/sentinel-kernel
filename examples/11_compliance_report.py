"""
11 — EU AI Act compliance report.

Runs the automated EU AI Act checker and prints the article diff.
Optionally writes an HTML report to disk.

Run:
    python examples/11_compliance_report.py
    python examples/11_compliance_report.py --html compliance.html
"""

from __future__ import annotations

import sys
from pathlib import Path

from sentinel import Sentinel
from sentinel.compliance import EUAIActChecker
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


def main() -> int:
    html_path: Path | None = None
    args = sys.argv[1:]
    if args and args[0] == "--html":
        if len(args) < 2:
            print("Usage: python examples/11_compliance_report.py --html PATH")
            return 2
        html_path = Path(args[1])

    def policy(inputs: dict) -> tuple[bool, str | None]:
        return True, None

    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="compliance-demo",
        policy_evaluator=SimpleRuleEvaluator({"p.py": policy}),
    )

    @sentinel.trace(policy="p.py")
    def example_decision(input: dict) -> dict:
        return {"decision": "approved"}

    example_decision(input={"x": 1})
    example_decision(input={"x": 2})

    report = EUAIActChecker().check(sentinel)

    print(report.as_text())
    print()
    print("=" * 64)
    print("  DIFF — only the gaps")
    print("=" * 64)
    print(report.diff())

    if html_path:
        html_path.write_text(report.as_html(), encoding="utf-8")
        print(f"\nHTML report written to {html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
