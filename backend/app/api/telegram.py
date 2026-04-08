"""
Endpoints Telegram : /telegram/link, /telegram/test, /telegram/settings
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
import hmac

from app.core.auth_firebase import get_current_uid
from app.schemas.telegram import (
    TelegramLink,
    TelegramSettingsRead,
    TelegramSettingsUpdate,
)
from app.services import firestore_service, telegram_service, audit_service

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/link")
async def link_telegram(
    payload: TelegramLink,
    uid: str = Depends(get_current_uid),
):
    """Lie un chat Telegram à l'utilisateur."""
    firestore_service.update_telegram_settings(
        uid,
        {
            "enabled": True,
            "chat_id": payload.chat_id,
            "username": payload.username,
            "notify_orders": True,
            "notify_errors": True,
            "notify_subscription": True,
        },
    )
    audit_service.log_telegram_linked(uid, payload.chat_id)
    return {"message": "Telegram linked successfully"}


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


@router.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    """Reçoit les updates Telegram via webhook."""
    from app.services.telegram_bot import WEBHOOK_SECRET, handle_webhook_update

    if not hmac.compare_digest(secret, WEBHOOK_SECRET):
        return {"ok": False}

    update = await request.json()
    await handle_webhook_update(update)
    return {"ok": True}
