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
        parts = text.strip().split(maxsplit=1)
        link_code = parts[1].strip().upper() if len(parts) > 1 else ""

        if link_code:
            from app.services import audit_service, firestore_service

            uid = firestore_service.consume_telegram_link_request(
                link_code,
                chat_id=str(chat_id),
                username=username or None,
            )
            if uid:
                audit_service.log_telegram_linked(uid, str(chat_id))
                reply = (
                    f"✅ <b>Telegram lié avec succès</b>\n\n"
                    f"Bonjour {first_name}, ce chat recevra désormais vos notifications InvestX."
                )
                await _send_reply(chat_id, reply)
                logger.info("Linked Telegram chat %s to user %s", chat_id, uid)
                return

            reply = (
                "⚠️ <b>Code invalide ou expiré</b>\n\n"
                "Retournez dans InvestX pour générer un nouveau code de liaison."
            )
            await _send_reply(chat_id, reply)
            return

        reply = (
            f"👋 Bienvenue sur <b>InvestX</b>, {first_name} !\n\n"
            f"Pour lier Telegram en toute sécurité :\n"
            f"1. Ouvrez la page <b>Integrations → Telegram</b> dans InvestX\n"
            f"2. Générez votre code de liaison\n"
            f"3. Revenez ici via le lien automatique ou envoyez <code>/start CODE</code>\n\n"
            f"🆔 Votre Chat ID de support est <code>{chat_id}</code>."
        )
        await _send_reply(chat_id, reply)
        logger.info("Sent chat_id %s to user %s (@%s)", chat_id, first_name, username)

    elif text.strip().startswith("/help"):
        reply = (
            "ℹ️ <b>Commandes disponibles</b>\n\n"
            "/start CODE – Lier Telegram a votre compte InvestX\n"
            "/start – Afficher l'aide de liaison\n"
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


def get_webhook_secret() -> str:
    """Retourne le secret webhook configuré."""
    secret = settings.telegram_webhook_secret.strip()
    if not secret:
        raise RuntimeError("TELEGRAM_WEBHOOK_SECRET must be set when webhook mode is enabled")
    return secret


async def _setup_webhook() -> None:
    """Configure le webhook Telegram vers notre endpoint."""
    webhook_secret = get_webhook_secret()
    webhook_url = f"{settings.app_base_url.rstrip('/')}/api/telegram/webhook"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message"],
                    "secret_token": webhook_secret,
                },
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
