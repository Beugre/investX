"""
Service Revolut X – validation credentials, passage d'ordres, prix, klines.
Utilise l'API REST Revolut X (https://revx.revolut.com/api/1.0/).
Auth : Ed25519 signature (X-Revx-API-Key + X-Revx-Timestamp + X-Revx-Signature).
"""

from __future__ import annotations

import base64
import json
import time
import uuid
from typing import Any

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.exceptions import ExchangeError
from app.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://revx.revolut.com/api/1.0"


# ══════════════════════════════════════════════════════
# Auth helpers
# ══════════════════════════════════════════════════════

def _load_private_key(pem_str: str) -> Ed25519PrivateKey:
    """Charge une clé privée Ed25519 depuis un PEM (string)."""
    pem_bytes = pem_str.encode("utf-8")
    key = serialization.load_pem_private_key(pem_bytes, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ExchangeError("La clé privée n'est pas Ed25519")
    return key


def _sign_request(
    private_key: Ed25519PrivateKey,
    method: str,
    path: str,
    timestamp_ms: str,
    query: str = "",
    body: str = "",
) -> str:
    """Signe la requête selon le protocole Revolut X.
    Message = timestamp + METHOD + path + query + body (concaténés sans séparateur).
    """
    message = f"{timestamp_ms}{method.upper()}{path}{query}{body}"
    signature = private_key.sign(message.encode("utf-8"))
    return base64.b64encode(signature).decode("utf-8")


def _headers(
    api_key: str,
    private_key: Ed25519PrivateKey,
    method: str,
    path: str,
    query: str = "",
    body: str = "",
) -> dict[str, str]:
    """Construit les headers d'authentification Revolut X."""
    ts = str(int(time.time() * 1000))
    sig = _sign_request(private_key, method, path, ts, query, body)
    return {
        "X-Revx-API-Key": api_key,
        "X-Revx-Timestamp": ts,
        "X-Revx-Signature": sig,
        "Content-Type": "application/json",
    }


def _request(
    api_key: str,
    private_key_pem: str,
    method: str,
    endpoint: str,
    params: dict | None = None,
    json_body: dict | None = None,
    timeout: float = 15.0,
) -> Any:
    """Effectue une requête authentifiée vers l'API Revolut X."""
    pk = _load_private_key(private_key_pem)
    path = f"/api/1.0{endpoint}"
    query = "&".join(f"{k}={v}" for k, v in (params or {}).items())
    body_str = json.dumps(json_body, separators=(",", ":")) if json_body else ""

    hdrs = _headers(api_key, pk, method, path, query, body_str)
    url = f"{BASE_URL}{endpoint}"
    if query:
        url = f"{url}?{query}"

    try:
        with httpx.Client(timeout=timeout) as client:
            if method.upper() == "GET":
                resp = client.get(url, headers=hdrs)
            elif method.upper() == "POST":
                resp = client.post(url, headers=hdrs, content=body_str)
            elif method.upper() == "DELETE":
                resp = client.delete(url, headers=hdrs)
            else:
                raise ExchangeError(f"Unsupported HTTP method: {method}")

        if resp.status_code == 401:
            raise ExchangeError("Revolut X : credentials invalides (401 Unauthorized)")
        if resp.status_code == 403:
            raise ExchangeError("Revolut X : accès refusé (403 Forbidden)")
        if resp.status_code == 429:
            raise ExchangeError("Revolut X : trop de requêtes (rate limit)")
        if resp.status_code >= 400:
            detail = resp.text[:300] if resp.text else str(resp.status_code)
            # Enrichir le message pour les erreurs de balance
            detail_upper = detail.upper()
            if "INSUFFICIENT" in detail_upper or "BALANCE" in detail_upper or "FUNDS" in detail_upper or "NOT_ENOUGH" in detail_upper:
                raise ExchangeError(f"Revolut X : solde insuffisant – {detail}")
            raise ExchangeError(f"Revolut X API error {resp.status_code}: {detail}")

        if resp.status_code == 204:
            return {}
        return resp.json()
    except ExchangeError:
        raise
    except Exception as e:
        logger.error("Revolut X request failed: %s %s – %s", method, endpoint, e)
        raise ExchangeError(f"Revolut X request failed: {e}") from e


# ══════════════════════════════════════════════════════
# Fonctions publiques (même interface que binance_service)
# ══════════════════════════════════════════════════════

def validate_credentials(api_key: str, private_key_pem: str) -> bool:
    """Teste si les credentials Revolut X sont valides."""
    try:
        _request(api_key, private_key_pem, "GET", "/balances")
        return True
    except ExchangeError as e:
        logger.warning("Revolut X credentials validation failed: %s", e.message)
        return False
    except Exception as e:
        logger.error("Unexpected error validating Revolut X credentials: %s", e)
        return False


def place_market_buy_order(
    api_key: str,
    private_key_pem: str,
    symbol: str,
    quote_amount: float,
) -> dict[str, Any]:
    """Passe un ordre market buy sur Revolut X.
    Utilise quote_size pour acheter avec un montant en quote currency (EUR).
    Symbol format: "BTC-EUR", "ETH-EUR", etc.
    """
    client_order_id = str(uuid.uuid4())
    body = {
        "client_order_id": client_order_id,
        "symbol": symbol,
        "side": "BUY",
        "order_configuration": {
            "market": {
                "quote_size": str(round(quote_amount, 2)),
            }
        },
    }

    try:
        result = _request(api_key, private_key_pem, "POST", "/orders", json_body=body)
        data = result.get("data", result)

        venue_order_id = data.get("venue_order_id", client_order_id)
        state = data.get("state", "PENDING").upper()
        failure_reason = data.get("failure_reason", "") or data.get("reject_reason", "") or ""

        # Vérifier si l'ordre a été rejeté/annulé par l'exchange
        _FAILED_STATES = {"CANCELLED", "CANCELED", "REJECTED", "EXPIRED", "FAILED"}
        if state in _FAILED_STATES:
            detail = failure_reason or state
            logger.warning(
                "Revolut X order %s returned state=%s reason=%s",
                venue_order_id, state, failure_reason,
            )
            # Détecter spécifiquement le solde insuffisant
            reason_upper = detail.upper()
            if any(kw in reason_upper for kw in ("INSUFFICIENT", "BALANCE", "FUNDS", "NOT_ENOUGH")):
                raise ExchangeError(
                    f"Revolut X : solde insuffisant – {detail}"
                )
            raise ExchangeError(
                f"Revolut X : ordre {state.lower()} – {detail}"
            )

        # Récupérer les fills pour le prix moyen et la quantité
        fills_data = _get_order_fills(api_key, private_key_pem, venue_order_id)

        total_qty = 0.0
        total_cost = 0.0
        total_commission = 0.0
        commission_asset = ""

        for fill in fills_data:
            qty = float(fill.get("base_size", 0))
            price = float(fill.get("price", 0))
            fee = float(fill.get("fee", 0))
            total_qty += qty
            total_cost += qty * price
            total_commission += fee
            if not commission_asset:
                commission_asset = fill.get("fee_currency", "")

        avg_price = total_cost / total_qty if total_qty > 0 else 0.0
        actual_spent = total_cost if total_cost > 0 else quote_amount

        # Base asset extrait du symbol (BTC-EUR → BTC)
        base_asset = symbol.split("-")[0] if "-" in symbol else symbol

        # Quantité nette
        if commission_asset == base_asset:
            net_qty = total_qty - total_commission
        else:
            net_qty = total_qty

        # Sécurité finale : si aucun fill n'a été trouvé, l'ordre n'a pas vraiment été exécuté
        if total_qty == 0:
            logger.warning(
                "Revolut X order %s state=%s but 0 fills – treating as failed",
                venue_order_id, state,
            )
            raise ExchangeError(
                f"Revolut X : ordre non exécuté (état: {state.lower()}, aucun fill reçu). "
                f"Vérifiez votre solde Cryptos · EUR."
            )

        logger.info(
            "Revolut X market buy: symbol=%s, quote=%.2f, qty=%.8f, avg_price=%.2f",
            symbol, quote_amount, net_qty, avg_price,
        )

        return {
            "symbol": symbol,
            "side": "BUY",
            "amount_eur": actual_spent,
            "quantity": net_qty,
            "quantity_gross": total_qty,
            "commission": total_commission,
            "commission_asset": commission_asset,
            "price": avg_price,
            "status": state,
            "exchange_order_id": venue_order_id,
        }
    except ExchangeError:
        raise
    except Exception as e:
        logger.error("Revolut X order failed: %s", e)
        raise ExchangeError(f"Order failed: {e}") from e


def _get_order_fills(
    api_key: str, private_key_pem: str, venue_order_id: str
) -> list[dict]:
    """Récupère les fills d'un ordre. Retry jusqu'à 3 fois car le fill peut prendre un instant."""
    import time as _time
    for attempt in range(3):
        try:
            result = _request(
                api_key, private_key_pem, "GET",
                f"/orders/fills/{venue_order_id}",
            )
            fills = result.get("data", [])
            if fills:
                return fills
            _time.sleep(0.5)  # Attendre un peu pour le fill
        except ExchangeError:
            if attempt == 2:
                raise
            _time.sleep(0.5)
    return []


def get_symbol_price(api_key: str, private_key_pem: str, symbol: str) -> float:
    """Retourne le prix actuel d'un symbole via l'order-book public."""
    try:
        return get_symbol_price_no_auth(symbol)
    except Exception:
        # Fallback sur l'endpoint authentifié tickers (si implémenté)
        try:
            result = _request(api_key, private_key_pem, "GET", "/tickers")
            ticker = result.get("data", {}).get(symbol, {})
            return float(ticker.get("last_price", 0))
        except Exception as e:
            logger.error("Failed to get price for %s: %s", symbol, e)
            raise ExchangeError(f"Failed to get price: {e}") from e


def get_asset_balances(
    api_key: str, private_key_pem: str, assets: list[str] | None = None
) -> dict[str, float]:
    """Retourne les balances des assets."""
    try:
        result = _request(api_key, private_key_pem, "GET", "/balances")
        balances = {}
        for item in result.get("data", []):
            asset = item.get("currency", "")
            available = float(item.get("available", 0))
            if (assets is None or asset in assets) and available > 0:
                balances[asset] = available
        return balances
    except Exception as e:
        logger.error("Failed to get Revolut X balances: %s", e)
        raise ExchangeError(f"Failed to get balances: {e}") from e


# ══════════════════════════════════════════════════════
# Endpoints publics (pas d'auth nécessaire)
# ══════════════════════════════════════════════════════

def get_symbol_price_no_auth(symbol: str) -> float:
    """Récupère le prix via l'order-book public."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{BASE_URL}/public/order-book/{symbol}")
            resp.raise_for_status()
            data = resp.json()

        # Calculer le mid-price depuis les asks et bids
        asks = data.get("data", {}).get("asks", [])
        bids = data.get("data", {}).get("bids", [])

        if asks and bids:
            best_ask = float(asks[0][0]) if isinstance(asks[0], list) else float(asks[0].get("price", 0))
            best_bid = float(bids[0][0]) if isinstance(bids[0], list) else float(bids[0].get("price", 0))
            return (best_ask + best_bid) / 2
        elif asks:
            return float(asks[0][0]) if isinstance(asks[0], list) else float(asks[0].get("price", 0))

        raise ExchangeError(f"No price data for {symbol}")
    except ExchangeError:
        raise
    except Exception as e:
        logger.error("Failed to get public price for %s: %s", symbol, e)
        raise ExchangeError(f"Failed to get price: {e}") from e


def get_daily_klines_public(symbol: str, limit: int = 250) -> list[list]:
    """Récupère les candles daily via l'API publique Revolut X.
    interval=1440 (minutes) = 1 jour.
    Retourne au format compatible Binance : [[open_time, open, high, low, close, volume, ...], ...]
    """
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{BASE_URL}/public/order-book/{symbol}",
            )
            # L'order-book public ne fournit pas de candles.
            # On utilise les candles via un endpoint dédié si disponible,
            # sinon fallback sur Binance pour les klines (données publiques).
            pass

        # Revolut X candles endpoint nécessite auth.
        # Pour le RSI/MA200, on utilise les klines Binance publiques (même données de marché).
        # Le prix BTC est le même sur tous les exchanges.
        from app.services import binance_service
        binance_symbol = _revx_to_binance_symbol(symbol)
        return binance_service.get_daily_klines_public(binance_symbol, limit)
    except Exception as e:
        logger.error("Failed to get daily klines for %s: %s", symbol, e)
        raise ExchangeError(f"Failed to get klines: {e}") from e


def _revx_to_binance_symbol(revx_symbol: str) -> str:
    """Convertit un symbole Revolut X en symbole Binance pour les klines publiques.
    BTC-EUR → BTCUSDC (on utilise USDC pour les klines, le prix est quasi identique)
    """
    base = revx_symbol.split("-")[0] if "-" in revx_symbol else revx_symbol[:3]
    return f"{base}USDC"
