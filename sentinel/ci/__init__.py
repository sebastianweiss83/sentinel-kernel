"""
sentinel.ci
~~~~~~~~~~~
One-stop CI/CD aggregator for Sentinel's existing checks.

Wraps the EU AI Act checker, the runtime sovereignty scanner, and
(optionally) a SentinelManifesto into a single pass/fail result with
an aggregate exit code suitable for a CI pipeline.

This module does not reimplement any check. It orchestrates existing
library APIs and is fully local — no subprocesses, no network.
"""

from sentinel.ci.checks import CICheckOutcome, CICheckResult, run_ci_checks

__all__ = ["CICheckOutcome", "CICheckResult", "run_ci_checks"]
