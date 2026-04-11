//! Requirement types that map 1:1 onto RFC-001.
//!
//! Each requirement is a small struct implementing [`Requirement`]. The
//! [`SovereigntyManifest`] holds a heterogeneous list of them and calls
//! `check` on each when building a report.

use crate::report::{RequirementResult, RequirementStatus};

/// A single sovereignty requirement.
pub trait Requirement: Send + Sync {
    /// A short, stable name for the requirement (used in the report).
    fn name(&self) -> &'static str;

    /// Evaluate this requirement. Must be deterministic and network-free.
    fn check(&self) -> RequirementResult;
}

/// No US-owned critical-path components are allowed.
#[derive(Debug, Default, Clone)]
pub struct EUJurisdiction;

impl EUJurisdiction {
    pub fn new() -> Self {
        Self
    }
}

impl Requirement for EUJurisdiction {
    fn name(&self) -> &'static str {
        "eu_jurisdiction"
    }

    fn check(&self) -> RequirementResult {
        // In this language-neutral spec the check is declarative. A real
        // deployment would wire this up to a scanner that inspects the
        // runtime environment. The pure-Rust library only validates
        // that the requirement is well-formed.
        RequirementResult {
            name: self.name().to_string(),
            status: RequirementStatus::Compliant,
            detail: "EU-only requirement declared".to_string(),
            remediation: None,
            deadline: None,
        }
    }
}

/// Critical path must be capable of running fully offline.
#[derive(Debug, Default, Clone)]
pub struct AirGapRequired;

impl AirGapRequired {
    pub fn new() -> Self {
        Self
    }
}

impl Requirement for AirGapRequired {
    fn name(&self) -> &'static str {
        "air_gap_required"
    }

    fn check(&self) -> RequirementResult {
        RequirementResult {
            name: self.name().to_string(),
            status: RequirementStatus::Compliant,
            detail: "Air-gap requirement declared".to_string(),
            remediation: None,
            deadline: None,
        }
    }
}

/// Zero US CLOUD Act exposure in the critical path.
#[derive(Debug, Default, Clone)]
pub struct ZeroCloudActExposure;

impl ZeroCloudActExposure {
    pub fn new() -> Self {
        Self
    }
}

impl Requirement for ZeroCloudActExposure {
    fn name(&self) -> &'static str {
        "zero_cloud_act_exposure"
    }

    fn check(&self) -> RequirementResult {
        RequirementResult {
            name: self.name().to_string(),
            status: RequirementStatus::Compliant,
            detail: "Zero CLOUD Act exposure declared".to_string(),
            remediation: None,
            deadline: None,
        }
    }
}

/// A known gap with a documented migration plan.
#[derive(Debug, Clone)]
pub struct AcknowledgedGap {
    provider: String,
    reason: String,
    migrating_to: String,
    by: String,
}

impl AcknowledgedGap {
    pub fn new(
        provider: impl Into<String>,
        reason: impl Into<String>,
        migrating_to: impl Into<String>,
        by: impl Into<String>,
    ) -> Self {
        Self {
            provider: provider.into(),
            reason: reason.into(),
            migrating_to: migrating_to.into(),
            by: by.into(),
        }
    }

    pub fn provider(&self) -> &str {
        &self.provider
    }

    pub fn migrating_to(&self) -> &str {
        &self.migrating_to
    }

    pub fn by(&self) -> &str {
        &self.by
    }
}

impl Requirement for AcknowledgedGap {
    fn name(&self) -> &'static str {
        "acknowledged_gap"
    }

    fn check(&self) -> RequirementResult {
        RequirementResult {
            name: format!("acknowledged_gap:{}", self.provider),
            status: RequirementStatus::Acknowledged,
            detail: format!(
                "{} — migrating to {} by {}. Reason: {}",
                self.provider, self.migrating_to, self.by, self.reason
            ),
            remediation: Some(self.migrating_to.clone()),
            deadline: Some(self.by.clone()),
        }
    }
}

/// Statement of intent for a future milestone.
#[derive(Debug, Clone)]
pub struct Targeting {
    goal: String,
    by: String,
}

impl Targeting {
    pub fn new(goal: impl Into<String>, by: impl Into<String>) -> Self {
        Self {
            goal: goal.into(),
            by: by.into(),
        }
    }
}

impl Requirement for Targeting {
    fn name(&self) -> &'static str {
        "targeting"
    }

    fn check(&self) -> RequirementResult {
        RequirementResult {
            name: format!("targeting:{}", self.goal),
            status: RequirementStatus::Targeting,
            detail: format!("Targeting {} by {}", self.goal, self.by),
            remediation: None,
            deadline: Some(self.by.clone()),
        }
    }
}
