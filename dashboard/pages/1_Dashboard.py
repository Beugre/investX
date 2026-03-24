"""
Page 1 – Dashboard : vue d'ensemble du portfolio.
"""

import streamlit as st

from components.auth_guard import require_auth
from components.metrics import display_kpi_row, display_price_info
from components.tables import display_orders_table
from services.api_client import (
    get_portfolio_summary,
    get_dca_config,
    get_dca_v2_config,
    get_dca_v2_status,
    get_subscription_status,
    get_orders,
    get_latest_order,
)

st.set_page_config(page_title="Dashboard – InvestX", page_icon="📊", layout="wide")
st.title("📊 Dashboard")

token = require_auth()
if not token:
    st.stop()

# ── Statut abonnement ──
try:
    sub = get_subscription_status(token)
    status = sub.get("status", "none")
    if status == "active":
        st.success("✅ Abonnement actif")
    elif status == "none":
        st.warning("⚠️ Pas d'abonnement – allez dans Subscription pour vous abonner.")
    else:
        st.error(f"⚠️ Abonnement : {status}")
except Exception as e:
    st.error(f"Erreur chargement abonnement : {e}")

# ── Config DCA ──
try:
    v2_config = get_dca_v2_config(token)
    v2_active = v2_config and v2_config.get("enabled")
except Exception:
    v2_config = None
    v2_active = False

if v2_active:
    # Afficher les indicateurs DCA RSI v2
    st.subheader("🧠 DCA RSI v2")
    try:
        status = get_dca_v2_status(token)
        if "error" not in status:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("RSI (14j)", f"{status.get('rsi', 0):.1f}", status.get("rsi_bracket", ""))
            c2.metric("Régime", status.get("regime", "—"))
            mvrv = status.get("mvrv")
            c3.metric("MVRV", f"{mvrv:.2f}" if mvrv else "N/A")
            c4.metric("Montant prévu", f"${status.get('raw_amount', 0):.2f}")

            c5, c6, c7 = st.columns(3)
            c5.metric("BTC", f"${status.get('btc_amount', 0):.2f}", f"{status.get('btc_pct', 90)}%")
            c6.metric("ETH", f"${status.get('eth_amount', 0):.2f}", f"{status.get('eth_pct', 10)}%")
            c7.metric("Base quotidien", f"${status.get('base_amount', 0):.2f}")
        else:
            st.info(status["error"])
    except Exception as e:
        st.warning(f"Indicateurs v2 non disponibles : {e}")
else:
    try:
        config = get_dca_config(token)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Paire", config.get("symbol", "—"))
        with col2:
            st.metric("Montant quotidien", f"{config.get('daily_amount_eur', 0):.2f} €")
        with col3:
            enabled = config.get("enabled", False)
            st.metric("DCA", "✅ Activé" if enabled else "❌ Désactivé")
    except Exception as e:
        st.warning(f"Config DCA non disponible : {e}")

st.divider()

# ── Portfolio KPIs ──
st.subheader("📈 Portfolio")
try:
    summary = get_portfolio_summary(token)
    snapshots = summary.get("snapshots", [])
    if snapshots:
        for snap in snapshots:
            st.markdown(f"**{snap.get('symbol', '')}**")
            display_kpi_row(snap)
            display_price_info(snap)
    else:
        st.info("Aucune donnée portfolio. Les KPIs apparaîtront après votre premier achat DCA.")
except Exception as e:
    st.error(f"Erreur portfolio : {e}")

st.divider()

# ── Derniers ordres ──
st.subheader("🕐 Derniers ordres")
try:
    orders = get_orders(token, limit=10)
    display_orders_table(orders)
except Exception as e:
    st.warning(f"Impossible de charger les ordres : {e}")
