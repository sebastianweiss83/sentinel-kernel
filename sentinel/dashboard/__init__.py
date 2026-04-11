"""
sentinel.dashboard
~~~~~~~~~~~~~~~~~~
Terminal dashboard and self-contained HTML report generator.
Both zero-dependency and air-gapped safe.
"""

from sentinel.dashboard.html import HTMLReport
from sentinel.dashboard.terminal import TerminalDashboard, TerminalReport

__all__ = ["TerminalDashboard", "TerminalReport", "HTMLReport"]
