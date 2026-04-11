//! Runnable example: `cargo run --example basic`
//!
//! Shows three industry scenarios end-to-end.

use sentinel_manifest::{
    AcknowledgedGap, AirGapRequired, EUJurisdiction, SovereigntyManifest, Targeting,
    ZeroCloudActExposure,
};

fn main() {
    for report in [
        defence_scenario(),
        healthcare_scenario(),
        enterprise_scenario(),
    ] {
        println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        println!("  {}", report.name);
        println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        println!("  Overall score: {:.0}%", report.overall_score * 100.0);
        for r in &report.requirements {
            println!("  - {} [{:?}]", r.name, r.status);
            println!("    {}", r.detail);
        }
        println!();
    }
}

fn defence_scenario() -> sentinel_manifest::ManifestoReport {
    SovereigntyManifest::new("Defence — VS-NfD target")
        .add(Box::new(EUJurisdiction::new()))
        .add(Box::new(AirGapRequired::new()))
        .add(Box::new(ZeroCloudActExposure::new()))
        .add(Box::new(Targeting::new("VS-NfD deployment", "2027-Q1")))
        .check()
}

fn healthcare_scenario() -> sentinel_manifest::ManifestoReport {
    SovereigntyManifest::new("Healthcare — GDPR + MDR")
        .add(Box::new(EUJurisdiction::new()))
        .add(Box::new(AirGapRequired::new()))
        .add(Box::new(AcknowledgedGap::new(
            "Clinical dashboard SaaS",
            "Replacement not yet selected",
            "Self-hosted Grafana",
            "2027-Q2",
        )))
        .check()
}

fn enterprise_scenario() -> sentinel_manifest::ManifestoReport {
    SovereigntyManifest::new("Enterprise — EU AI Act ready")
        .add(Box::new(EUJurisdiction::new()))
        .add(Box::new(ZeroCloudActExposure::new()))
        .add(Box::new(AcknowledgedGap::new(
            "GitHub Actions",
            "No production-ready EU alternative today",
            "Self-hosted Forgejo",
            "2027-Q2",
        )))
        .check()
}
