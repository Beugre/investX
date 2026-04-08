"""
InvestX – Application FastAPI principale.
SaaS DCA Crypto Multi-utilisateur.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.logger import get_logger
from app.scheduler.runner import start_scheduler, stop_scheduler
from app.services.telegram_bot import start_bot as start_telegram_bot, stop_bot as stop_telegram_bot

# Import des routers
from app.api.health import router as health_router
from app.api.users import router as users_router
from app.api.dca import router as dca_router
from app.api.binance import router as binance_router
from app.api.revolutx import router as revolutx_router
from app.api.stripe import router as stripe_router
from app.api.telegram import router as telegram_router
from app.api.portfolio import router as portfolio_router
from app.api.auth import router as internal_router
from app.api.alerts import router as alerts_router
from app.api.admin import router as admin_router

logger = get_logger(__name__)


def _init_firebase() -> None:
    """Initialise le SDK Firebase Admin."""
    if not firebase_admin._apps:
        if settings.google_application_credentials:
            cred = credentials.Certificate(settings.google_application_credentials)
            firebase_admin.initialize_app(cred, {
                "projectId": settings.firebase_project_id,
            })
        else:
            # Utilise les credentials par défaut (Cloud Run, GCE, etc.)
            firebase_admin.initialize_app(options={
                "projectId": settings.firebase_project_id,
            })
        logger.info("Firebase Admin SDK initialized (project: %s)", settings.firebase_project_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    # Startup
    _init_firebase()
    start_scheduler()
    start_telegram_bot()
    logger.info("InvestX backend started (env: %s)", settings.app_env)
    yield
    # Shutdown
    await stop_telegram_bot()
    stop_scheduler()
    logger.info("InvestX backend stopped")


app = FastAPI(
    title="InvestX API",
    description="SaaS DCA Crypto Multi-utilisateur",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Rate Limiter ──
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://investxbot.com",
        "https://www.investxbot.com",
        "http://localhost:8501",
        "http://localhost:8601",
        "http://213.199.41.168:8601",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Enregistrement des routers ──
app.include_router(health_router)
app.include_router(users_router)
app.include_router(dca_router)
app.include_router(binance_router)
app.include_router(revolutx_router)
app.include_router(stripe_router)
app.include_router(telegram_router)
app.include_router(portfolio_router)
app.include_router(internal_router)
app.include_router(alerts_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"app": "InvestX", "version": "0.1.0", "status": "running"}
