"""
Service Portfolio – calcul snapshots et métriques.
"""

from __future__ import annotations

from app.services import firestore_service, binance_service, revolutx_service, secret_manager_service
from app.logger import get_logger

logger = get_logger(__name__)


def _order_sort_key(order: dict) -> tuple:
    return (
        order.get("executed_at") or order.get("created_at") or "",
        order.get("order_id") or "",
    )


def _normalize_order(order: dict) -> dict[str, float | str]:
    """Normalise les ordres historiques pour un calcul de position cohérent."""
    side = str(order.get("side", "BUY")).upper()
    symbol = str(order.get("symbol", ""))
    qty = float(order.get("quantity", 0) or 0)
    amount = float(order.get("amount_eur", 0) or 0)
    commission = float(order.get("commission", 0) or 0)
    commission_asset = str(order.get("commission_asset", "") or "")

    if side == "BUY" and "commission" not in order:
        estimated_fee = qty * 0.001
        qty = max(0.0, qty - estimated_fee)
        amount = qty * float(order.get("price", 0) or 0)
        commission = estimated_fee
        if not commission_asset:
            commission_asset = (
                symbol.replace("USDC", "").replace("USDT", "").replace("EUR", "").replace("-", "")
            )

    return {
        "side": side,
        "quantity": qty,
        "amount_eur": amount,
        "commission": commission,
        "commission_asset": commission_asset,
    }


def compute_snapshot(uid: str, symbol: str) -> dict:
    """Calcule le snapshot portfolio actuel pour un symbole."""
    orders = firestore_service.list_orders(uid, limit=1000, symbol=symbol)
    filled_orders = [
        o for o in orders if str(o.get("status", "")).upper() in {"FILLED", "DONE", "COMPLETED"}
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

    total_qty = 0.0
    total_cost_basis = 0.0
    total_commission = 0.0
    commission_asset = ""

    for order in sorted(filled_orders, key=_order_sort_key):
        normalized = _normalize_order(order)
        side = str(normalized["side"])
        qty = float(normalized["quantity"])
        amount = float(normalized["amount_eur"])
        total_commission += float(normalized["commission"])
        if not commission_asset and normalized["commission_asset"]:
            commission_asset = str(normalized["commission_asset"])

        if side == "BUY":
            total_qty += qty
            total_cost_basis += amount
            continue

        if side == "SELL" and total_qty > 0:
            sell_qty = min(qty, total_qty)
            avg_cost_before_sell = total_cost_basis / total_qty if total_qty > 0 else 0.0
            total_qty -= sell_qty
            total_cost_basis = max(0.0, total_cost_basis - (avg_cost_before_sell * sell_qty))

    avg_price = total_cost_basis / total_qty if total_qty > 0 else 0.0

    # Récupérer le prix actuel via l'exchange approprié au symbole
    # Les symboles Revolut X utilisent le format "BTC-EUR", Binance "BTCUSDC"
    market_price = 0.0
    try:
        is_revx_symbol = "-" in symbol  # SOL-EUR, BTC-EUR, etc.
        if is_revx_symbol:
            creds = secret_manager_service.get_revolutx_secret(uid)
            market_price = revolutx_service.get_symbol_price(
                creds["api_key"], creds["private_key_pem"], symbol
            )
        else:
            creds = secret_manager_service.get_binance_secret(uid)
            market_price = binance_service.get_symbol_price(
                creds["api_key"], creds["api_secret"], symbol
            )
    except Exception as e:
        logger.warning("Could not fetch market price for %s/%s: %s", uid, symbol, e)

    if market_price <= 0 and total_qty > 0:
        # Ne pas enregistrer un snapshot avec un prix = 0 (trompeur)
        last = firestore_service.get_latest_snapshot(uid, symbol)
        if last and last.get("market_price", 0) > 0:
            market_price = last["market_price"]
            logger.info("Using last known price for %s/%s: %.2f", uid, symbol, market_price)

    market_value = total_qty * market_price
    pnl_value = market_value - total_cost_basis
    pnl_percent = (pnl_value / total_cost_basis * 100) if total_cost_basis > 0 else 0.0

    return {
        "symbol": symbol,
        "quantity_total": total_qty,
        "invested_total_eur": total_cost_basis,
        "avg_buy_price": avg_price,
        "market_price": market_price,
        "market_value_eur": market_value,
        "pnl_value_eur": pnl_value,
        "pnl_percent": round(pnl_percent, 2),
        "total_commission": total_commission,
        "commission_asset": commission_asset,
    }


def refresh_snapshot(uid: str, symbol: str) -> str:
    """Recalcule et sauvegarde le snapshot portfolio."""
    snapshot_data = compute_snapshot(uid, symbol)
    snapshot_id = firestore_service.save_snapshot(uid, snapshot_data)
    logger.info("Snapshot refreshed for user %s / %s", uid, symbol)
    return snapshot_id
