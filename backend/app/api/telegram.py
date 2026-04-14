"""
Endpoints Telegram : /telegram/link, /telegram/test, /telegram/settings
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
import hmac

from app.core.auth_firebase import get_current_uid
from app.core.exceptions import BadRequest
from app.schemas.telegram import (
    TelegramLinkRequestRead,
    TelegramSettingsRead,
    TelegramSettingsUpdate,
)
from app.services import firestore_service, telegram_service

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/link/request", response_model=TelegramLinkRequestRead)
async def create_telegram_link_request(uid: str = Depends(get_current_uid)):
    """Génère un code à envoyer au bot Telegram pour prouver la possession du chat."""
    link = firestore_service.create_telegram_link_request(uid)
    code = link["link_code"]
    return TelegramLinkRequestRead(
        link_code=code,
        expires_at=link["expires_at"],
        bot_url=f"https://t.me/InvestX_The_Bot?start={code}",
    )


@router.post("/link")
async def link_telegram_legacy(uid: str = Depends(get_current_uid)):
    """Ancien endpoint manuel désactivé pour éviter l'usurpation de chat_id."""
    raise BadRequest("Manual Telegram linking is disabled. Use /telegram/link/request.")


@router.post("/test")
async def test_telegram(uid: str = Depends(get_current_uid)):
    """Envoie un message de test Telegram."""
    settings = firestore_service.get_telegram_settings(uid)
    if not settings or not settings.get("chat_id"):
        return {"success": False, "message": "Telegram not linked"}

    success = await telegram_service.send_message(
        settings["chat_id"], "🔔 Test InvestX – Telegram fonctionne !"
    )
    return {"success": success}


@router.get("/settings", response_model=TelegramSettingsRead)
async def get_telegram_settings(uid: str = Depends(get_current_uid)):
    """Retourne les paramètres Telegram."""
    settings = firestore_service.get_telegram_settings(uid)
    if not settings:
        return TelegramSettingsRead()
    return TelegramSettingsRead(**settings)


@router.put("/settings", response_model=TelegramSettingsRead)
async def update_telegram_settings(
    payload: TelegramSettingsUpdate,
    uid: str = Depends(get_current_uid),
):
    """Met à jour les préférences de notification Telegram."""
    data = payload.model_dump()
    firestore_service.update_telegram_settings(uid, data)
    return TelegramSettingsRead(**{**data, **(firestore_service.get_telegram_settings(uid) or {})})


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """Reçoit les updates Telegram via webhook."""
    from app.services.telegram_bot import get_webhook_secret, handle_webhook_update

    webhook_secret = get_webhook_secret()
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        x_telegram_bot_api_secret_token, webhook_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")

    update = await request.json()
    await handle_webhook_update(update)
    return {"ok": True}
