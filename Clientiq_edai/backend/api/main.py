# FastAPI main app
"""
ClientIQ — FastAPI Application
Main entrypoint: registers all routers, CORS, middleware, and health endpoints.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import time

from backend.utils.config import settings
from backend.utils.logger import logger
from backend.api.routes_auth import router as auth_router
from backend.api.routes_query import router as query_router
from backend.api.routes_analytics import router as analytics_router
from backend.api.routes_clients import router as clients_router
from backend.api.routes_graph import router as graph_router
from backend.api.routes_admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    logger.info("╔══════════════════════════════════════╗")
    logger.info("║     ClientIQ API Starting...          ║")
    logger.info("╚══════════════════════════════════════╝")

    # Verify database connectivity
    from backend.database.connection import check_db_connection
    db_ok = await check_db_connection()
    if not db_ok:
        logger.warning("TiDB connection unavailable — running in degraded mode")

    # Verify hosted LLM
    from backend.services.mistral_client import MistralClient
    llm_ok = MistralClient().health_check()
    if not llm_ok:
        logger.warning("Mistral API not reachable or MISTRAL_API_KEY is missing - LLM features unavailable")

    logger.info("ClientIQ API ready | env={}", settings.app_env)
    yield
    logger.info("ClientIQ API shutting down")


# ─── App Instance ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="ClientIQ API",
    description="Enterprise Multi-Agent Hybrid RAG Intelligence Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def request_timing(request: Request, call_next):
    """Log request duration for performance monitoring."""
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    logger.debug("{} {} → {} ({:.1f}ms)", request.method, request.url.path, response.status_code, duration)
    response.headers["X-Process-Time"] = f"{duration:.1f}ms"
    return response


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth_router,      prefix="/api/auth",      tags=["Authentication"])
app.include_router(query_router,     prefix="/api/query",     tags=["AI Query"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(clients_router,   prefix="/api/clients",   tags=["CRM Clients"])
app.include_router(graph_router,     prefix="/api/graph",     tags=["Knowledge Graph"])
app.include_router(admin_router,     prefix="/api/admin",     tags=["Admin"])

# ─── Health & Root ────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    from backend.database.connection import check_db_connection
    from backend.services.mistral_client import MistralClient

    db_status = await check_db_connection()
    llm_status = MistralClient().health_check()

    return {
        "status": "healthy" if (db_status and llm_status) else "degraded",
        "database": "connected" if db_status else "unavailable",
        "llm": "connected" if llm_status else "unavailable",
        "version": "1.0.0",
        "app": settings.app_name,
        "env": settings.app_env,
    }


# ─── Static files (frontend) ─────────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: {} | path={}", exc, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url.path)},
    )
