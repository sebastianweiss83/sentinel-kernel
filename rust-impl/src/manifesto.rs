//! The top-level SovereigntyManifest builder.

use chrono::Utc;

use crate::report::{ManifestoReport, RequirementResult, RequirementStatus};
use crate::requirements::Requirement;

/// Build a manifesto by chaining requirements, then call [`check`].
///
/// [`check`]: SovereigntyManifest::check
pub struct SovereigntyManifest {
    name: String,
    requirements: Vec<Box<dyn Requirement>>,
}

impl SovereigntyManifest {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            requirements: Vec::new(),
        }
    }

    pub fn add(mut self, requirement: Box<dyn Requirement>) -> Self {
        self.requirements.push(requirement);
        self
    }

    pub fn check(&self) -> ManifestoReport {
        let results: Vec<RequirementResult> = self.requirements.iter().map(|r| r.check()).collect();

        let acknowledged_gaps: Vec<String> = results
            .iter()
            .filter(|r| matches!(r.status, RequirementStatus::Acknowledged))
            .map(|r| r.detail.clone())
            .collect();

        let overall_score = compute_score(&results);

        ManifestoReport {
            name: self.name.clone(),
            requirements: results,
            overall_score,
            acknowledged_gaps,
            generated_at: Utc::now().to_rfc3339(),
        }
    }
}

fn compute_score(results: &[RequirementResult]) -> f64 {
    if results.is_empty() {
        return 1.0;
    }
    let mut weighted = 0.0_f64;
    let mut denominator = 0.0_f64;
    for r in results {
        let (value, weight) = match r.status {
            RequirementStatus::Compliant => (1.0, 1.0),
            RequirementStatus::Partial => (0.5, 1.0),
            RequirementStatus::Violation => (0.0, 1.0),
            RequirementStatus::Acknowledged => (1.0, 0.5),
            RequirementStatus::Targeting => (0.75, 0.5),
        };
        weighted += value * weight;
        denominator += weight;
    }
    if denominator == 0.0 {
        1.0
    } else {
        weighted / denominator
    }
}
