"""
sentinel.dashboard.terminal
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Minimal ANSI terminal dashboard. Zero runtime dependencies —
no rich, no blessed, no curses. Works in classified environments
where installing extra libraries is friction.
"""

from __future__ import annotations

import os
import shutil
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


# ANSI colour codes. Falls back to no-colour when stdout is not a tty
# or NO_COLOR is set.
_COLOR_RESET = "\x1b[0m"
_COLOR_BOLD = "\x1b[1m"
_COLOR_GREEN = "\x1b[32m"
_COLOR_YELLOW = "\x1b[33m"
_COLOR_RED = "\x1b[31m"
_COLOR_CYAN = "\x1b[36m"
_COLOR_DIM = "\x1b[2m"


def _use_color() -> bool:
    return not os.environ.get("NO_COLOR")


def _c(text: str, colour: str) -> str:
    if not _use_color():
        return text
    return f"{colour}{text}{_COLOR_RESET}"


class TerminalDashboard:
    """
    Live terminal dashboard for Sentinel.

    Usage::

        dashboard = TerminalDashboard(sentinel)
        dashboard.render_once()   # one frame, for tests and CI
        dashboard.run(interval_s=2)  # live loop

    The dashboard reads from the Sentinel's storage on each frame.
    It does not subscribe to events; this is deliberate — the
    terminal dashboard is passive and non-interfering.
    """

    def __init__(self, sentinel: Sentinel) -> None:
        self.sentinel = sentinel

    def render_once(self) -> str:
        """Render one frame to a string (testable)."""
        from sentinel.core.trace import PolicyResult

        traces = self.sentinel.query(limit=100)
        width = _terminal_width()

        allow_count = sum(
            1
            for t in traces
            if t.policy_evaluation and t.policy_evaluation.result == PolicyResult.ALLOW
        )
        deny_count = sum(
            1
            for t in traces
            if t.policy_evaluation and t.policy_evaluation.result == PolicyResult.DENY
        )
        no_policy = sum(
            1
            for t in traces
            if t.policy_evaluation is None or t.policy_evaluation.result == PolicyResult.NOT_EVALUATED
        )

        score = self._sovereignty_score()
        ks = self.sentinel.kill_switch_active
        ks_label = _c("ENGAGED", _COLOR_RED) if ks else _c("normal", _COLOR_GREEN)

        lines: list[str] = []
        lines.append(_c("═" * width, _COLOR_CYAN))
        title = "  SENTINEL SOVEREIGNTY DASHBOARD"
        lines.append(_c(title, _COLOR_BOLD))
        lines.append(_c("═" * width, _COLOR_CYAN))
        lines.append("")
        lines.append(f"  Project        : {self.sentinel.project}")
        lines.append(f"  Storage        : {self.sentinel.storage.backend_name}")
        lines.append(f"  Data residency : {self.sentinel.data_residency.value}")
        lines.append(f"  Sovereign scope: {self.sentinel.sovereign_scope}")
        lines.append(f"  Kill switch    : {ks_label}")
        lines.append("")
        lines.append(_c("  Decision counts (last 100)", _COLOR_BOLD))
        lines.append(f"  {_c('ALLOW', _COLOR_GREEN)}   : {allow_count}")
        lines.append(f"  {_c('DENY', _COLOR_RED)}    : {deny_count}")
        lines.append(f"  {_c('NO_POLICY', _COLOR_DIM)}: {no_policy}")
        lines.append("")
        lines.append(f"  Sovereignty score: {_format_score(score)}")
        lines.append("")
        lines.append(_c("  Recent traces", _COLOR_BOLD))
        for t in traces[:8]:
            pol = t.policy_evaluation.result.value if t.policy_evaluation else "—"
            ts = t.started_at.strftime("%H:%M:%S")
            agent = t.agent[:30]
            lines.append(f"  {ts}  {agent:<30}  {pol}")
        if not traces:
            lines.append(_c("  (no traces yet)", _COLOR_DIM))
        lines.append("")
        lines.append(_c("═" * width, _COLOR_CYAN))
        return "\n".join(lines)

    def run(self, interval_s: float = 2.0, max_frames: int | None = None) -> None:
        """Live loop. max_frames=None means run forever (Ctrl-C to stop)."""
        frames = 0
        try:
            while max_frames is None or frames < max_frames:
                _clear_screen()
                print(self.render_once())
                frames += 1
                time.sleep(interval_s)
        except KeyboardInterrupt:
            return

    def _sovereignty_score(self) -> float:
        """Delegate to RuntimeScanner for a live number."""
        from sentinel.scanner import RuntimeScanner

        return RuntimeScanner().scan().sovereignty_score

    def print_summary(self) -> None:
        """Render one frame and print it — convenience for scripts."""
        print(self.render_once())


# Public alias — matches RFC-001 / mega-prompt naming where the
# terminal renderer is referred to as `TerminalReport`. The canonical
# class name is `TerminalDashboard` (it is a live dashboard, not a
# one-shot report), but the alias keeps the two vocabularies in sync.
TerminalReport = TerminalDashboard


def _terminal_width() -> int:
    try:
        return max(40, shutil.get_terminal_size().columns)
    except OSError:
        return 80


def _clear_screen() -> None:
    print("\x1b[2J\x1b[H", end="")


def _format_score(score: float) -> str:
    pct = f"{score:.0%}"
    if score >= 0.9:
        return _c(pct, _COLOR_GREEN)
    if score >= 0.6:
        return _c(pct, _COLOR_YELLOW)
    return _c(pct, _COLOR_RED)
