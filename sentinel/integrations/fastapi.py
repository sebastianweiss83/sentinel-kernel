"""
sentinel.integrations.fastapi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FastAPI middleware for Sentinel.

Automatically traces every API endpoint that handles AI decisions.

Sovereignty posture:
  - FastAPI: open source (Sebastián Ramírez, Spain / Encode / OSS)
  - Jurisdiction: Neutral
  - CLOUD Act exposure: None
  - Air-gap capable: Yes
  - Runtime network calls: None (middleware only observes request/response)
  - Critical path: No — the middleware is additive

Install: pip install sentinel-kernel[fastapi]

Usage::

    from fastapi import FastAPI
    from sentinel import Sentinel
    from sentinel.integrations.fastapi import SentinelMiddleware

    app = FastAPI()
    sentinel = Sentinel()
    app.add_middleware(
        SentinelMiddleware,
        sentinel=sentinel,
        path_prefixes=["/decisions", "/approve"],
    )

    @app.post("/decisions/approve")
    async def approve(amount: int) -> dict:
        # automatically traced
        return {"approved": amount < 10_000}
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from sentinel.core.trace import DecisionTrace

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


_MISSING_DEP_MESSAGE = (
    "SentinelMiddleware requires starlette (installed with FastAPI).\n"
    "Install the extra:\n"
    "    pip install sentinel-kernel[fastapi]"
)


def _import_starlette_base() -> Any:
    try:
        from starlette.middleware.base import BaseHTTPMiddleware
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc
    return BaseHTTPMiddleware


# Resolve at import time so the class inherits from the real base
# when available; fall back to a marker for environments without
# the dep.
try:  # pragma: no cover - environment dependent
    from starlette.middleware.base import (
        BaseHTTPMiddleware as _BaseHTTPMiddleware,
    )
    _HAS_STARLETTE = True
except ImportError:  # pragma: no cover - hit only when extra not installed
    _HAS_STARLETTE = False

    class _BaseHTTPMiddleware:  # type: ignore[no-redef]
        """Stub base class used when starlette is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass


#: Default path prefixes that are always skipped (health probes, metrics).
DEFAULT_SKIP_PREFIXES: tuple[str, ...] = (
    "/health",
    "/healthz",
    "/readyz",
    "/livez",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
)


class SentinelMiddleware(_BaseHTTPMiddleware):
    """
    Starlette/FastAPI middleware that records a DecisionTrace per request.

    Args:
        app:            The ASGI app (passed automatically by FastAPI).
        sentinel:       The Sentinel instance to record traces on.
        path_prefixes:  If set, only record traces for requests whose
                        path starts with one of these prefixes. If
                        None, record every non-skipped request.
        skip_prefixes:  Path prefixes to always skip (defaults cover
                        health/metrics/docs endpoints).
    """

    def __init__(
        self,
        app: Any,
        sentinel: Sentinel,
        *,
        path_prefixes: list[str] | None = None,
        skip_prefixes: list[str] | None = None,
    ) -> None:
        if not _HAS_STARLETTE:
            raise ImportError(_MISSING_DEP_MESSAGE)
        super().__init__(app)
        self.sentinel = sentinel
        self.path_prefixes = path_prefixes
        self.skip_prefixes = tuple(skip_prefixes or DEFAULT_SKIP_PREFIXES)

    def _should_trace(self, path: str) -> bool:
        if path.startswith(self.skip_prefixes):
            return False
        if self.path_prefixes is None:
            return True
        return any(path.startswith(p) for p in self.path_prefixes)

    async def dispatch(self, request: Any, call_next: Any) -> Any:
        path = request.url.path
        if not self._should_trace(path):
            return await call_next(request)

        start = time.monotonic()
        response = None
        status_code = 0
        error: str | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:  # noqa: BLE001
            error = repr(exc)
            raise
        finally:
            latency_ms = int((time.monotonic() - start) * 1000)
            trace = DecisionTrace(
                project=self.sentinel.project,
                agent=f"fastapi.{request.method}.{path}",
                inputs={
                    "method": request.method,
                    "path": path,
                    "query": str(request.url.query or ""),
                },
                data_residency=self.sentinel.data_residency,
                sovereign_scope=self.sentinel.sovereign_scope,
                storage_backend=self.sentinel.storage.backend_name,
                tags={"integration": "fastapi"},
            )
            output: dict[str, Any] = {"status_code": status_code}
            if error is not None:
                output["error"] = error
            trace.complete(output=output, latency_ms=latency_ms)
            self.sentinel.storage.save(trace)
