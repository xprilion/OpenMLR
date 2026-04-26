"""Tests for app entrypoint and main module."""

import pytest

from openmlr.app import app

pytestmark = pytest.mark.asyncio


class TestAppCreation:
    async def test_app_title(self):
        assert app.title == "OpenMLR"

    async def test_app_version(self):
        assert app.version == "0.3.0"

    async def test_app_routers_registered(self):
        route_paths = [r.path for r in app.routes]
        assert "/api/auth/register" in route_paths
        assert "/api/auth/login" in route_paths
        assert "/api/health" in route_paths
        assert "/api/message" in route_paths

    async def test_cors_middleware_configured(self):
        from fastapi.middleware.cors import CORSMiddleware
        middlewares = [m.cls for m in app.user_middleware]
        assert CORSMiddleware in middlewares

    async def test_global_exception_handler_configured(self):
        handlers = app.exception_handlers
        assert Exception in handlers


class TestMainModule:
    async def test_main_is_callable(self):
        from openmlr.main import main
        assert callable(main)

    async def test_main_contains_uvicorn_import(self):
        import inspect

        from openmlr.main import main
        source = inspect.getsource(main)
        assert "uvicorn" in source
