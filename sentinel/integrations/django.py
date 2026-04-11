"""
sentinel.integrations.django
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Django middleware for Sentinel.

Automatically traces every view/request that handles AI decisions.

Sovereignty posture:
  - Django: open source (Django Software Foundation, US non-profit)
  - Jurisdiction: US non-profit but governance is community-driven;
    CLOUD Act does not apply to an open source project foundation
    in the same way it applies to commercial providers.
  - CLOUD Act exposure: None in typical deployments — Django runs
    on your servers, the DSF never sees your traffic
  - Air-gap capable: Yes
  - Runtime network calls: None from the middleware itself
  - Critical path: No — the middleware is additive

Install: pip install sentinel-kernel[django]

Usage::

    # settings.py
    from sentinel import Sentinel
    from sentinel.integrations.django import SentinelMiddleware

    SENTINEL = Sentinel(project="my-django-app")

    MIDDLEWARE = [
        # ... other middleware ...
        "sentinel.integrations.django.SentinelMiddleware",
    ]

The middleware reads the Sentinel instance from
``settings.SENTINEL``. If no such setting exists it raises a
``django.core.exceptions.ImproperlyConfigured`` on the first
request (not at import time, so management commands still work).
"""

from __future__ import annotations

import time
from typing import Any

from sentinel.core.trace import DecisionTrace

_MISSING_DEP_MESSAGE = (
    "SentinelMiddleware requires Django. Install the extra:\n"
    "    pip install sentinel-kernel[django]"
)


def _import_django() -> Any:
    try:
        import django  # noqa: F401
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc
    return True


#: Path prefixes skipped by default — health probes, admin static.
DEFAULT_SKIP_PREFIXES: tuple[str, ...] = (
    "/health",
    "/healthz",
    "/static/",
    "/metrics",
)


class SentinelMiddleware:
    """
    Django middleware (new-style, callable) that records a
    :class:`DecisionTrace` for every non-skipped request.

    The middleware is stateless per request — instantiation happens
    once, and each call produces exactly one trace.
    """

    def __init__(self, get_response: Any) -> None:
        _import_django()
        self.get_response = get_response
        self._sentinel: Any | None = None

    def _resolve_sentinel(self) -> Any:
        if self._sentinel is not None:
            return self._sentinel
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured

        sentinel = getattr(settings, "SENTINEL", None)
        if sentinel is None:
            raise ImproperlyConfigured(
                "SentinelMiddleware requires settings.SENTINEL to be set to a "
                "Sentinel instance."
            )
        self._sentinel = sentinel
        return sentinel

    def _should_trace(self, path: str) -> bool:
        skip = getattr(
            self._resolve_sentinel(),
            "django_skip_prefixes",
            DEFAULT_SKIP_PREFIXES,
        )
        return not path.startswith(tuple(skip))

    def __call__(self, request: Any) -> Any:
        sentinel = self._resolve_sentinel()
        path = request.path
        if not self._should_trace(path):
            return self.get_response(request)

        start = time.monotonic()
        status_code = 0
        error: str | None = None
        response = None
        try:
            response = self.get_response(request)
            status_code = getattr(response, "status_code", 0)
            return response
        except Exception as exc:  # noqa: BLE001
            error = repr(exc)
            raise
        finally:
            latency_ms = int((time.monotonic() - start) * 1000)
            trace = DecisionTrace(
                project=sentinel.project,
                agent=f"django.{request.method}.{path}",
                inputs={
                    "method": request.method,
                    "path": path,
                },
                data_residency=sentinel.data_residency,
                sovereign_scope=sentinel.sovereign_scope,
                storage_backend=sentinel.storage.backend_name,
                tags={"integration": "django"},
            )
            output: dict[str, Any] = {"status_code": status_code}
            if error is not None:
                output["error"] = error
            trace.complete(output=output, latency_ms=latency_ms)
            sentinel.storage.save(trace)
