"""
tests/test_compliance.py
~~~~~~~~~~~~~~~~~~~~~~~~
Tests for the EU AI Act automated compliance checker.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sentinel import Sentinel
from sentinel.compliance import EUAIActChecker
from sentinel.compliance.euaiact import ENFORCEMENT_DATE
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


def _make_sentinel(*, with_policy: bool = True) -> Sentinel:
    policy_eval = None
    if with_policy:
        def p(inputs: dict) -> tuple[bool, str | None]:
            return True, None
        policy_eval = SimpleRuleEvaluator({"p.py": p})
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="compliance-test",
        policy_evaluator=policy_eval,
    )


def test_art12_passes_with_traces_written() -> None:
    sentinel = _make_sentinel()
    report = EUAIActChecker().check(sentinel)
    assert report.articles["Art. 12"].status == "COMPLIANT"


def test_art14_passes_with_kill_switch() -> None:
    sentinel = _make_sentinel()
    report = EUAIActChecker().check(sentinel)
    assert report.articles["Art. 14"].status == "COMPLIANT"


def test_art14_fails_without_kill_switch() -> None:
    """Simulate a Sentinel without a kill switch by stripping the methods."""
    sentinel = _make_sentinel()

    class Stub:
        def __init__(self, s: Sentinel) -> None:
            self.storage = s.storage
            self.policy_evaluator = s.policy_evaluator
        # No engage_kill_switch / disengage_kill_switch

    report = EUAIActChecker().check(Stub(sentinel))  # type: ignore[arg-type]
    assert report.articles["Art. 14"].status == "NON_COMPLIANT"


def test_art9_partial_with_policy() -> None:
    report = EUAIActChecker().check(_make_sentinel(with_policy=True))
    assert report.articles["Art. 9"].status == "PARTIAL"


def test_art9_partial_without_policy() -> None:
    report = EUAIActChecker().check(_make_sentinel(with_policy=False))
    assert report.articles["Art. 9"].status == "PARTIAL"


def test_honest_about_non_automatable_articles() -> None:
    report = EUAIActChecker().check(_make_sentinel())
    for art_id in ("Art. 10", "Art. 11", "Art. 15"):
        art = report.articles[art_id]
        assert art.automated is False
        assert art.status == "ACTION_REQUIRED"
        assert art.human_action is not None


def test_compliance_report_html_generation() -> None:
    report = EUAIActChecker().check(_make_sentinel())
    html = report.as_html()
    assert "<html" in html
    assert "EU AI Act Compliance Report" in html
    # self-contained: no external network loads
    assert "src=\"http" not in html
    assert "href=\"http" not in html
    assert "cdn." not in html


def test_compliance_report_json_export(tmp_path: Path) -> None:
    report = EUAIActChecker().check(_make_sentinel())
    out = tmp_path / "compliance.json"
    report.export_json(out)
    data = json.loads(out.read_text())
    assert data["overall"] in ("COMPLIANT", "PARTIAL", "NON_COMPLIANT")
    assert "Art. 12" in data["articles"]
    assert "human_action_required" in data


def test_days_to_enforcement_correct() -> None:
    report = EUAIActChecker().check(_make_sentinel())
    expected = (ENFORCEMENT_DATE - date.today()).days
    assert report.days_to_enforcement == expected


def test_diff_shows_only_gaps() -> None:
    sentinel = _make_sentinel()
    report = EUAIActChecker().check(sentinel)
    diff = report.diff()
    assert "COMPLIANT" not in diff or diff.count("COMPLIANT") == 0
    # Art 10/11/15 should show up as gaps
    assert "Art. 10" in diff
    assert "Art. 11" in diff
    assert "Art. 15" in diff
    # Art 12 should NOT show up (it's COMPLIANT in this config)
    assert "Art. 12" not in diff


def test_overall_is_partial_when_gaps_present() -> None:
    report = EUAIActChecker().check(_make_sentinel())
    assert report.overall == "PARTIAL"


def test_overall_non_compliant_when_core_article_fails() -> None:
    """Cover the NON_COMPLIANT return branch (euaiact.py line 89)."""
    report = EUAIActChecker().check(_make_sentinel())
    # Force a core article to NON_COMPLIANT
    report.articles["Art. 12"].status = "NON_COMPLIANT"
    assert report.overall == "NON_COMPLIANT"


def test_overall_compliant_when_all_articles_pass() -> None:
    """Cover the COMPLIANT return branch (euaiact.py line 92)."""
    report = EUAIActChecker().check(_make_sentinel())
    for art in report.articles.values():
        art.status = "COMPLIANT"
    assert report.overall == "COMPLIANT"


def test_automated_coverage_nonzero() -> None:
    report = EUAIActChecker().check(_make_sentinel())
    assert 0.0 < report.automated_coverage < 1.0
