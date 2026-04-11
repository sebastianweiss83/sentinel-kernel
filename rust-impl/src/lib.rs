//! Rust implementation of RFC-001 SovereigntyManifest.
//!
//! Portable spec for declaring sovereignty requirements and checking
//! them against reality. Compatible with the Python reference
//! implementation in [`sentinel-kernel`](https://github.com/sebastianweiss83/sentinel-kernel).
//!
//! # Example
//!
//! ```
//! use sentinel_manifest::{SovereigntyManifest, EUJurisdiction, AirGapRequired};
//!
//! let report = SovereigntyManifest::new("My Policy v1")
//!     .add(Box::new(EUJurisdiction::new()))
//!     .add(Box::new(AirGapRequired::new()))
//!     .check();
//!
//! assert!(report.overall_score >= 0.0 && report.overall_score <= 1.0);
//! ```

pub mod manifesto;
pub mod report;
pub mod requirements;

pub use manifesto::SovereigntyManifest;
pub use report::{ManifestoReport, RequirementResult, RequirementStatus};
pub use requirements::{
    AcknowledgedGap, AirGapRequired, EUJurisdiction, Requirement, Targeting, ZeroCloudActExposure,
};
