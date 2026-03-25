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
    """Passe un ordre buy sur Revolut X.

    Stratégie maker-first (0 % frais) :
    1. Récupérer le best bid de l'order-book
    2. Placer un limit buy au best bid (maker)
    3. Poller 60 s – si FILLED → terminé (0 % frais)
    4. Sinon annuler et réessayer (3 tentatives max)
    5. Après 3 échecs maker → fallback taker (market, 0.09 %)

    Symbol format: "BTC-EUR", "ETH-EUR", etc.
    """
    import time as _time

    MAKER_RETRIES = 3
    MAKER_WAIT_SECONDS = 60
    MAKER_POLL_INTERVAL = 5  # poll toutes les 5s
    _FAILED_STATES = {"CANCELLED", "CANCELED", "REJECTED", "EXPIRED", "FAILED"}
    _SUCCESS_STATES = {"FILLED", "DONE", "COMPLETED"}

    # ── Tentatives Maker (limit au best bid) ──────────
    for maker_attempt in range(1, MAKER_RETRIES + 1):
        try:
            # Récupérer le best bid pour placer l'ordre maker
            best_bid = _get_best_bid(symbol)
            if best_bid <= 0:
                logger.warning("Maker attempt %d: no best bid for %s, skipping", maker_attempt, symbol)
                break  # aller directement au taker

            # Calculer la quantité à acheter au prix bid
            base_qty = quote_amount / best_bid

            client_order_id = str(uuid.uuid4())
            body = {
                "client_order_id": client_order_id,
                "symbol": symbol,
                "side": "BUY",
                "order_configuration": {
                    "limit": {
                        "base_size": str(round(base_qty, 8)),
                        "price": str(round(best_bid, 8)),
                        "time_in_force": "GTC",
                    }
                },
            }

            logger.info(
                "Maker attempt %d/%d for %s: bid=%.2f qty=%.8f",
                maker_attempt, MAKER_RETRIES, symbol, best_bid, base_qty,
            )

            result = _request(api_key, private_key_pem, "POST", "/orders", json_body=body)
            data = result.get("data", result)
            logger.info("Revolut X POST /orders (maker) response: %s", json.dumps(data, default=str)[:500])

            venue_order_id = data.get("venue_order_id", data.get("id", client_order_id))
            state = (data.get("state") or data.get("status") or "PENDING").upper()

            # Vérifier rejet immédiat
            if state in _FAILED_STATES:
                _handle_failed_state(data, venue_order_id, state)

            # ── Poller pendant MAKER_WAIT_SECONDS ──
            polls = MAKER_WAIT_SECONDS // MAKER_POLL_INTERVAL
            for poll in range(polls):
                if state in _SUCCESS_STATES:
                    break
                _time.sleep(MAKER_POLL_INTERVAL)
                try:
                    poll_result = _request(api_key, private_key_pem, "GET", f"/orders/{venue_order_id}")
                    order_data = poll_result.get("data", poll_result)
                    state = (order_data.get("state") or order_data.get("status") or state).upper()
                    logger.debug("Maker poll %d: state=%s", poll + 1, state)
                    if state in _FAILED_STATES:
                        _handle_failed_state(order_data, venue_order_id, state)
                except ExchangeError:
                    raise
                except Exception as e:
                    logger.debug("Maker poll %d failed: %s", poll + 1, e)

            if state in _SUCCESS_STATES:
                logger.info("Maker order FILLED on attempt %d for %s", maker_attempt, symbol)
                return _build_order_result(
                    api_key, private_key_pem, symbol, quote_amount,
                    venue_order_id, state, data, order_type="maker",
                )

            # Pas FILLED → annuler et réessayer
            logger.info(
                "Maker attempt %d: order %s still %s after %ds, cancelling",
                maker_attempt, venue_order_id, state, MAKER_WAIT_SECONDS,
            )
            try:
                _request(api_key, private_key_pem, "DELETE", f"/orders/{venue_order_id}")
            except Exception as e:
                logger.warning("Failed to cancel maker order %s: %s", venue_order_id, e)

        except ExchangeError:
            raise  # solde insuffisant etc. → ne pas réessayer
        except Exception as e:
            logger.warning("Maker attempt %d failed: %s", maker_attempt, e)

    # ── Fallback Taker (market) ───────────────────────
    logger.info("All %d maker attempts failed for %s, falling back to taker (0.09%%)", MAKER_RETRIES, symbol)
    return _place_taker_order(api_key, private_key_pem, symbol, quote_amount)


