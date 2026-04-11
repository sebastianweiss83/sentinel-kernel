"""
sentinel.dashboard
~~~~~~~~~~~~~~~~~~
Terminal dashboard and self-contained HTML report generator.
Both zero-dependency and air-gapped safe.
"""

from sentinel.dashboard.html import HTMLReport
from sentinel.dashboard.terminal import TerminalDashboard

__all__ = ["TerminalDashboard", "HTMLReport"]
