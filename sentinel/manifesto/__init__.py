"""
sentinel.manifesto
~~~~~~~~~~~~~~~~~~
Manifesto-as-code — express your organisation's sovereignty
requirements as Python classes, then check reality against them.
"""

from sentinel.manifesto.base import (
    AcknowledgedGap,
    AuditTrailIntegrity,
    BSIProfile,
    DimensionStatus,
    EUOnly,
    Gap,
    GDPRCompliant,
    ManifestoReport,
    MigrationPlan,
    OnPremiseOnly,
    Required,
    RetentionPolicy,
    SentinelManifesto,
    Targeting,
    VSNfDReady,
    ZeroExposure,
)

__all__ = [
    "SentinelManifesto",
    "EUOnly",
    "OnPremiseOnly",
    "Required",
    "ZeroExposure",
    "Targeting",
    "AcknowledgedGap",
    "GDPRCompliant",
    "RetentionPolicy",
    "AuditTrailIntegrity",
    "BSIProfile",
    "VSNfDReady",
    "ManifestoReport",
    "Gap",
    "DimensionStatus",
    "MigrationPlan",
]
