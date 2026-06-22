"""
Job de monitoring – vérifie la santé du système et alerte l'admin via Telegram.
"""

from __future__ import annotations

import asyncio

import httpx

from app.config import settings
from app.services import telegram_service, firestore_service
from app.logger import get_logger

logger = get_logger(__name__)

# Chat ID admin pour les alertes système (à configurer)
ADMIN_CHAT_ID = "1181024836"

# URL interne du health check
HEALTH_URL = "http://127.0.0.1:8600/health"


def health_check_job() -> None:
    """Vérifie la santé du backend et alerte l'admin si dégradé."""
    # En dev local, le dashboard Streamlit (port 8600) n'est pas lancé — on skip
    if settings.app_env != "production":
        return
    try:
        response = httpx.get(HEALTH_URL, timeout=10)

        if response.status_code != 200:
            _alert_admin(f"⚠️ Health check HTTP {response.status_code}")
            return

        data = response.json()
        status = data.get("status", "unknown")

        if status != "ok":
            checks = data.get("checks", {})
            details = "\n".join(
                f"  • {k}: {v}" for k, v in checks.items() if v not in ("ok", "running")
            )
            _alert_admin(
                f"⚠️ <b>InvestX – Système dégradé</b>\n\n"
                f"Statut : {status}\n"
                f"Détails :\n{details}"
            )

    except Exception as e:
        _alert_admin(f"🔴 <b>InvestX – Health check échoué</b>\n\n{e}")


def _alert_admin(message: str) -> None:
    """Envoie une alerte Telegram à l'admin."""
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(telegram_service.send_message(ADMIN_CHAT_ID, message))
        loop.close()
        logger.warning("Admin alert sent: %s", message[:100])
    except Exception as e:
        logger.error("Failed to send admin alert: %s", e)