def _place_taker_order(
    api_key: str,
    private_key_pem: str,
    symbol: str,
    quote_amount: float,
) -> dict[str, Any]:
    """Place un ordre market (taker, 0.09 % frais) en fallback."""
    import time as _time

    _FAILED_STATES = {"CANCELLED", "CANCELED", "REJECTED", "EXPIRED", "FAILED"}
    _SUCCESS_STATES = {"FILLED", "DONE", "COMPLETED"}

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
        logger.info("Revolut X POST /orders (taker) response: %s", json.dumps(data, default=str)[:500])

        venue_order_id = data.get("venue_order_id", data.get("id", client_order_id))
        state = (data.get("state") or data.get("status") or "PENDING").upper()

        if state in _FAILED_STATES:
            _handle_failed_state(data, venue_order_id, state)

        # Poller jusqu'à FILLED
        for attempt in range(8):
            if state in _SUCCESS_STATES:
                break
            _time.sleep(0.75)
            try:
                poll_result = _request(api_key, private_key_pem, "GET", f"/orders/{venue_order_id}")
                order_data = poll_result.get("data", poll_result)
                state = (order_data.get("state") or order_data.get("status") or state).upper()
                if state in _FAILED_STATES:
                    _handle_failed_state(order_data, venue_order_id, state)
            except ExchangeError:
                raise
            except Exception as e:
                logger.debug("Taker poll %d failed: %s", attempt + 1, e)

        return _build_order_result(
            api_key, private_key_pem, symbol, quote_amount,
            venue_order_id, state, data, order_type="taker",
        )
    except ExchangeError:
        raise
    except Exception as e:
        logger.error("Revolut X taker order failed: %s", e)
        raise ExchangeError(f"Order failed: {e}") from e


