"""
Page 1 – Dashboard : vue d'ensemble du portfolio.
Auto-refresh toutes les 60 secondes.

Layout par exchange (onglets si 2 exchanges connectés) :
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
    get_binance_status,
    get_revolutx_status,
    get_active_exchange,
    get_exchange_balance,
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

# ── Exchange actif et devise ──
try:
    active_exchange = get_active_exchange(token)
except Exception:
    active_exchange = "binance"

is_revolutx_active = active_exchange == "revolutx"
active_cs = "€" if is_revolutx_active else "$"

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
            c4.metric("Montant prévu", f"{active_cs}{v2_status.get('raw_amount', 0):.2f}")

            # ── Balance exchange ──
            try:
                bal_data = get_exchange_balance(token)
                balances = bal_data.get("balances", {})
                if balances:
                    bal_cols = st.columns(len(balances))
                    for i, (asset, amount) in enumerate(balances.items()):
                        sym = "€" if asset == "EUR" else "$" if asset == "USDC" else ""
                        bal_cols[i].metric(f"💰 Balance {asset}", f"{sym}{amount:,.2f}")
            except Exception:
                pass

            # ── Spending caps ──
            spending = v2_status.get("spending", {})
            caps = v2_status.get("caps", {})
            if spending or caps:
                st.markdown("**📊 Limites de dépenses**")
                sc1, sc2, sc3 = st.columns(3)
                daily_spent = spending.get("daily", 0)
                daily_cap = caps.get("daily_cap", 0)
                weekly_spent = spending.get("weekly", 0)
                weekly_cap = caps.get("weekly_cap", 0)
                monthly_spent = spending.get("monthly", 0)
                monthly_cap = caps.get("monthly_cap", 0)
                sc1.metric("Jour", f"{active_cs}{daily_spent:.2f} / {daily_cap:.0f}")
                sc2.metric("Semaine", f"{active_cs}{weekly_spent:.2f} / {weekly_cap:.0f}")
                sc3.metric("Mois", f"{active_cs}{monthly_spent:.2f} / {monthly_cap:.0f}")
        else:
            st.info(v2_status["error"])
    except Exception as e:
        st.warning(f"Indicateurs v2 non disponibles : {e}")
else:
    try:
        config = get_dca_config(token)
        c1, c2, c3 = st.columns(3)
        c1.metric("Paire", config.get("symbol", "—"))
        c2.metric("Montant quotidien", f"{active_cs}{config.get('daily_amount_eur', 0):.2f}")
        enabled = config.get("enabled", False)
        c3.metric("DCA", "✅ Activé" if enabled else "❌ Désactivé")
    except Exception as e:
        st.warning(f"Config DCA non disponible : {e}")

st.divider()


# ══════════════════════════════════════════════════════
# Détection des exchanges connectés
# ══════════════════════════════════════════════════════
BINANCE_PAIRS = ["BTCUSDC", "ETHUSDC", "BNBUSDC", "ADAUSDC", "SOLUSDC"]
REVOLUTX_PAIRS = ["BTC-EUR", "ETH-EUR", "BNB-EUR", "ADA-EUR", "SOL-EUR"]

binance_connected = False
revolutx_connected = False
try:
    bs = get_binance_status(token)
    binance_connected = bs.get("is_connected", False)
except Exception:
    pass
try:
    rx = get_revolutx_status(token)
    revolutx_connected = rx.get("is_connected", False)
except Exception:
    pass

exchanges_info: list[tuple[str, list[str], str]] = []
if binance_connected:
    exchanges_info.append(("🟡 Binance", BINANCE_PAIRS, "$"))
if revolutx_connected:
    exchanges_info.append(("🔵 Revolut X", REVOLUTX_PAIRS, "€"))
if not exchanges_info:
    exchanges_info.append(("🟡 Binance", BINANCE_PAIRS, "$"))


# ══════════════════════════════════════════════════════
# Fonction de rendu portfolio pour un exchange
# ══════════════════════════════════════════════════════
def render_exchange_portfolio(
    token: str,
    symbols: list[str],
    cs: str,
    tab_key: str,
) -> None:
    """Render full portfolio dashboard for one exchange."""

    # ── Sélecteur de paire ──
    symbol = st.selectbox(
        "Paire", symbols, index=0, key=f"symbol_{tab_key}"
    )

    # ── Filtres ──
    period_options = {"7J": 7, "30J": 30, "90J": 90, "ALL": 365}
    period_label = st.selectbox(
        "📅 Période",
        list(period_options.keys()),
        index=1,
        key=f"period_{tab_key}",
    )
    period_limit = period_options[period_label]

    # ── Chargement des données ──
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

    # ── KPIs (snapshot le plus récent) ──
    st.subheader("📈 Portfolio")
    snapshot = None
    if history:
        snapshot = history[0]
        st.markdown(f"**{snapshot.get('symbol', '')}**")
        display_kpi_row(snapshot, cs)
        display_price_info(snapshot, cs)
    else:
        st.info(
            "Aucune donnée portfolio pour cette paire. "
            "Les KPIs apparaîtront après votre premier achat DCA."
        )

    st.divider()

    # ── Préparer les dataframes ──
    df_hist = pd.DataFrame()
    if history:
        df_hist = pd.DataFrame(history)
        if "captured_at" in df_hist.columns:
            df_hist["captured_at"] = pd.to_datetime(df_hist["captured_at"])
            df_hist = df_hist.sort_values("captured_at")

    df_orders = pd.DataFrame()
    if orders:
        df_orders = pd.DataFrame(orders)
        if "executed_at" in df_orders.columns:
            df_orders["executed_at"] = pd.to_datetime(df_orders["executed_at"])
            df_orders = df_orders.sort_values("executed_at")
            if not df_orders.empty and period_label != "ALL":
                cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=period_limit)
                df_orders = df_orders[df_orders["executed_at"] >= cutoff]

    # ── Graphe : Portefeuille vs Capital investi ──
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
            yaxis_title=f"{cs}",
            hovermode="x unified",
        )
        st.plotly_chart(fig_main, use_container_width=True, key=f"fig_main_{tab_key}")
    else:
        st.info("📊 Le graphe apparaîtra après quelques snapshots.")

    st.divider()

    # ── Deux graphes côte à côte ──
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 PnL dans le temps")
        pnl_mode = st.radio(
            "Métrique", [cs, "%"], horizontal=True, key=f"pnl_mode_{tab_key}"
        )
        if not df_hist.empty and "pnl_value_eur" in df_hist.columns:
            pnl_col = "pnl_value_eur" if pnl_mode == cs else "pnl_percent"
            y_label = f"PnL ({cs})" if pnl_mode == cs else "PnL (%)"
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
            fig_pnl.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig_pnl.update_layout(
                height=350,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="",
                yaxis_title=y_label,
                showlegend=False,
                hovermode="x unified",
            )
            st.plotly_chart(fig_pnl, use_container_width=True, key=f"fig_pnl_{tab_key}")
        else:
            st.info("📊 Données insuffisantes pour le graphe PnL.")

    with col_right:
        st.subheader("🛒 Prix & achats DCA")
        if not df_orders.empty and "price" in df_orders.columns:
            fig_buy = go.Figure()
            fig_buy.add_trace(go.Scatter(
                x=df_orders["executed_at"],
                y=df_orders["price"],
                name="Prix d'achat",
                line=dict(color="#636EFA", width=1.5),
                mode="lines",
            ))
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
                    f"Prix: {cs}%{{y:,.2f}}<br>"
                    f"Montant: {cs}%{{customdata[0]:.2f}}<br>"
                    "Quantité: %{customdata[1]:.8f}<extra></extra>"
                ),
            ))
            if snapshot:
                avg = snapshot.get("avg_buy_price", 0)
                if avg > 0:
                    fig_buy.add_hline(
                        y=avg, line_dash="dot", line_color="orange",
                        annotation_text=f"Moy: {cs}{avg:,.0f}",
                        annotation_position="top right",
                    )
            fig_buy.update_layout(
                height=350,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="",
                yaxis_title=f"Prix ({cs})",
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified",
            )
            st.plotly_chart(fig_buy, use_container_width=True, key=f"fig_buy_{tab_key}")
        else:
            st.info("🛒 Les points d'achats apparaîtront après vos premières exécutions DCA.")

    st.divider()

    # ── Tableau des derniers ordres ──
    st.subheader("🕐 Derniers ordres")
    if not df_orders.empty:
        display_cols = {
            "executed_at": "Date",
            "symbol": "Paire",
            "amount_eur": f"Montant ({cs})",
            "quantity": "Quantité",
            "price": f"Prix ({cs})",
            "status": "Statut",
            "source": "Source",
        }
        available = [c for c in display_cols if c in df_orders.columns]
        df_display = df_orders[available].copy()
        df_display = df_display.sort_values("executed_at", ascending=False).head(20)
        df_display.columns = [display_cols[c] for c in available]
        if "Date" in df_display.columns:
            df_display["Date"] = df_display["Date"].dt.strftime("%d/%m/%Y %H:%M")
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun ordre pour le moment.")


# ══════════════════════════════════════════════════════
# Rendu : onglets si 2 exchanges, sinon direct
# ══════════════════════════════════════════════════════
if len(exchanges_info) >= 2:
    tabs = st.tabs([ex[0] for ex in exchanges_info])
    for tab, (label, pairs, cs) in zip(tabs, exchanges_info):
        with tab:
            render_exchange_portfolio(token, pairs, cs, tab_key=label)
else:
    label, pairs, cs = exchanges_info[0]
    render_exchange_portfolio(token, pairs, cs, tab_key=label)
