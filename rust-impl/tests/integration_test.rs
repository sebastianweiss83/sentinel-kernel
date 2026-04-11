//! Integration tests for sentinel-manifest.

use sentinel_manifest::{
    AcknowledgedGap, AirGapRequired, EUJurisdiction, RequirementStatus, SovereigntyManifest,
    Targeting, ZeroCloudActExposure,
};

#[test]
fn empty_manifesto_has_perfect_score() {
    let report = SovereigntyManifest::new("empty").check();
    assert!((report.overall_score - 1.0).abs() < f64::EPSILON);
    assert!(report.requirements.is_empty());
}

#[test]
fn compliant_requirements_produce_full_score() {
    let report = SovereigntyManifest::new("all compliant")
        .add(Box::new(EUJurisdiction::new()))
        .add(Box::new(AirGapRequired::new()))
        .add(Box::new(ZeroCloudActExposure::new()))
        .check();
    assert_eq!(report.requirements.len(), 3);
    assert!((report.overall_score - 1.0).abs() < f64::EPSILON);
    for r in &report.requirements {
        assert!(matches!(r.status, RequirementStatus::Compliant));
    }
}

#[test]
fn acknowledged_gap_is_not_a_violation() {
    let report = SovereigntyManifest::new("gap")
        .add(Box::new(EUJurisdiction::new()))
        .add(Box::new(AcknowledgedGap::new(
            "GitHub Actions",
            "No EU alternative",
            "Self-hosted Forgejo",
            "2027-Q2",
        )))
        .check();

    assert_eq!(report.acknowledged_gaps.len(), 1);
    let gap = &report.requirements[1];
    assert!(matches!(gap.status, RequirementStatus::Acknowledged));
    assert_eq!(gap.deadline.as_deref(), Some("2027-Q2"));
}

#[test]
fn targeting_is_tracked_but_soft() {
    let report = SovereigntyManifest::new("targeting")
        .add(Box::new(Targeting::new("BSI assessment", "2026-Q4")))
        .check();
    assert!(matches!(
        report.requirements[0].status,
        RequirementStatus::Targeting
    ));
    // Targeting alone produces a score below 1.0 — it's a statement
    // of intent, not a completed objective.
    assert!(report.overall_score < 1.0);
}

#[test]
fn report_json_round_trip() {
    let report = SovereigntyManifest::new("round trip")
        .add(Box::new(EUJurisdiction::new()))
        .check();
    let json = report.to_json();
    let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
    assert_eq!(parsed["name"], "round trip");
    assert!(parsed["requirements"].is_array());
    assert!(parsed["overall_score"].is_number());
}

#[test]
fn compliant_ratio_reports_partial_results() {
    let report = SovereigntyManifest::new("mixed")
        .add(Box::new(EUJurisdiction::new()))
        .add(Box::new(Targeting::new("BSI", "2026-Q4")))
        .check();
    assert!(report.compliant_ratio() > 0.0);
    assert!(report.compliant_ratio() < 1.0);
}