def _get_best_bid(symbol: str) -> float:
    """Récupère le meilleur prix bid depuis l'order-book public."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{BASE_URL}/public/order-book/{symbol}")
            resp.raise_for_status()
            data = resp.json()
        bids = data.get("data", {}).get("bids", [])
        if bids:
            if isinstance(bids[0], list):
                return float(bids[0][0])
            # Revolut X utilise "p" comme clé prix dans l'order-book
            return float(bids[0].get("p", bids[0].get("price", 0)))
        return 0.0
    except Exception as e:
        logger.warning("Failed to get best bid for %s: %s", symbol, e)
        return 0.0


def _handle_failed_state(data: dict, venue_order_id: str, state: str) -> None:
    """Lève l'exception appropriée pour un ordre en état d'échec."""
    failure_reason = data.get("failure_reason", "") or data.get("reject_reason", "") or data.get("reason", "") or ""
    logger.warning("Revolut X order %s state=%s reason=%s", venue_order_id, state, failure_reason)

    reason_upper = (failure_reason or "").upper()
    if any(kw in reason_upper for kw in ("INSUFFICIENT", "BALANCE", "FUNDS", "NOT_ENOUGH")):
        raise ExchangeError(f"Revolut X : solde insuffisant – {failure_reason}")
    if state in ("CANCELLED", "CANCELED") and not failure_reason:
        raise ExchangeError(
            "Revolut X : solde insuffisant – l'ordre a été annulé, "
            "vérifiez que votre portefeuille Cryptos · EUR est suffisamment approvisionné"
        )
    raise ExchangeError(f"Revolut X : ordre {state.lower()} – {failure_reason or state}")


def _build_order_result(
    api_key: str,
    private_key_pem: str,
    symbol: str,
    quote_amount: float,
    venue_order_id: str,
    state: str,
    initial_data: dict,
    order_type: str = "taker",
) -> dict[str, Any]:
    """Construit le dict résultat en extrayant les données de remplissage.

    3 niveaux de fallback :
    1. Champs directs de l'ordre (filled_size, average_filled_price…)
    2. Endpoint fills
    3. Estimation via le prix public
    """
    _SUCCESS_STATES = {"FILLED", "DONE", "COMPLETED"}

    # Récupérer les données finales de l'ordre
    try:
        poll_result = _request(api_key, private_key_pem, "GET", f"/orders/{venue_order_id}")
        order_data = poll_result.get("data", poll_result)
    except Exception:
        order_data = initial_data

    logger.info("Revolut X order %s final data: %s", venue_order_id, json.dumps(order_data, default=str)[:500])

    # Niveau 1 : champs directs
    total_qty = _extract_float(order_data, "filled_size", "filled_quantity", "executed_quantity", "base_size")
    avg_price = _extract_float(order_data, "average_fill_price", "average_filled_price", "avg_price", "average_price", "price")
    total_cost = _extract_float(order_data, "filled_value", "total_value", "cost", "quote_size")
    total_commission = _extract_float(order_data, "fee", "commission", "total_fee")

    # Niveau 2 : fills endpoint
    if total_qty == 0:
        fills_data = _get_order_fills(api_key, private_key_pem, venue_order_id)
        for fill in fills_data:
            qty = float(fill.get("base_size", 0) or fill.get("quantity", 0))
            price = float(fill.get("price", 0))
            fee = float(fill.get("fee", 0))
            total_qty += qty
            total_cost += qty * price
            total_commission += fee
        if total_qty > 0:
            avg_price = total_cost / total_qty

    if avg_price == 0 and total_qty > 0 and total_cost > 0:
        avg_price = total_cost / total_qty

    # Niveau 3 : estimation
    estimated = False
    if total_qty == 0 and state in _SUCCESS_STATES:
        estimated = True
        logger.warning("Revolut X order %s state=%s but no fill data – estimating", venue_order_id, state)
        try:
            avg_price = get_symbol_price_no_auth(symbol)
        except Exception:
            try:
                avg_price = get_symbol_price(api_key, private_key_pem, symbol)
            except Exception:
                avg_price = 0.0
        if avg_price > 0:
            total_qty = quote_amount / avg_price
            total_cost = quote_amount

    actual_spent = total_cost if total_cost > 0 else quote_amount
    base_asset = symbol.split("-")[0] if "-" in symbol else symbol
    commission_asset = order_data.get("fee_currency", base_asset) if total_commission > 0 else ""

    if commission_asset == base_asset and total_commission > 0:
        net_qty = total_qty - total_commission
    else:
        net_qty = total_qty

    # Frais estimés si pas de commission explicite
    if total_commission == 0 and order_type == "taker":
        fees_rate = 0.0009  # 0.09 %
        total_commission = actual_spent * fees_rate
        commission_asset = symbol.split("-")[1] if "-" in symbol else "EUR"

    logger.info(
        "Revolut X %s buy: symbol=%s, quote=%.2f, qty=%.8f, avg_price=%.2f, estimated=%s",
        order_type, symbol, quote_amount, net_qty, avg_price, estimated,
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
        "order_type": order_type,  # "maker" (0%) ou "taker" (0.09%)
        **({"estimated": True} if estimated else {}),
    }


def _extract_float(data: dict, *keys: str) -> float:
    """Tente d'extraire un float depuis l'un des champs donnés."""
    for key in keys:
        val = data.get(key)
        if val is not None:
            try:
                fval = float(val)
                if fval > 0:
                    return fval
            except (ValueError, TypeError):
                pass
    return 0.0


def _get_order_fills(
    api_key: str, private_key_pem: str, venue_order_id: str,
    max_retries: int = 5, delay: float = 1.0,
) -> list[dict]:
    """Récupère les fills d'un ordre.
    Retry jusqu'à max_retries fois car le fill peut mettre quelques secondes.
    """
    import time as _time
    for attempt in range(max_retries):
        try:
            result = _request(
                api_key, private_key_pem, "GET",
                f"/orders/fills/{venue_order_id}",
            )
            fills = result.get("data", [])
            if fills:
                return fills
            logger.debug(
                "Fills attempt %d/%d for %s: empty, retrying...",
                attempt + 1, max_retries, venue_order_id,
            )
            _time.sleep(delay)
        except ExchangeError:
            if attempt == max_retries - 1:
                raise
            _time.sleep(delay)
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
            best_ask = float(asks[0][0]) if isinstance(asks[0], list) else float(asks[0].get("p", asks[0].get("price", 0)))
            best_bid = float(bids[0][0]) if isinstance(bids[0], list) else float(bids[0].get("p", bids[0].get("price", 0)))
            return (best_ask + best_bid) / 2
        elif asks:
            return float(asks[0][0]) if isinstance(asks[0], list) else float(asks[0].get("p", asks[0].get("price", 0)))

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
