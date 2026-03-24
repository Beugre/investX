"""
Service Binance – validation credentials, passage d'ordres, prix.
"""

from __future__ import annotations

from typing import Any

from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

from app.core.exceptions import BinanceError
from app.logger import get_logger

logger = get_logger(__name__)


def _get_client(api_key: str, api_secret: str) -> BinanceClient:
    return BinanceClient(api_key, api_secret)


def validate_credentials(api_key: str, api_secret: str) -> bool:
    """Teste si les credentials Binance sont valides."""
    try:
        client = _get_client(api_key, api_secret)
        client.get_account()
        return True
    except BinanceAPIException as e:
        logger.warning("Binance credentials validation failed: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error validating Binance credentials: %s", e)
        return False


def get_permissions(api_key: str, api_secret: str) -> dict[str, bool]:
    """Retourne les permissions de l'API key Binance."""
    try:
        client = _get_client(api_key, api_secret)
        info = client.get_account_api_permissions()
        logger.info("Binance API permissions response keys: %s", list(info.keys()))
        return {
            "can_trade": info.get("enableSpotAndMarginTrading", info.get("canTrade", False)),
            "can_withdraw": info.get("enableWithdrawals", info.get("canWithdraw", False)),
            "can_deposit": info.get("enableDeposit", info.get("canDeposit", False)),
        }
    except Exception as e:
        logger.error("Failed to get Binance permissions: %s", e)
        raise BinanceError(f"Failed to get permissions: {e}") from e


def check_no_withdraw_permission(api_key: str, api_secret: str) -> bool:
    """Vérifie que l'API key n'a PAS la permission de retrait.
    Retourne True si c'est safe (pas de retrait).
    """
    try:
        client = _get_client(api_key, api_secret)
        info = client.get_account_api_permissions()
        logger.info("Binance withdraw check – response: %s", {k: v for k, v in info.items() if 'withdraw' in k.lower() or 'Withdraw' in k})
        # Binance API uses 'enableWithdrawals' (not 'canWithdraw')
        can_withdraw = info.get("enableWithdrawals", info.get("canWithdraw", False))
        if can_withdraw:
            logger.warning("Binance API key has withdrawal permission – refusing")
            return False
        return True
    except Exception as e:
        logger.error("Could not check Binance withdrawal permission: %s", e)
        return False


def place_market_buy_order(
    api_key: str,
    api_secret: str,
    symbol: str,
    quote_amount: float,
) -> dict[str, Any]:
    """Passe un ordre market buy sur Binance.
    Utilise quoteOrderQty pour acheter avec un montant en quote currency (EUR).
    """
    try:
        client = _get_client(api_key, api_secret)
        order = client.order_market_buy(
            symbol=symbol,
            quoteOrderQty=quote_amount,
        )
        logger.info(
            "Market buy order placed: symbol=%s, quote=%s, orderId=%s",
            symbol,
            quote_amount,
            order.get("orderId"),
        )

        # Extraire les infos utiles
        fills = order.get("fills", [])
        total_qty = sum(float(f["qty"]) for f in fills)
        total_cost = sum(float(f["qty"]) * float(f["price"]) for f in fills)
        avg_price = total_cost / total_qty if total_qty > 0 else 0.0

        return {
            "symbol": symbol,
            "side": "BUY",
            "amount_eur": quote_amount,
            "quantity": total_qty,
            "price": avg_price,
            "status": order.get("status", "FILLED"),
            "exchange_order_id": str(order.get("orderId", "")),
        }
    except BinanceAPIException as e:
        logger.error("Binance order failed: %s", e)
        raise BinanceError(f"Order failed: {e.message}") from e
    except Exception as e:
        logger.error("Unexpected error placing Binance order: %s", e)
        raise BinanceError(f"Order failed: {e}") from e


def get_symbol_price(api_key: str, api_secret: str, symbol: str) -> float:
    """Retourne le prix actuel d'un symbole."""
    try:
        client = _get_client(api_key, api_secret)
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    except Exception as e:
        logger.error("Failed to get price for %s: %s", symbol, e)
        raise BinanceError(f"Failed to get price: {e}") from e


def get_asset_balances(
    api_key: str, api_secret: str, assets: list[str] | None = None
) -> dict[str, float]:
    """Retourne les balances des assets spécifiés."""
    try:
        client = _get_client(api_key, api_secret)
        account = client.get_account()
        balances = {}
        for b in account.get("balances", []):
            asset = b["asset"]
            if assets is None or asset in assets:
                free = float(b["free"])
                locked = float(b["locked"])
                total = free + locked
                if total > 0:
                    balances[asset] = total
        return balances
    except Exception as e:
        logger.error("Failed to get balances: %s", e)
        raise BinanceError(f"Failed to get balances: {e}") from e


# ══════════════════════════════════════════════════════
# Klines (bougies) pour RSI, MA200, rolling high
# ══════════════════════════════════════════════════════

def get_daily_klines(
    api_key: str,
    api_secret: str,
    symbol: str,
    limit: int = 250,
) -> list[list]:
    """Récupère les klines daily (1d) pour un symbole.
    Retourne les `limit` dernières bougies journalières.
    Format : [[open_time, open, high, low, close, volume, close_time, ...], ...]
    """
    try:
        client = _get_client(api_key, api_secret)
        klines = client.get_klines(
            symbol=symbol,
            interval=BinanceClient.KLINE_INTERVAL_1DAY,
            limit=limit,
        )
        logger.info("Fetched %d daily klines for %s", len(klines), symbol)
        return klines
    except BinanceAPIException as e:
        logger.error("Failed to get klines for %s: %s", symbol, e)
        raise BinanceError(f"Failed to get klines: {e.message}") from e
    except Exception as e:
        logger.error("Unexpected error getting klines for %s: %s", symbol, e)
        raise BinanceError(f"Failed to get klines: {e}") from e


def get_symbol_price_no_auth(symbol: str) -> float:
    """Récupère le prix actuel via l'API publique (pas besoin d'API key).
    Utile pour les vérifications rapides.
    """
    try:
        client = BinanceClient()
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    except Exception as e:
        logger.error("Failed to get public price for %s: %s", symbol, e)
        raise BinanceError(f"Failed to get price: {e}") from e


def get_daily_klines_public(symbol: str, limit: int = 250) -> list[list]:
    """Récupère les klines daily via l'API publique (pas besoin d'API key)."""
    try:
        client = BinanceClient()
        klines = client.get_klines(
            symbol=symbol,
            interval=BinanceClient.KLINE_INTERVAL_1DAY,
            limit=limit,
        )
        return klines
    except Exception as e:
        logger.error("Failed to get public klines for %s: %s", symbol, e)
        raise BinanceError(f"Failed to get klines: {e}") from e
