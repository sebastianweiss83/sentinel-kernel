"""
sentinel.manifesto
~~~~~~~~~~~~~~~~~~
Manifesto-as-code — express your organisation's sovereignty
requirements as Python classes, then check reality against them.
"""

from sentinel.manifesto.base import (
    AcknowledgedGap,
    DimensionStatus,
    EUOnly,
    Gap,
    ManifestoReport,
    MigrationPlan,
    OnPremiseOnly,
    Required,
    SentinelManifesto,
    Targeting,
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
    "ManifestoReport",
    "Gap",
    "DimensionStatus",
    "MigrationPlan",
]
