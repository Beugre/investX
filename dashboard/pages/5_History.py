"""
Page 5 – Historique des ordres et snapshots.
"""

import streamlit as st
import pandas as pd

from components.auth_guard import require_auth
from components.tables import display_orders_table, display_snapshots_table
from services.api_client import (
    get_orders,
    get_portfolio_history,
    get_binance_status,
    get_revolutx_status,
    export_orders_csv,
    get_dca_v2_cycle_logs,
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

tab_orders, tab_snapshots, tab_cycles = st.tabs(["📋 Ordres", "📸 Snapshots", "🔄 Cycles v2"])

with tab_orders:
    st.subheader("Historique des ordres")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        symbol_filter = st.selectbox("Filtrer par paire", available_symbols, key="order_symbol")
    with col2:
        limit = st.slider("Nombre d'ordres", 10, 200, 50, key="order_limit")
    with col3:
        st.write("")
        st.write("")
        if st.button("📥 Export CSV"):
            try:
                csv_data = export_orders_csv(
                    token,
                    symbol=symbol_filter if symbol_filter else None,
                    limit=500,
                )
                st.download_button(
                    "💾 Télécharger",
                    csv_data,
                    file_name="investx_orders.csv",
                    mime="text/csv",
                )
            except Exception as e:
                st.error(f"Erreur export : {e}")

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

with tab_cycles:
    st.subheader("🔄 Historique des cycles DCA v2")
    cycle_limit = st.slider("Nombre de cycles", 10, 100, 30, key="cycle_limit")
    try:
        logs = get_dca_v2_cycle_logs(token, limit=cycle_limit)
        if logs:
            df = pd.DataFrame(logs)

            # Le backend sauvegarde "created_at" (pas "started_at")
            time_col = "started_at" if "started_at" in df.columns else "created_at"
            if time_col in df.columns:
                df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
                df = df.sort_values(time_col, ascending=True)

            # Le backend sauvegarde "total_amount" (pas "total_invested")
            amount_col = "total_invested" if "total_invested" in df.columns else "total_amount"

            # Graphique : montant investi par cycle
            if amount_col in df.columns and time_col in df.columns:
                st.markdown("**💰 Montant investi par cycle**")
                chart_data = df.set_index(time_col)[[amount_col]].dropna()
                if not chart_data.empty:
                    st.bar_chart(chart_data)

            # Graphique : nombre d'ordres par cycle (si disponible)
            orders_col = "orders_count" if "orders_count" in df.columns else None
            if not orders_col and "pair_orders" in df.columns:
                df["orders_count"] = df["pair_orders"].apply(
                    lambda x: len(x) if isinstance(x, list) else 0
                )
                orders_col = "orders_count"
            if orders_col and time_col in df.columns:
                st.markdown("**📊 Nombre d'ordres par cycle**")
                chart_data2 = df.set_index(time_col)[[orders_col]].dropna()
                if not chart_data2.empty:
                    st.bar_chart(chart_data2)

            # Tableau détaillé
            st.markdown("**📋 Détails des cycles**")
            display_cols = [c for c in [time_col, "status", "mode", amount_col,
                                        "orders_count", "rsi", "regime"] if c in df.columns]
            df_display = df[display_cols].copy()
            if time_col in df_display.columns:
                df_display[time_col] = df_display[time_col].dt.strftime("%d/%m/%Y %H:%M")
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun cycle v2 enregistré.")
    except Exception as e:
        st.error(f"Erreur : {e}")
