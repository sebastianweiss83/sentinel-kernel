"""
sentinel.integrations.jupyter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Jupyter notebook integration for Sentinel.

Sovereignty posture:
  - Jupyter: open source (Project Jupyter / NumFOCUS), neutral
  - No CLOUD Act exposure when self-hosted
  - Air-gap capable: yes
  - Runtime network calls: none
  - Critical path: no

Install: pip install sentinel-kernel[jupyter]

Usage in a notebook cell::

    from sentinel import Sentinel
    from sentinel.integrations.jupyter import SentinelWidget

    sentinel = Sentinel()
    widget = SentinelWidget(sentinel=sentinel)
    widget.display()   # renders a live decision feed inline

    # ... run some agents ...
    widget.refresh()   # manually refresh the display
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


_MISSING_DEP_MESSAGE = (
    "SentinelWidget requires ipywidgets. Install the extra:\n"
    "    pip install sentinel-kernel[jupyter]"
)


def _import_ipywidgets() -> Any:
    try:
        import ipywidgets
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc
    return ipywidgets


class SentinelWidget:
    """
    Inline Jupyter widget for live decision feed.

    Wraps a Sentinel instance and renders the most recent traces
    as an HTML table inside a notebook cell. Call :meth:`refresh`
    to re-read from storage and update the display. Call
    :meth:`display` to render it into the current output area.

    The widget does **not** own a background thread. Notebooks are
    interactive — the user refreshes when they want to see new
    data.
    """

    def __init__(self, sentinel: Sentinel, *, limit: int = 20) -> None:
        _import_ipywidgets()
        self.sentinel = sentinel
        self.limit = limit
        self._widget = self._build_widget()

    def _build_widget(self) -> Any:
        ipywidgets = _import_ipywidgets()
        return ipywidgets.HTML(value=self._render_html())

    def _render_html(self) -> str:
        traces = self.sentinel.query(limit=self.limit)
        if not traces:
            return (
                "<i>No traces yet — run a @sentinel.trace-decorated "
                "function.</i>"
            )

        rows = []
        for t in traces:
            result = (
                t.policy_evaluation.result.value
                if t.policy_evaluation is not None
                else "NOT_EVALUATED"
            )
            rows.append(
                f"<tr>"
                f"<td>{t.started_at.strftime('%H:%M:%S')}</td>"
                f"<td>{_escape(t.agent)}</td>"
                f"<td>{result}</td>"
                f"<td>{t.latency_ms or 0} ms</td>"
                f"</tr>"
            )
        return (
            "<table style='border-collapse:collapse;font-family:monospace;'>"
            "<thead><tr>"
            "<th style='text-align:left;padding:4px 8px;'>Time</th>"
            "<th style='text-align:left;padding:4px 8px;'>Agent</th>"
            "<th style='text-align:left;padding:4px 8px;'>Result</th>"
            "<th style='text-align:right;padding:4px 8px;'>Latency</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    def refresh(self) -> None:
        """Re-query storage and update the widget HTML."""
        self._widget.value = self._render_html()

    def display(self) -> Any:
        """Render the widget into the current notebook output area."""
        try:
            from IPython.display import display as _display
        except ImportError as exc:
            raise ImportError(_MISSING_DEP_MESSAGE) from exc
        _display(self._widget)  # type: ignore[no-untyped-call]
        return self._widget

    def render_html(self) -> str:
        """Public accessor for the current rendered HTML (test hook)."""
        return self._render_html()


def _escape(text: str) -> str:
    """Minimal HTML escape — we don't want to pull a dep just for this."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
