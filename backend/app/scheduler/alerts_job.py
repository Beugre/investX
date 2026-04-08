"""
Job de vérification des alertes de prix.
"""

from __future__ import annotations

from app.logger import get_logger
from app.services import firestore_service, telegram_service
from app.services.binance_service import get_symbol_price_no_auth

logger = get_logger(__name__)


def check_price_alerts_job() -> None:
    """Vérifie toutes les alertes actives et notifie si déclenchées."""
    try:
        alerts = firestore_service.get_all_active_alerts()
        if not alerts:
            return

        # Regrouper les symboles pour limiter les appels API
        symbols = {a["symbol"] for a in alerts}
        prices: dict[str, float] = {}
        for sym in symbols:
            try:
                price = get_symbol_price_no_auth(sym)
                if price and price > 0:
                    prices[sym] = price
            except Exception as e:
                logger.warning("Cannot get price for %s: %s", sym, e)

        triggered = 0
        for alert in alerts:
            sym = alert["symbol"]
            if sym not in prices:
                continue
            current_price = prices[sym]
            target = alert["target_price"]
            direction = alert["direction"]

            should_trigger = (
                (direction == "above" and current_price >= target)
                or (direction == "below" and current_price <= target)
            )
            if should_trigger:
                uid = alert["uid"]
                alert_id = alert["id"]
                firestore_service.mark_alert_triggered(uid, alert_id)
                triggered += 1

                # Notification Telegram
                arrow = "📈" if direction == "above" else "📉"
                msg = (
                    f"{arrow} *Alerte de prix déclenchée*\n\n"
                    f"Paire : `{sym}`\n"
                    f"Prix actuel : `{current_price:,.2f}`\n"
                    f"Cible : `{target:,.2f}` ({direction})"
                )
                try:
                    tg = firestore_service.get_telegram_settings(uid)
                    if tg and tg.get("chat_id") and tg.get("notify_on_execution", True):
                        import asyncio
                        asyncio.run(telegram_service.send_message(tg["chat_id"], msg))
                except Exception as e:
                    logger.warning("Alert notification failed for %s: %s", uid, e)

        if triggered:
            logger.info("Price alerts: %d triggered", triggered)
    except Exception as e:
        logger.error("Price alerts job failed: %s", e)
