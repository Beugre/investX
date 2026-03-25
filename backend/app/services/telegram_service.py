"""
Service Telegram – envoi de notifications via Bot API.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


async def send_message(chat_id: str, text: str) -> bool:
    """Envoie un message Telegram à un chat_id."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
            if response.status_code == 200:
                logger.info("Telegram message sent to %s", chat_id)
                return True
            else:
                logger.warning(
                    "Telegram API error %s: %s",
                    response.status_code,
                    response.text,
                )
                return False
    except Exception as e:
        logger.error("Failed to send Telegram message: %s", e)
        return False


async def send_order_notification(chat_id: str, order: dict) -> bool:
    """Envoie une notification d'achat DCA réussi."""
    symbol = order.get('symbol', '?')
    cs = "€" if symbol.endswith("-EUR") else "$"
    est_tag = "\n⚠️ <i>Données estimées (fills indisponibles)</i>" if order.get("estimated") else ""
    text = (
        "✅ <b>Achat DCA exécuté</b>\n\n"
        f"Paire : {symbol}\n"
        f"Montant : {order.get('amount_eur', 0):.2f} {cs}\n"
        f"Quantité : {order.get('quantity', 0):.8f}\n"
        f"Prix : {order.get('price', 0):,.2f} {cs}\n"
        f"Statut : {order.get('status', '?')}"
        f"{est_tag}"
    )
    return await send_message(chat_id, text)


async def send_error_notification(chat_id: str, error_message: str) -> bool:
    """Envoie une notification d'erreur."""
    text = f"❌ <b>Erreur DCA</b>\n\n{error_message}"
    return await send_message(chat_id, text)


async def send_subscription_notification(chat_id: str, status: str) -> bool:
    """Envoie une notification de changement d'abonnement."""
    emoji = "✅" if status == "active" else "⚠️"
    text = f"{emoji} <b>Abonnement</b>\n\nStatut : {status}"
    return await send_message(chat_id, text)
