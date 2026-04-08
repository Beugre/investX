"""
Job de vérification take-profit : vend automatiquement quand le prix cible est atteint.
"""

from __future__ import annotations

from app.logger import get_logger
from app.services import firestore_service, telegram_service
from app.services.binance_service import get_ticker_price

logger = get_logger(__name__)


def check_take_profit_job() -> None:
    """Vérifie les configs take-profit et exécute les ventes si les cibles sont atteintes."""
    try:
        configs = firestore_service.get_all_take_profit_configs()
        if not configs:
            return

        for tp_config in configs:
            uid = tp_config["uid"]
            rules = tp_config.get("rules", [])
            for rule in rules:
                symbol = rule.get("symbol", "")
                target_price = rule.get("target_price", 0)
                sell_pct = rule.get("sell_pct", 50)

                if not symbol or target_price <= 0:
                    continue

                try:
                    current_price = get_ticker_price(symbol)
                    if not current_price or current_price < target_price:
                        continue

                    # Prix atteint ! Exécuter la vente
                    _execute_take_profit(uid, symbol, sell_pct, current_price, target_price)
                except Exception as e:
                    logger.warning(
                        "Take-profit check failed for %s/%s: %s", uid, symbol, e
                    )
    except Exception as e:
        logger.error("Take-profit job failed: %s", e)


def _execute_take_profit(
    uid: str, symbol: str, sell_pct: float,
    current_price: float, target_price: float,
) -> None:
    """Exécute un ordre de vente take-profit."""
    from app.services.dca_service import _get_exchange_client, _get_user_exchange

    exchange = _get_user_exchange(uid)
    if not exchange:
        logger.warning("Take-profit: no exchange for %s", uid)
        return

    # Calculer la quantité à vendre
    snapshot = firestore_service.get_latest_snapshot(uid, symbol)
    if not snapshot:
        logger.warning("Take-profit: no snapshot for %s/%s", uid, symbol)
        return

    total_qty = snapshot.get("total_quantity", 0)
    if total_qty <= 0:
        return

    sell_qty = total_qty * (sell_pct / 100)
    if sell_qty <= 0:
        return

    try:
        client = _get_exchange_client(uid, exchange)
        if not client:
            return

        # Placer l'ordre de vente market
        order = client.create_market_sell_order(symbol, sell_qty)
        logger.info(
            "Take-profit SELL executed: %s %s %.8f @ %.2f (target: %.2f)",
            uid, symbol, sell_qty, current_price, target_price,
        )

        # Sauvegarder l'ordre
        order_data = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": sell_qty,
            "price": current_price,
            "amount_eur": sell_qty * current_price,
            "order_type": "take_profit",
            "exchange": exchange,
        }
        firestore_service.save_order(uid, order_data)

        # Désactiver la règle pour éviter les ventes multiples
        _disable_triggered_rule(uid, symbol, target_price)

        # Notification Telegram
        msg = (
            f"💰 *Take-Profit exécuté*\n\n"
            f"Paire : `{symbol}`\n"
            f"Prix cible : `{target_price:,.2f}`\n"
            f"Prix d'exécution : `{current_price:,.2f}`\n"
            f"Quantité vendue : `{sell_qty:.8f}` ({sell_pct:.0f}%)\n"
            f"Valeur : `{sell_qty * current_price:,.2f}`"
        )
        try:
            tg = firestore_service.get_telegram_settings(uid)
            if tg and tg.get("chat_id"):
                import asyncio
                asyncio.run(telegram_service.send_message(tg["chat_id"], msg))
        except Exception:
            pass

    except Exception as e:
        logger.error("Take-profit SELL failed for %s/%s: %s", uid, symbol, e)


def _disable_triggered_rule(uid: str, symbol: str, target_price: float) -> None:
    """Désactive une règle take-profit après exécution."""
    tp = firestore_service.get_take_profit_config(uid)
    if not tp:
        return
    rules = tp.get("rules", [])
    updated_rules = [
        r for r in rules
        if not (r.get("symbol") == symbol and r.get("target_price") == target_price)
    ]
    firestore_service.update_take_profit_config(uid, {"rules": updated_rules})
