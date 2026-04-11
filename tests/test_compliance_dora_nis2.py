"""
tests/test_compliance_dora_nis2.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for DORA + NIS2 + unified compliance checkers.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sentinel import DataResidency, Sentinel
from sentinel.compliance import (
    DoraChecker,
    DoraReport,
    NIS2Checker,
    NIS2Report,
    UnifiedComplianceChecker,
)
from sentinel.compliance.dora import DORA_ENFORCEMENT_DATE
from sentinel.compliance.nis2 import NIS2_ENFORCEMENT_DATE
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


def _sentinel(tmp_path: Path, with_policy: bool = True) -> Sentinel:
    policy = None
    if with_policy:
        policy = SimpleRuleEvaluator({"p.py": lambda i: (True, None)})
    return Sentinel(
        storage=SQLiteStorage(str(tmp_path / "comp.db")),
        project="comp-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=policy,
    )


# ---------------------------------------------------------------------------
# DORA
# ---------------------------------------------------------------------------


def test_dora_check_compliant_with_storage_and_policy(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = DoraChecker().check(sentinel)
    assert report.articles["Art. 17"].status == "COMPLIANT"
    assert report.articles["Art. 6"].status == "PARTIAL"
    assert report.articles["Art. 28"].status == "ACTION_REQUIRED"
    assert report.articles["Art. 24"].status == "ACTION_REQUIRED"


def test_dora_check_partial_without_policy(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path, with_policy=False)
    report = DoraChecker().check(sentinel)
    assert report.articles["Art. 6"].status == "ACTION_REQUIRED"


def test_dora_overall_states(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = DoraChecker().check(sentinel)
    # Has at least one ACTION_REQUIRED → PARTIAL overall
    assert report.overall == "PARTIAL"


def test_dora_empty_report_overall_is_unknown() -> None:
    empty = DoraReport(timestamp=datetime.now())
    assert empty.overall == "UNKNOWN"


def test_dora_as_text_and_as_dict(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = DoraChecker().check(sentinel)
    text = report.as_text()
    assert "DORA COMPLIANCE REPORT" in text
    assert "Art. 17" in text
    data = report.as_dict()
    assert data["overall"] == "PARTIAL"
    assert "days_since_enforcement" in data


def test_dora_overall_compliant_when_all_articles_compliant() -> None:
    from sentinel.compliance.dora import DoraArticleReport, DoraReport

    report = DoraReport(timestamp=datetime.now())
    for art in ("Art. 17", "Art. 6", "Art. 28", "Art. 24"):
        report.articles[art] = DoraArticleReport(
            article=art, title="t", status="COMPLIANT", automated=True, detail="ok"
        )
    assert report.overall == "COMPLIANT"


def test_dora_overall_non_compliant_when_any_article_non_compliant() -> None:
    from sentinel.compliance.dora import DoraArticleReport, DoraReport

    report = DoraReport(timestamp=datetime.now())
    report.articles["Art. 17"] = DoraArticleReport(
        article="Art. 17", title="t", status="COMPLIANT", automated=True, detail="ok"
    )
    report.articles["Art. 6"] = DoraArticleReport(
        article="Art. 6", title="t", status="NON_COMPLIANT", automated=True, detail="bad"
    )
    assert report.overall == "NON_COMPLIANT"


def test_dora_days_since_enforcement_is_integer(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = DoraChecker().check(sentinel)
    # It should be an int, either positive (past) or negative (future)
    assert isinstance(report.days_since_enforcement, int)
    assert DORA_ENFORCEMENT_DATE.year == 2025


# ---------------------------------------------------------------------------
# NIS2
# ---------------------------------------------------------------------------


def test_nis2_check_partial_without_policy(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path, with_policy=False)
    report = NIS2Checker().check(sentinel)
    assert report.articles["Art. 21"].status == "PARTIAL"


def test_nis2_check_compliant_with_policy_and_kill_switch(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = NIS2Checker().check(sentinel)
    assert report.articles["Art. 21"].status == "COMPLIANT"
    assert report.articles["Art. 23"].status == "COMPLIANT"
    assert report.articles["Art. 20"].status == "ACTION_REQUIRED"
    assert report.articles["Art. 24"].status == "ACTION_REQUIRED"


def test_nis2_overall_states(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = NIS2Checker().check(sentinel)
    assert report.overall == "PARTIAL"


def test_nis2_empty_report_overall_unknown() -> None:
    empty = NIS2Report(timestamp=datetime.now())
    assert empty.overall == "UNKNOWN"


def test_nis2_overall_compliant_when_all_articles_compliant() -> None:
    from sentinel.compliance.nis2 import NIS2ArticleReport, NIS2Report

    report = NIS2Report(timestamp=datetime.now())
    for art in ("Art. 21", "Art. 23", "Art. 20", "Art. 24"):
        report.articles[art] = NIS2ArticleReport(
            article=art, title="t", status="COMPLIANT", automated=True, detail="ok"
        )
    assert report.overall == "COMPLIANT"


def test_nis2_overall_non_compliant_when_any_article_non_compliant() -> None:
    from sentinel.compliance.nis2 import NIS2ArticleReport, NIS2Report

    report = NIS2Report(timestamp=datetime.now())
    report.articles["Art. 21"] = NIS2ArticleReport(
        article="Art. 21", title="t", status="COMPLIANT", automated=True, detail="ok"
    )
    report.articles["Art. 23"] = NIS2ArticleReport(
        article="Art. 23", title="t", status="NON_COMPLIANT", automated=True, detail="bad"
    )
    assert report.overall == "NON_COMPLIANT"


def test_nis2_as_text_and_as_dict(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = NIS2Checker().check(sentinel)
    text = report.as_text()
    assert "NIS2 COMPLIANCE REPORT" in text
    assert "Art. 21" in text
    data = report.as_dict()
    assert data["overall"] == "PARTIAL"
    assert "days_since_enforcement" in data
    assert NIS2_ENFORCEMENT_DATE.year == 2024


# ---------------------------------------------------------------------------
# Unified
# ---------------------------------------------------------------------------


def test_unified_runs_only_eu_ai_act_by_default(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = UnifiedComplianceChecker().check(sentinel)
    assert report.dora is None
    assert report.nis2 is None
    assert "EU AI Act" in report.frameworks


def test_unified_with_financial_sector(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = UnifiedComplianceChecker(financial_sector=True).check(sentinel)
    assert report.dora is not None
    assert report.nis2 is None
    assert "DORA" in report.frameworks


def test_unified_with_critical_infrastructure(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = UnifiedComplianceChecker(critical_infrastructure=True).check(sentinel)
    assert report.nis2 is not None
    assert report.dora is None
    assert "NIS2" in report.frameworks


def test_unified_with_both_frameworks(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = UnifiedComplianceChecker(
        financial_sector=True,
        critical_infrastructure=True,
    ).check(sentinel)
    assert report.dora is not None
    assert report.nis2 is not None
    assert set(report.frameworks) == {"EU AI Act", "DORA", "NIS2"}


def test_unified_as_dict_contains_all_frameworks(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = UnifiedComplianceChecker(
        financial_sector=True,
        critical_infrastructure=True,
    ).check(sentinel)
    data = report.as_dict()
    assert "eu_ai_act" in data
    assert "dora" in data
    assert "nis2" in data


def test_unified_as_text_includes_all_sections(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = UnifiedComplianceChecker(
        financial_sector=True,
        critical_infrastructure=True,
    ).check(sentinel)
    text = report.as_text()
    assert "EU AI ACT COMPLIANCE REPORT" in text
    assert "DORA COMPLIANCE REPORT" in text
    assert "NIS2 COMPLIANCE REPORT" in text


def test_unified_save_html(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = UnifiedComplianceChecker(
        financial_sector=True,
        critical_infrastructure=True,
    ).check(sentinel)
    out = tmp_path / "unified.html"
    report.save_html(out)
    content = out.read_text()
    assert "<!doctype html>" in content
    assert "EU AI Act" in content
    assert "DORA" in content
    assert "NIS2" in content


def test_unified_save_html_eu_ai_only(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)
    report = UnifiedComplianceChecker().check(sentinel)
    out = tmp_path / "eu.html"
    report.save_html(out)
    content = out.read_text()
    # DORA / NIS2 headers are NOT in the HTML when not enabled
    assert "<h2>DORA</h2>" not in content
    assert "<h2>NIS2</h2>" not in content


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_dora_check_text(capsys) -> None:
    from sentinel import cli

    rc = cli.main(["dora", "check"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DORA COMPLIANCE REPORT" in out


def test_cli_dora_check_json(capsys) -> None:
    from sentinel import cli

    rc = cli.main(["dora", "check", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["overall"] in {"COMPLIANT", "PARTIAL", "NON_COMPLIANT"}


def test_cli_dora_without_subcommand_prints_help(capsys) -> None:
    from sentinel import cli

    rc = cli.main(["dora"])
    assert rc == 1


def test_cli_nis2_check_text(capsys) -> None:
    from sentinel import cli

    rc = cli.main(["nis2", "check"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "NIS2 COMPLIANCE REPORT" in out


def test_cli_nis2_check_json(capsys) -> None:
    from sentinel import cli

    rc = cli.main(["nis2", "check", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "overall" in data


def test_cli_nis2_without_subcommand_prints_help(capsys) -> None:
    from sentinel import cli

    rc = cli.main(["nis2"])
    assert rc == 1


def test_cli_compliance_check_all_frameworks_text(capsys) -> None:
    from sentinel import cli

    rc = cli.main(["compliance", "check", "--all-frameworks"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "EU AI ACT" in out
    assert "DORA" in out
    assert "NIS2" in out


def test_cli_compliance_check_all_frameworks_json(capsys) -> None:
    from sentinel import cli

    rc = cli.main(["compliance", "check", "--all-frameworks", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "eu_ai_act" in data
    assert "dora" in data
    assert "nis2" in data


def test_cli_compliance_check_all_frameworks_html_stdout(capsys) -> None:
    from sentinel import cli

    rc = cli.main(["compliance", "check", "--all-frameworks", "--html"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "<!doctype html>" in out


def test_cli_compliance_check_all_frameworks_html_to_file(
    tmp_path: Path, capsys
) -> None:
    from sentinel import cli

    out_path = tmp_path / "unified.html"
    rc = cli.main([
        "compliance", "check", "--all-frameworks", "--html",
        "--output", str(out_path),
    ])
    assert rc == 0
    assert out_path.exists()
    assert "<!doctype html>" in out_path.read_text()


def test_cli_compliance_check_financial_sector_text_to_file(
    tmp_path: Path, capsys
) -> None:
    from sentinel import cli

    out_path = tmp_path / "text.txt"
    rc = cli.main([
        "compliance", "check", "--financial-sector",
        "--output", str(out_path),
    ])
    assert rc == 0
    content = out_path.read_text()
    assert "DORA" in content


def test_cli_compliance_check_critical_infra_json_to_file(
    tmp_path: Path, capsys
) -> None:
    from sentinel import cli

    out_path = tmp_path / "ci.json"
    rc = cli.main([
        "compliance", "check", "--critical-infrastructure",
        "--json", "--output", str(out_path),
    ])
    assert rc == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert "nis2" in data
