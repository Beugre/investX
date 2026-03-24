"""
Page 1 – Dashboard : vue d'ensemble du portfolio.
Auto-refresh toutes les 60 secondes.

Layout :
  Bloc 1 — KPIs (investi, valeur, PnL €, PnL %)
  Bloc 2 — Grand graphe : Portefeuille vs Capital investi
  Bloc 3 — 2 graphes côte à côte : PnL dans le temps / Prix + points d'achats
  Bloc 4 — Tableau des derniers ordres
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from components.auth_guard import require_auth
from components.metrics import display_kpi_row, display_price_info
from services.api_client import (
    get_portfolio_summary,
    get_portfolio_history,
    get_dca_config,
    get_dca_v2_config,
    get_dca_v2_status,
    get_subscription_status,
    get_orders,
)

st.set_page_config(page_title="Dashboard – InvestX", page_icon="📊", layout="wide")

# Auto-refresh toutes les 60 secondes (60000 ms)
st_autorefresh(interval=60_000, limit=None, key="dashboard_autorefresh")

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

# ── Config DCA (indicateurs rapides) ──
try:
    v2_config = get_dca_v2_config(token)
    v2_active = v2_config and v2_config.get("enabled")
except Exception:
    v2_config = None
    v2_active = False

if v2_active:
    st.subheader("🧠 DCA RSI v2")
    try:
        v2_status = get_dca_v2_status(token)
        if "error" not in v2_status:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("RSI (14j)", f"{v2_status.get('rsi', 0):.1f}", v2_status.get("rsi_bracket", ""))
            c2.metric("Régime", v2_status.get("regime", "—"))
            mvrv = v2_status.get("mvrv")
            c3.metric("MVRV", f"{mvrv:.2f}" if mvrv else "N/A")
            c4.metric("Montant prévu", f"${v2_status.get('raw_amount', 0):.2f}")
        else:
            st.info(v2_status["error"])
    except Exception as e:
        st.warning(f"Indicateurs v2 non disponibles : {e}")
else:
    try:
        config = get_dca_config(token)
        c1, c2, c3 = st.columns(3)
        c1.metric("Paire", config.get("symbol", "—"))
        c2.metric("Montant quotidien", f"${config.get('daily_amount_eur', 0):.2f}")
        enabled = config.get("enabled", False)
        c3.metric("DCA", "✅ Activé" if enabled else "❌ Désactivé")
    except Exception as e:
        st.warning(f"Config DCA non disponible : {e}")

st.divider()

# ══════════════════════════════════════════════════════
# BLOC 1 — KPIs
# ══════════════════════════════════════════════════════
st.subheader("📈 Portfolio")
snapshot = None
try:
    summary = get_portfolio_summary(token)
    snapshots_list = summary.get("snapshots", [])
    if snapshots_list:
        snapshot = snapshots_list[0]
        st.markdown(f"**{snapshot.get('symbol', '')}**")
        display_kpi_row(snapshot)
        display_price_info(snapshot)
    else:
        st.info("Aucune donnée portfolio. Les KPIs apparaîtront après votre premier achat DCA.")
except Exception as e:
    st.error(f"Erreur portfolio : {e}")

st.divider()

# ══════════════════════════════════════════════════════
# Chargement des données pour les graphes
# ══════════════════════════════════════════════════════
symbol = snapshot.get("symbol", "BTCUSDC") if snapshot else "BTCUSDC"

# ── Filtres ──
filter_col1, filter_col2 = st.columns([1, 3])
with filter_col1:
    period_options = {"7J": 7, "30J": 30, "90J": 90, "ALL": 365}
    period_label = st.selectbox("📅 Période", list(period_options.keys()), index=1)
    period_limit = period_options[period_label]

# Charger historique et ordres
history: list[dict] = []
orders: list[dict] = []
try:
    history = get_portfolio_history(token, symbol=symbol, limit=period_limit)
except Exception:
    pass
try:
    orders = get_orders(token, symbol=symbol, limit=500)
except Exception:
    pass

# Préparer la dataframe des snapshots
df_hist = pd.DataFrame()
if history:
    df_hist = pd.DataFrame(history)
    if "captured_at" in df_hist.columns:
        df_hist["captured_at"] = pd.to_datetime(df_hist["captured_at"])
        df_hist = df_hist.sort_values("captured_at")

# Préparer la dataframe des ordres
df_orders = pd.DataFrame()
if orders:
    df_orders = pd.DataFrame(orders)
    if "executed_at" in df_orders.columns:
        df_orders["executed_at"] = pd.to_datetime(df_orders["executed_at"])
        df_orders = df_orders.sort_values("executed_at")
        # Filtrer par période
        if not df_orders.empty and period_label != "ALL":
            cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=period_limit)
            df_orders = df_orders[df_orders["executed_at"] >= cutoff]


# ══════════════════════════════════════════════════════
# BLOC 2 — Grand graphe : Portefeuille vs Capital investi
# ══════════════════════════════════════════════════════
st.subheader("💼 Portefeuille vs Capital investi")

if not df_hist.empty and "invested_total_eur" in df_hist.columns:
    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(
        x=df_hist["captured_at"],
        y=df_hist["invested_total_eur"],
        name="Capital investi",
        line=dict(color="#636EFA", width=2),
        fill=None,
    ))
    fig_main.add_trace(go.Scatter(
        x=df_hist["captured_at"],
        y=df_hist["market_value_eur"],
        name="Valeur portefeuille",
        line=dict(color="#00CC96", width=2),
        fill="tonexty",
        fillcolor="rgba(0,204,150,0.15)",
    ))
    fig_main.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="",
        yaxis_title="$ USD",
        hovermode="x unified",
    )
    st.plotly_chart(fig_main, use_container_width=True)
else:
    st.info("📊 Le graphe apparaîtra après quelques snapshots (actualisation toutes les minutes).")

st.divider()

# ══════════════════════════════════════════════════════
# BLOC 3 — Deux graphes côte à côte
# ══════════════════════════════════════════════════════
col_left, col_right = st.columns(2)

# ── Graphe gauche : PnL dans le temps ──
with col_left:
    st.subheader("📊 PnL dans le temps")

    pnl_mode = st.radio("Métrique", ["$", "%"], horizontal=True, key="pnl_mode")

    if not df_hist.empty and "pnl_value_eur" in df_hist.columns:
        pnl_col = "pnl_value_eur" if pnl_mode == "$" else "pnl_percent"
        y_label = "PnL ($)" if pnl_mode == "$" else "PnL (%)"

        # Couleur conditionnelle : vert si dernier PnL > 0, rouge sinon
        last_pnl = df_hist[pnl_col].iloc[-1] if len(df_hist) > 0 else 0
        area_color = "rgba(0,204,150,0.3)" if last_pnl >= 0 else "rgba(239,85,59,0.3)"
        line_color = "#00CC96" if last_pnl >= 0 else "#EF553B"

        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Scatter(
            x=df_hist["captured_at"],
            y=df_hist[pnl_col],
            name=y_label,
            line=dict(color=line_color, width=2),
            fill="tozeroy",
            fillcolor=area_color,
        ))
        # Ligne zéro
        fig_pnl.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig_pnl.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="",
            yaxis_title=y_label,
            showlegend=False,
            hovermode="x unified",
        )
        st.plotly_chart(fig_pnl, use_container_width=True)
    else:
        st.info("📊 Données insuffisantes pour le graphe PnL.")

# ── Graphe droit : Prix + points d'achats ──
with col_right:
    st.subheader("🛒 Prix & achats DCA")

    if not df_orders.empty and "price" in df_orders.columns:
        fig_buy = go.Figure()

        # Ligne de prix (à partir des ordres)
        fig_buy.add_trace(go.Scatter(
            x=df_orders["executed_at"],
            y=df_orders["price"],
            name="Prix d'achat",
            line=dict(color="#636EFA", width=1.5),
            mode="lines",
        ))

        # Points d'achats DCA
        fig_buy.add_trace(go.Scatter(
            x=df_orders["executed_at"],
            y=df_orders["price"],
            name="Achats DCA",
            mode="markers",
            marker=dict(
                size=df_orders["amount_eur"].clip(lower=3, upper=20) if "amount_eur" in df_orders.columns else 8,
                color="#00CC96",
                symbol="circle",
                line=dict(width=1, color="white"),
            ),
            customdata=df_orders[["amount_eur", "quantity"]].values if {"amount_eur", "quantity"}.issubset(df_orders.columns) else None,
            hovertemplate=(
                "<b>%{x|%d/%m %Hh%M}</b><br>"
                "Prix: $%{y:,.2f}<br>"
                "Montant: $%{customdata[0]:.2f}<br>"
                "Quantité: %{customdata[1]:.8f}<extra></extra>"
            ),
        ))

        # Ligne prix moyen
        if snapshot:
            avg = snapshot.get("avg_buy_price", 0)
            if avg > 0:
                fig_buy.add_hline(
                    y=avg, line_dash="dot", line_color="orange",
                    annotation_text=f"Moy: ${avg:,.0f}",
                    annotation_position="top right",
                )

        fig_buy.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="",
            yaxis_title="Prix ($)",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_buy, use_container_width=True)
    else:
        st.info("🛒 Les points d'achats apparaîtront après vos premières exécutions DCA.")

st.divider()

# ══════════════════════════════════════════════════════
# BLOC 4 — Tableau des derniers ordres
# ══════════════════════════════════════════════════════
st.subheader("🕐 Derniers ordres")

if not df_orders.empty:
    display_cols = {
        "executed_at": "Date",
        "symbol": "Paire",
        "amount_eur": "Montant ($)",
        "quantity": "Quantité",
        "price": "Prix ($)",
        "status": "Statut",
        "source": "Source",
    }
    available = [c for c in display_cols if c in df_orders.columns]
    df_display = df_orders[available].copy()
    df_display = df_display.sort_values("executed_at", ascending=False).head(20)
    df_display.columns = [display_cols[c] for c in available]

    # Formatage
    if "Date" in df_display.columns:
        df_display["Date"] = df_display["Date"].dt.strftime("%d/%m/%Y %H:%M")

    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("Aucun ordre pour le moment.")
