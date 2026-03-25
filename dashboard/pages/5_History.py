"""
Page 5 – Historique des ordres et snapshots.
"""

import streamlit as st

from components.auth_guard import require_auth
from components.tables import display_orders_table, display_snapshots_table
from services.api_client import (
    get_orders,
    get_portfolio_history,
    get_binance_status,
    get_revolutx_status,
)

st.set_page_config(page_title="History – InvestX", page_icon="📜")
st.title("📜 Historique")

token = require_auth()
if not token:
    st.stop()

# ── Paires dynamiques selon les exchanges connectés ──
BINANCE_PAIRS = ["BTCUSDC", "ETHUSDC", "BNBUSDC", "ADAUSDC", "SOLUSDC"]
REVOLUTX_PAIRS = ["BTC-EUR", "ETH-EUR", "BNB-EUR", "ADA-EUR", "SOL-EUR"]

available_symbols: list[str] = [""]
try:
    bs = get_binance_status(token)
    if bs.get("is_connected", False):
        available_symbols.extend(BINANCE_PAIRS)
except Exception:
    pass
try:
    rx = get_revolutx_status(token)
    if rx.get("is_connected", False):
        available_symbols.extend(REVOLUTX_PAIRS)
except Exception:
    pass
if len(available_symbols) == 1:
    available_symbols.extend(BINANCE_PAIRS)

tab_orders, tab_snapshots = st.tabs(["📋 Ordres", "📸 Snapshots"])

with tab_orders:
    st.subheader("Historique des ordres")
    symbol_filter = st.selectbox("Filtrer par paire", available_symbols, key="order_symbol")
    limit = st.slider("Nombre d'ordres", 10, 200, 50, key="order_limit")

    try:
        orders = get_orders(
            token,
            symbol=symbol_filter if symbol_filter else None,
            limit=limit,
        )
        display_orders_table(orders)
    except Exception as e:
        st.error(f"Erreur : {e}")

with tab_snapshots:
    st.subheader("Historique des snapshots portfolio")
    symbol_filter2 = st.selectbox("Filtrer par paire", available_symbols, key="snap_symbol")
    limit2 = st.slider("Nombre de snapshots", 10, 100, 30, key="snap_limit")

    try:
        snapshots = get_portfolio_history(
            token,
            symbol=symbol_filter2 if symbol_filter2 else None,
            limit=limit2,
        )
        display_snapshots_table(snapshots)
    except Exception as e:
        st.error(f"Erreur : {e}")
