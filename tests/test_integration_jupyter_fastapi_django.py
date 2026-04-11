"""
tests/test_integration_jupyter_fastapi_django.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for Jupyter / FastAPI / Django integrations.

Each integration is guarded behind an importorskip so the suite
gracefully skips when the optional dep is not installed.
"""

from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.storage import SQLiteStorage


def _sentinel(tmp_path: Path) -> Sentinel:
    return Sentinel(
        storage=SQLiteStorage(str(tmp_path / "int.db")),
        project="int-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )


# ===========================================================================
# Jupyter
# ===========================================================================

pytest.importorskip("ipywidgets")


class TestJupyterWidget:
    def test_widget_import_guard(self, monkeypatch) -> None:
        import sentinel.integrations.jupyter as jp_mod

        original = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == "ipywidgets":
                raise ImportError("blocked")
            return original(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked)
        with pytest.raises(ImportError, match="sentinel-kernel\\[jupyter\\]"):
            jp_mod._import_ipywidgets()

    def test_widget_empty_feed(self, tmp_path: Path) -> None:
        from sentinel.integrations.jupyter import SentinelWidget

        sentinel = _sentinel(tmp_path)
        w = SentinelWidget(sentinel=sentinel)
        html = w.render_html()
        assert "No traces yet" in html

    def test_widget_renders_traces(self, tmp_path: Path) -> None:
        from sentinel.integrations.jupyter import SentinelWidget

        sentinel = _sentinel(tmp_path)

        @sentinel.trace
        def agent(x: int) -> dict:
            return {"x": x}

        for i in range(3):
            agent(x=i)

        w = SentinelWidget(sentinel=sentinel, limit=10)
        html = w.render_html()
        assert "<table" in html
        assert "agent" in html
        assert "NOT_EVALUATED" in html

    def test_widget_refresh_updates_html(self, tmp_path: Path) -> None:
        from sentinel.integrations.jupyter import SentinelWidget

        sentinel = _sentinel(tmp_path)
        w = SentinelWidget(sentinel=sentinel)
        before = w._widget.value

        @sentinel.trace
        def agent(x: int) -> dict:
            return {"x": x}

        agent(x=1)
        w.refresh()
        assert w._widget.value != before

    def test_widget_display_with_ipython(self, tmp_path: Path) -> None:
        pytest.importorskip("IPython")
        from sentinel.integrations.jupyter import SentinelWidget

        sentinel = _sentinel(tmp_path)
        w = SentinelWidget(sentinel=sentinel)
        returned = w.display()
        assert returned is not None

    def test_widget_display_raises_without_ipython(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from sentinel.integrations.jupyter import SentinelWidget

        sentinel = _sentinel(tmp_path)
        w = SentinelWidget(sentinel=sentinel)

        original = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == "IPython.display":
                raise ImportError("blocked")
            return original(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked)
        with pytest.raises(ImportError, match="sentinel-kernel\\[jupyter\\]"):
            w.display()

    def test_html_escape_helper(self) -> None:
        from sentinel.integrations.jupyter import _escape

        assert _escape("<script>") == "&lt;script&gt;"
        assert _escape('"&"') == "&quot;&amp;&quot;"


# ===========================================================================
# FastAPI / Starlette
# ===========================================================================

pytest.importorskip("starlette")


class TestFastAPIMiddleware:
    def test_middleware_import_guard(self, monkeypatch) -> None:
        import sentinel.integrations.fastapi as fa_mod

        original = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == "starlette.middleware.base":
                raise ImportError("blocked")
            return original(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked)
        with pytest.raises(ImportError, match="sentinel-kernel\\[fastapi\\]"):
            fa_mod._import_starlette_base()

    def test_middleware_import_returns_base_when_installed(self) -> None:
        import sentinel.integrations.fastapi as fa_mod

        base = fa_mod._import_starlette_base()
        assert base is not None

    def test_middleware_init_raises_when_starlette_missing(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Exercise the `raise ImportError` path at __init__ when
        _HAS_STARLETTE is False."""
        import sentinel.integrations.fastapi as fa_mod

        monkeypatch.setattr(fa_mod, "_HAS_STARLETTE", False)
        sentinel = _sentinel(tmp_path)
        with pytest.raises(ImportError, match="sentinel-kernel\\[fastapi\\]"):
            fa_mod.SentinelMiddleware(app=None, sentinel=sentinel)

    def test_middleware_records_trace(self, tmp_path: Path) -> None:
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from sentinel.integrations.fastapi import SentinelMiddleware

        sentinel = _sentinel(tmp_path)

        async def approve(request):  # noqa: ARG001
            return JSONResponse({"approved": True})

        app = Starlette(routes=[Route("/decisions/approve", approve, methods=["POST"])])
        app.add_middleware(SentinelMiddleware, sentinel=sentinel)

        client = TestClient(app)
        response = client.post("/decisions/approve", json={"amount": 100})
        assert response.status_code == 200

        traces = sentinel.query(limit=10)
        assert len(traces) == 1
        assert "fastapi.POST./decisions/approve" in traces[0].agent
        assert traces[0].tags["integration"] == "fastapi"

    def test_middleware_skips_health_endpoints(self, tmp_path: Path) -> None:
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from sentinel.integrations.fastapi import SentinelMiddleware

        sentinel = _sentinel(tmp_path)

        async def health(request):  # noqa: ARG001
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/health", health)])
        app.add_middleware(SentinelMiddleware, sentinel=sentinel)

        client = TestClient(app)
        client.get("/health")
        assert sentinel.query(limit=10) == []

    def test_middleware_respects_path_prefixes(self, tmp_path: Path) -> None:
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from sentinel.integrations.fastapi import SentinelMiddleware

        sentinel = _sentinel(tmp_path)

        async def other(request):  # noqa: ARG001
            return JSONResponse({"ok": True})

        async def decisions(request):  # noqa: ARG001
            return JSONResponse({"ok": True})

        app = Starlette(
            routes=[
                Route("/other", other),
                Route("/decisions/x", decisions),
            ]
        )
        app.add_middleware(
            SentinelMiddleware,
            sentinel=sentinel,
            path_prefixes=["/decisions"],
        )

        client = TestClient(app)
        client.get("/other")         # skipped by prefix filter
        client.get("/decisions/x")   # traced

        traces = sentinel.query(limit=10)
        assert len(traces) == 1
        assert "/decisions/x" in traces[0].agent

    def test_middleware_records_exception(self, tmp_path: Path) -> None:
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from sentinel.integrations.fastapi import SentinelMiddleware

        sentinel = _sentinel(tmp_path)

        async def crash(request):  # noqa: ARG001
            raise RuntimeError("boom")

        app = Starlette(routes=[Route("/decisions/crash", crash)])
        app.add_middleware(SentinelMiddleware, sentinel=sentinel)

        client = TestClient(app)
        with pytest.raises(RuntimeError):
            client.get("/decisions/crash")

        traces = sentinel.query(limit=10)
        assert len(traces) == 1
        assert "error" in traces[0].output


# ===========================================================================
# Django
# ===========================================================================

pytest.importorskip("django")


class TestDjangoMiddleware:
    def test_middleware_import_guard(self, monkeypatch) -> None:
        import sentinel.integrations.django as dj_mod

        original = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == "django":
                raise ImportError("blocked")
            return original(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked)
        with pytest.raises(ImportError, match="sentinel-kernel\\[django\\]"):
            dj_mod._import_django()

    def test_middleware_import_returns_true_when_installed(self) -> None:
        import sentinel.integrations.django as dj_mod

        assert dj_mod._import_django() is True

    def _configure_django(self, tmp_path: Path, sentinel: Sentinel) -> None:
        import django
        from django.conf import settings

        if not settings.configured:
            settings.configure(
                DEBUG=True,
                SECRET_KEY="test-key",
                ROOT_URLCONF="tests.test_integration_jupyter_fastapi_django",
                ALLOWED_HOSTS=["*"],
                MIDDLEWARE=[
                    "sentinel.integrations.django.SentinelMiddleware",
                ],
                DATABASES={},
                INSTALLED_APPS=[],
            )
            django.setup()
        settings.SENTINEL = sentinel

    def test_middleware_records_trace(self, tmp_path: Path) -> None:
        sentinel = _sentinel(tmp_path)
        self._configure_django(tmp_path, sentinel)

        from sentinel.integrations.django import SentinelMiddleware

        class _FakeRequest:
            method = "POST"
            path = "/decisions/approve"

        class _FakeResponse:
            status_code = 200

        def get_response(request):  # noqa: ARG001
            return _FakeResponse()

        mw = SentinelMiddleware(get_response)
        response = mw(_FakeRequest())
        assert response.status_code == 200

        traces = sentinel.query(limit=10)
        approve_traces = [t for t in traces if "/decisions/approve" in t.agent]
        assert len(approve_traces) >= 1
        assert approve_traces[0].tags["integration"] == "django"

    def test_middleware_skips_health(self, tmp_path: Path) -> None:
        sentinel = _sentinel(tmp_path)
        self._configure_django(tmp_path, sentinel)

        from sentinel.integrations.django import SentinelMiddleware

        class _FakeRequest:
            method = "GET"
            path = "/health"

        class _FakeResponse:
            status_code = 200

        baseline = len(sentinel.query(limit=100))
        mw = SentinelMiddleware(lambda r: _FakeResponse())
        mw(_FakeRequest())
        after = len(sentinel.query(limit=100))
        assert after == baseline

    def test_middleware_records_exception(self, tmp_path: Path) -> None:
        sentinel = _sentinel(tmp_path)
        self._configure_django(tmp_path, sentinel)

        from sentinel.integrations.django import SentinelMiddleware

        class _FakeRequest:
            method = "GET"
            path = "/decisions/crash"

        def boom(request):  # noqa: ARG001
            raise RuntimeError("crash")

        mw = SentinelMiddleware(boom)
        with pytest.raises(RuntimeError):
            mw(_FakeRequest())

        traces = sentinel.query(limit=10)
        crash_traces = [t for t in traces if "/decisions/crash" in t.agent]
        assert len(crash_traces) >= 1
        assert "error" in crash_traces[0].output

    def test_middleware_raises_improperly_configured(self, tmp_path: Path) -> None:
        import django
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured

        if not settings.configured:
            settings.configure(
                DEBUG=True,
                SECRET_KEY="test-key",
                ROOT_URLCONF="tests.test_integration_jupyter_fastapi_django",
                ALLOWED_HOSTS=["*"],
                MIDDLEWARE=[],
                DATABASES={},
                INSTALLED_APPS=[],
            )
            django.setup()

        # Clear the SENTINEL setting if present
        if hasattr(settings, "SENTINEL"):
            settings.SENTINEL = None
            delattr(settings, "SENTINEL")

        from sentinel.integrations.django import SentinelMiddleware

        class _FakeRequest:
            method = "GET"
            path = "/decisions/check"

        mw = SentinelMiddleware(lambda r: None)
        with pytest.raises(ImproperlyConfigured):
            mw(_FakeRequest())
