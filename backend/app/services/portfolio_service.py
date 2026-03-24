"""
Service Portfolio – calcul snapshots et métriques.
"""

from __future__ import annotations

from app.services import firestore_service, binance_service, secret_manager_service
from app.logger import get_logger

logger = get_logger(__name__)


def compute_avg_buy_price(orders: list[dict]) -> float:
    """Calcule le prix moyen d'achat pondéré à partir de la liste d'ordres."""
    total_qty = 0.0
    total_cost = 0.0
    for o in orders:
        if o.get("status") == "FILLED" and o.get("side") == "BUY":
            qty = float(o.get("quantity", 0))
            price = float(o.get("price", 0))
            total_qty += qty
            total_cost += qty * price
    return total_cost / total_qty if total_qty > 0 else 0.0


def compute_snapshot(uid: str, symbol: str) -> dict:
    """Calcule le snapshot portfolio actuel pour un symbole."""
    orders = firestore_service.list_orders(uid, limit=1000, symbol=symbol)
    filled_orders = [
        o for o in orders if o.get("status") == "FILLED" and o.get("side") == "BUY"
    ]

    if not filled_orders:
        return {
            "symbol": symbol,
            "quantity_total": 0.0,
            "invested_total_eur": 0.0,
            "avg_buy_price": 0.0,
            "market_price": 0.0,
            "market_value_eur": 0.0,
            "pnl_value_eur": 0.0,
            "pnl_percent": 0.0,
        }

    total_qty = sum(float(o.get("quantity", 0)) for o in filled_orders)
    total_invested = sum(float(o.get("amount_eur", 0)) for o in filled_orders)
    avg_price = compute_avg_buy_price(filled_orders)

    # Récupérer le prix actuel via Binance
    market_price = 0.0
    try:
        creds = secret_manager_service.get_binance_secret(uid)
        market_price = binance_service.get_symbol_price(
            creds["api_key"], creds["api_secret"], symbol
        )
    except Exception as e:
        logger.warning("Could not fetch market price for %s/%s: %s", uid, symbol, e)

    market_value = total_qty * market_price
    pnl_value = market_value - total_invested
    pnl_percent = (pnl_value / total_invested * 100) if total_invested > 0 else 0.0

    return {
        "symbol": symbol,
        "quantity_total": total_qty,
        "invested_total_eur": total_invested,
        "avg_buy_price": avg_price,
        "market_price": market_price,
        "market_value_eur": market_value,
        "pnl_value_eur": pnl_value,
        "pnl_percent": round(pnl_percent, 2),
    }


def refresh_snapshot(uid: str, symbol: str) -> str:
    """Recalcule et sauvegarde le snapshot portfolio."""
    snapshot_data = compute_snapshot(uid, symbol)
    snapshot_id = firestore_service.save_snapshot(uid, snapshot_data)
    logger.info("Snapshot refreshed for user %s / %s", uid, symbol)
    return snapshot_id
