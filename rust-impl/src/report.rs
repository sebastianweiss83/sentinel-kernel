//! Report structures produced by a manifesto check.

use serde::{Deserialize, Serialize};
use std::io;
use std::path::Path;

/// Status of an individual requirement after evaluation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RequirementStatus {
    /// Hard requirement fully met.
    Compliant,
    /// Partially met — migration plan in progress.
    Partial,
    /// Hard requirement violated.
    Violation,
    /// Acknowledged gap with a documented migration plan.
    Acknowledged,
    /// Statement of intent — tracked but not gated.
    Targeting,
}

/// Result of evaluating a single requirement.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequirementResult {
    pub name: String,
    pub status: RequirementStatus,
    pub detail: String,
    pub remediation: Option<String>,
    pub deadline: Option<String>,
}

/// Full manifesto report — compatible with the Python JSON shape.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestoReport {
    pub name: String,
    pub requirements: Vec<RequirementResult>,
    pub overall_score: f64,
    pub acknowledged_gaps: Vec<String>,
    pub generated_at: String,
}

impl ManifestoReport {
    /// Serialise the report as pretty-printed JSON.
    pub fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_else(|_| "{}".to_string())
    }

    /// Save the report to a file as JSON.
    pub fn save_json(&self, path: &str) -> io::Result<()> {
        std::fs::write(Path::new(path), self.to_json())
    }

    /// Fraction of requirements considered compliant (0.0–1.0).
    pub fn compliant_ratio(&self) -> f64 {
        if self.requirements.is_empty() {
            return 1.0;
        }
        let compliant = self
            .requirements
            .iter()
            .filter(|r| matches!(r.status, RequirementStatus::Compliant))
            .count() as f64;
        compliant / self.requirements.len() as f64
    }
}
