"""
sentinel.compliance
~~~~~~~~~~~~~~~~~~~
Automated EU AI Act compliance checker with honest gap reporting.
"""

from sentinel.compliance.euaiact import (
    ArticleReport,
    ComplianceReport,
    EUAIActChecker,
    HumanActionItem,
)

__all__ = [
    "EUAIActChecker",
    "ComplianceReport",
    "ArticleReport",
    "HumanActionItem",
]
