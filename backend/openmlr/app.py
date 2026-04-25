"""FastAPI application — OpenMLR backend entry point."""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .config import load_config
from .services.event_bus import EventBus
from .services.session_manager import SessionManager
from .db.engine import engine
from .db.models import Base

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables & shared state.  Shutdown: teardown sessions."""
    import logging
    logger = logging.getLogger("openmlr.app")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    config = load_config()
    event_bus = EventBus()
    session_manager = SessionManager(event_bus=event_bus, default_config=config)

    app.state.config = config
    app.state.event_bus = event_bus
    app.state.session_manager = session_manager
    
    # Start Redis event bridge for cross-worker communication (background jobs)
    await event_bus.start_redis_bridge()
    logger.info("Redis event bridge started")

    yield
    
    # Cleanup
    await event_bus.stop_redis_bridge()
    for conv_id in list(session_manager.sessions.keys()):
        await session_manager.remove_session(conv_id)
    await engine.dispose()


app = FastAPI(
    title="OpenMLR",
    description="ML research intern — reads papers, trains models, writes papers",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS configuration - restrict in production
_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
_cors_origins = [origin.strip() for origin in _cors_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── API routers ──────────────────────────────────────────
from .auth.router import router as auth_router
from .routes.agent import router as agent_router
from .routes.settings import router as settings_router
from .routes.health import router as health_router

app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(settings_router)
app.include_router(health_router)


# ── Global error handler ────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logger = logging.getLogger(__name__)
    logger.exception(f"Unhandled exception: {exc}")
    # Don't leak internal details to client
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# ── Static frontend serving ─────────────────────────────
# Mount only if a production build exists; otherwise Vite dev server handles it.
if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").exists():
    # Serve hashed asset bundles
    if (FRONTEND_DIST / "assets").is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(FRONTEND_DIST / "assets")),
            name="assets",
        )

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """SPA fallback — serve index.html for all non-API routes."""
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"error": "Not found"})

        file_path = FRONTEND_DIST / full_path
        if file_path.is_file() and file_path.suffix:
            return FileResponse(str(file_path))

        return FileResponse(str(FRONTEND_DIST / "index.html"))
