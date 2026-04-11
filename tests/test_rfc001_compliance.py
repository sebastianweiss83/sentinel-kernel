"""
tests/test_rfc001_compliance.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Validate that a realistic manifesto matches the RFC-001 specification.

The RFC-001 spec defines the required shape of a ``ManifestoReport``:

    - ``timestamp``             (ISO 8601 string)
    - ``overall_score``         (float in [0.0, 1.0])
    - ``days_to_enforcement``   (int)
    - ``sovereignty_dimensions`` (dict of name → dimension-status)
    - ``eu_ai_act_articles``    (dict of article → status string)
    - ``gaps``                  (list)
    - ``acknowledged_gaps``     (list)
    - ``migration_plans``       (list)

Each ``sovereignty_dimensions`` entry must have: name, expected,
satisfied, detail. Each ``acknowledged_gaps`` entry must have: kind,
provider, migrating_to, by, reason.

These assertions are the implementation's contract with the RFC.
If the shape drifts from the spec, this test fails.
"""

from __future__ import annotations

from sentinel.manifesto import (
    AcknowledgedGap,
    BSIProfile,
    EUOnly,
    GDPRCompliant,
    Required,
    RetentionPolicy,
    SentinelManifesto,
)


class _RFC001Policy(SentinelManifesto):
    jurisdiction = EUOnly()
    kill_switch = Required()
    gdpr = GDPRCompliant()
    retention = RetentionPolicy(max_days=2555)
    bsi = BSIProfile(status="pursuing", by="2026-Q4", evidence="docs/bsi-profile.md")
    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No EU-sovereign CI with comparable UX yet",
    )


def _make_sentinel():
    from sentinel import DataResidency, Sentinel
    from sentinel.storage import SQLiteStorage

    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="rfc001-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )


def test_rfc001_report_has_required_top_level_keys() -> None:
    report = _RFC001Policy().check(sentinel=_make_sentinel())
    data = report.as_dict()

    for key in (
        "timestamp",
        "overall_score",
        "days_to_enforcement",
        "sovereignty_dimensions",
        "eu_ai_act_articles",
        "gaps",
        "acknowledged_gaps",
        "migration_plans",
    ):
        assert key in data, f"RFC-001 key missing: {key}"


def test_rfc001_overall_score_is_in_range() -> None:
    report = _RFC001Policy().check(sentinel=_make_sentinel())
    assert 0.0 <= report.overall_score <= 1.0


def test_rfc001_dimensions_have_required_fields() -> None:
    report = _RFC001Policy().check(sentinel=_make_sentinel())
    assert report.sovereignty_dimensions, "Expected at least one dimension"
    for dim in report.sovereignty_dimensions.values():
        d = dim.to_dict()
        assert set(d.keys()) >= {"name", "expected", "satisfied", "detail"}
        assert isinstance(d["satisfied"], bool)


def test_rfc001_acknowledged_gaps_have_all_mandatory_fields() -> None:
    report = _RFC001Policy().check(sentinel=_make_sentinel())
    assert report.acknowledged_gaps, "Expected the CI/CD acknowledged gap"
    for ack in report.acknowledged_gaps:
        d = ack.as_dict()
        # RFC-001 §7: mandatory fields on AcknowledgedGap
        assert d["kind"] == "acknowledged_gap"
        assert d["provider"]
        assert d["migrating_to"]
        assert d["by"]
        assert d["reason"]


def test_rfc001_ci_cd_gap_not_reported_as_violation() -> None:
    report = _RFC001Policy().check(sentinel=_make_sentinel())
    # Acknowledged gaps must never appear in the `gaps` list
    gap_dims = {g.dimension for g in report.gaps}
    assert "ci_cd" not in gap_dims


def test_rfc001_report_is_json_serialisable() -> None:
    import json

    report = _RFC001Policy().check(sentinel=_make_sentinel())
    payload = report.as_json()
    data = json.loads(payload)
    # Round-trip check
    assert data["overall_score"] == round(report.overall_score, 3)
    assert data["days_to_enforcement"] == report.days_to_enforcement


def test_rfc001_eu_ai_act_articles_mention_key_articles() -> None:
    report = _RFC001Policy().check(sentinel=_make_sentinel())
    articles = report.eu_ai_act_articles
    for art in ("Art. 12", "Art. 13", "Art. 14"):
        assert art in articles, f"Expected {art} in EU AI Act articles"
