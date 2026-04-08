"""
Client API – appels HTTP vers le backend FastAPI.
"""

from __future__ import annotations

from typing import Any

import requests
import streamlit as st

API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _get(path: str, token: str, params: dict | None = None) -> Any:
    r = requests.get(
        f"{API_BASE_URL}{path}",
        headers=_headers(token),
        params=params,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _post(path: str, token: str, json: dict | None = None) -> Any:
    r = requests.post(
        f"{API_BASE_URL}{path}",
        headers=_headers(token),
        json=json,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _put(path: str, token: str, json: dict | None = None) -> Any:
    r = requests.put(
        f"{API_BASE_URL}{path}",
        headers=_headers(token),
        json=json,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _delete(path: str, token: str) -> Any:
    r = requests.delete(
        f"{API_BASE_URL}{path}",
        headers=_headers(token),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


# ── User ──
def get_me(token: str) -> dict:
    return _get("/me", token)


def get_user_profile(token: str) -> dict:
    return _get("/me/profile", token)


def update_user_profile(token: str, data: dict) -> dict:
    return _put("/me/profile", token, json=data)


def init_onboarding(token: str) -> dict:
    return _post("/onboarding/init", token)


# ── Subscription ──
def get_subscription_status(token: str) -> dict:
    return _get("/billing/status", token)


def create_checkout_session(token: str) -> dict:
    return _post("/billing/create-checkout-session", token)


def create_customer_portal(token: str) -> dict:
    return _post("/billing/create-customer-portal-session", token)


def sync_subscription(token: str) -> dict:
    return _post("/billing/sync", token)


# ── DCA ──
def get_dca_config(token: str) -> dict:
    return _get("/dca/config", token)


def update_dca_config(token: str, config: dict) -> dict:
    return _put("/dca/config", token, json=config)


def enable_dca(token: str) -> dict:
    return _post("/dca/enable", token)


def disable_dca(token: str) -> dict:
    return _post("/dca/disable", token)


# ── DCA v2 (RSI) ──
def get_dca_v2_config(token: str) -> dict:
    return _get("/dca/v2/config", token)


def update_dca_v2_config(token: str, config: dict) -> dict:
    return _put("/dca/v2/config", token, json=config)


def enable_dca_v2(token: str) -> dict:
    return _post("/dca/v2/enable", token)


def disable_dca_v2(token: str) -> dict:
    return _post("/dca/v2/disable", token)


def force_execute_dca_v2(token: str) -> dict:
    """Timeout long : le maker order peut prendre 30s+ pour se remplir."""
    r = requests.post(
        f"{API_BASE_URL}/dca/v2/force-execute",
        headers=_headers(token),
        timeout=90,
    )
    r.raise_for_status()
    return r.json()


def get_dca_v2_status(token: str) -> dict:
    return _get("/dca/v2/status", token)


def get_dca_v2_spending(token: str) -> dict:
    return _get("/dca/v2/spending", token)


def get_dca_v2_crash_reserve(token: str) -> dict:
    return _get("/dca/v2/crash-reserve", token)


# ── Take-Profit ──
def get_take_profit_config(token: str) -> dict:
    return _get("/dca/v2/take-profit", token)


def update_take_profit_config(token: str, data: dict) -> dict:
    return _put("/dca/v2/take-profit", token, json=data)


def get_dca_v2_cycle_logs(token: str, limit: int = 30) -> list:
    return _get("/dca/v2/cycle-logs", token, params={"limit": limit})


def get_dca_v2_auto_config(base_daily_amount: float) -> dict:
    """Pas besoin de token – endpoint public."""
    r = requests.get(
        f"{API_BASE_URL}/dca/v2/auto-config",
        params={"base_daily_amount": base_daily_amount},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def simulate_dca_v2(payload: dict) -> dict:
    """Pas besoin de token – endpoint public."""
    r = requests.post(
        f"{API_BASE_URL}/dca/v2/simulate",
        json=payload,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def backtest_dca_v2(base_daily_amount: float, days: int = 365, symbol: str = "BTCUSDC") -> dict:
    """Backtesting RSI v2 – endpoint public."""
    r = requests.get(
        f"{API_BASE_URL}/dca/v2/backtest",
        params={"base_daily_amount": base_daily_amount, "days": days, "symbol": symbol},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ── Binance ──
def get_binance_status(token: str) -> dict:
    return _get("/binance/status", token)


def connect_binance(token: str, api_key: str, api_secret: str) -> dict:
    return _post("/binance/connect", token, json={
        "api_key": api_key,
        "api_secret": api_secret,
    })


def validate_binance(token: str) -> dict:
    return _post("/binance/validate", token)


def disconnect_binance(token: str) -> dict:
    return _delete("/binance/disconnect", token)


# ── Revolut X ──
def get_revolutx_status(token: str) -> dict:
    return _get("/revolutx/status", token)


def generate_revolutx_keys(token: str) -> dict:
    return _post("/revolutx/generate-keys", token)


def connect_revolutx(token: str, api_key: str, private_key_pem: str) -> dict:
    return _post("/revolutx/connect", token, json={
        "api_key": api_key,
        "private_key_pem": private_key_pem,
    })


def validate_revolutx(token: str) -> dict:
    return _post("/revolutx/validate", token)


def disconnect_revolutx(token: str) -> dict:
    return _delete("/revolutx/disconnect", token)


# ── Exchange actif ──
def get_active_exchange(token: str) -> str:
    result = _get("/me/exchange", token)
    return result.get("active_exchange", "binance")


def set_active_exchange(token: str, exchange: str) -> dict:
    return _put("/me/exchange", token, json={"exchange": exchange})


def get_exchange_balance(token: str) -> dict:
    return _get("/me/balance", token)


# ── Portfolio ──
def get_portfolio_summary(token: str) -> dict:
    return _get("/portfolio/summary", token)


def get_portfolio_history(token: str, symbol: str | None = None, limit: int = 30) -> list:
    params: dict = {"limit": limit}
    if symbol:
        params["symbol"] = symbol
    return _get("/portfolio/history", token, params=params)


def get_orders(token: str, symbol: str | None = None, limit: int = 50) -> list:
    params: dict = {"limit": limit}
    if symbol:
        params["symbol"] = symbol
    return _get("/orders", token, params=params)


def export_orders_csv(token: str, symbol: str | None = None, limit: int = 500) -> str:
    """Télécharge les ordres au format CSV (retourne le contenu texte)."""
    params: dict = {"limit": limit}
    if symbol:
        params["symbol"] = symbol
    import requests
    resp = requests.get(
        f"{API_BASE}/orders/export",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def get_latest_order(token: str, symbol: str = "BTCUSDC") -> dict | None:
    return _get("/orders/latest", token, params={"symbol": symbol})


# ── Telegram ──
def get_telegram_settings(token: str) -> dict:
    return _get("/telegram/settings", token)


def link_telegram(token: str, chat_id: str, username: str | None = None) -> dict:
    return _post("/telegram/link", token, json={
        "chat_id": chat_id,
        "username": username,
    })


def test_telegram(token: str) -> dict:
    return _post("/telegram/test", token)


def update_telegram_settings(token: str, settings: dict) -> dict:
    return _put("/telegram/settings", token, json=settings)


# ── Alertes de prix ──
def list_alerts(token: str) -> list:
    return _get("/alerts", token)


def create_alert(token: str, symbol: str, target_price: float, direction: str) -> dict:
    return _post("/alerts", token, json={
        "symbol": symbol,
        "target_price": target_price,
        "direction": direction,
    })


def delete_alert(token: str, alert_id: str) -> dict:
    return _delete(f"/alerts/{alert_id}", token)


# ── Admin ──
def admin_overview(token: str) -> dict:
    return _get("/admin/overview", token)


def admin_list_users(token: str) -> list:
    return _get("/admin/users", token)


def admin_recent_orders(token: str, limit: int = 50) -> list:
    return _get("/admin/recent-orders", token, params={"limit": limit})
