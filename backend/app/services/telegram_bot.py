"""
Telegram Bot Polling – répond à /start avec le chat_id de l'utilisateur.
Tourne en arrière-plan dans un thread séparé.
"""

from __future__ import annotations

import asyncio
import threading

import httpx

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

_polling_task: asyncio.Task | None = None
_should_stop = threading.Event()


async def _handle_message(message: dict) -> None:
    """Traite un message entrant du bot."""
    chat = message.get("chat", {})
    text = message.get("text", "")
    chat_id = chat.get("id")
    first_name = chat.get("first_name", "")
    username = chat.get("username", "")

    if not chat_id:
        return

    if text.strip().startswith("/start"):
        reply = (
            f"👋 Bienvenue sur <b>InvestX</b>, {first_name} !\n\n"
            f"Votre <b>Chat ID</b> est :\n\n"
            f"<code>{chat_id}</code>\n\n"
            f"📋 Copiez ce numéro et collez-le dans la page "
            f"<b>Intégrations → Telegram</b> de votre dashboard InvestX.\n\n"
            f"Une fois lié, vous recevrez ici vos notifications d'achats DCA, "
            f"d'erreurs et de changements d'abonnement."
        )
        await _send_reply(chat_id, reply)
        logger.info("Sent chat_id %s to user %s (@%s)", chat_id, first_name, username)

    elif text.strip().startswith("/help"):
        reply = (
            "ℹ️ <b>Commandes disponibles</b>\n\n"
            "/start – Obtenir votre Chat ID\n"
            "/help – Afficher cette aide\n"
            "/id – Ré-afficher votre Chat ID"
        )
        await _send_reply(chat_id, reply)

    elif text.strip().startswith("/id"):
        reply = f"🆔 Votre Chat ID : <code>{chat_id}</code>"
        await _send_reply(chat_id, reply)


async def _send_reply(chat_id: int, text: str) -> None:
    """Envoie une réponse Telegram."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
    except Exception as e:
        logger.error("Failed to send Telegram reply: %s", e)


async def _poll_updates() -> None:
    """Long-polling des updates Telegram."""
    offset = 0
    logger.info("Telegram bot polling started")

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        while not _should_stop.is_set():
            try:
                response = await client.get(
                    f"{TELEGRAM_API}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                )
                if response.status_code != 200:
                    logger.warning("Telegram getUpdates error: %s", response.status_code)
                    await asyncio.sleep(5)
                    continue

                data = response.json()
                results = data.get("result", [])

                for update in results:
                    offset = update["update_id"] + 1
                    message = update.get("message")
                    if message:
                        await _handle_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Telegram polling error: %s", e)
                await asyncio.sleep(5)

    logger.info("Telegram bot polling stopped")


async def _delete_webhook() -> None:
    """Supprime tout webhook existant pour éviter le conflit 409 avec getUpdates."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{TELEGRAM_API}/deleteWebhook")
            if resp.status_code == 200:
                logger.info("Telegram webhook deleted (switch to polling)")
            else:
                logger.warning("deleteWebhook returned %s", resp.status_code)
    except Exception as e:
        logger.warning("Failed to delete webhook: %s", e)


def start_bot() -> None:
    """Démarre le bot Telegram en mode polling ou webhook."""
    if settings.telegram_webhook_mode:
        logger.info("Telegram bot in WEBHOOK mode – polling disabled")
        loop = asyncio.get_event_loop()
        loop.create_task(_setup_webhook())
        return

    global _polling_task
    _should_stop.clear()

    loop = asyncio.get_event_loop()
    # Supprimer le webhook avant de commencer le polling
    loop.create_task(_delete_webhook())
    _polling_task = loop.create_task(_poll_updates())
    logger.info("Telegram bot polling task created")


async def stop_bot() -> None:
    """Arrête le polling Telegram."""
    global _polling_task
    _should_stop.set()
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
        _polling_task = None
    logger.info("Telegram bot stopped")


# ── Mode Webhook ──

import os

WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "investx-tg-webhook-default-secret")


async def _setup_webhook() -> None:
    """Configure le webhook Telegram vers notre endpoint."""
    webhook_url = f"{settings.app_base_url}/telegram/webhook/{WEBHOOK_SECRET}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/setWebhook",
                json={"url": webhook_url, "allowed_updates": ["message"]},
            )
            if resp.status_code == 200:
                logger.info("Telegram webhook set to %s", webhook_url)
            else:
                logger.error("setWebhook failed: %s", resp.text)
    except Exception as e:
        logger.error("Failed to set webhook: %s", e)


async def handle_webhook_update(update: dict) -> None:
    """Traite un update reçu via webhook."""
    message = update.get("message")
    if message:
        await _handle_message(message)
