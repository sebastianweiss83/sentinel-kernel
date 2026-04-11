"""
sentinel.scanner
~~~~~~~~~~~~~~~~
Sovereignty scanners.

Three layers, one question: where is this system exposed?

    RuntimeScanner        — installed Python packages
    CICDScanner           — GitHub Actions, Dockerfiles, CI providers
    InfrastructureScanner — Terraform, Kubernetes, cloud env configs
"""

from sentinel.scanner.cicd import CICDScanner, CICDScanResult
from sentinel.scanner.infrastructure import InfraScanResult, InfrastructureScanner
from sentinel.scanner.runtime import (
    PackageReport,
    RuntimeScanner,
    ScanResult,
)

__all__ = [
    "RuntimeScanner",
    "ScanResult",
    "PackageReport",
    "CICDScanner",
    "CICDScanResult",
    "InfrastructureScanner",
    "InfraScanResult",
]
