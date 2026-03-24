"""
Composants métriques pour le dashboard.
"""

from __future__ import annotations

import streamlit as st


def display_kpi_row(snapshot: dict) -> None:
    """Affiche une ligne de KPIs portfolio."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "💰 Capital investi",
            f"{snapshot.get('invested_total_eur', 0):,.2f} €",
        )

    with col2:
        st.metric(
            "📦 Quantité détenue",
            f"{snapshot.get('quantity_total', 0):.8f}",
        )

    with col3:
        st.metric(
            "📈 Valeur actuelle",
            f"{snapshot.get('market_value_eur', 0):,.2f} €",
        )

    with col4:
        pnl = snapshot.get("pnl_value_eur", 0)
        pnl_pct = snapshot.get("pnl_percent", 0)
        st.metric(
            "📊 PnL",
            f"{pnl:+,.2f} €",
            delta=f"{pnl_pct:+.2f}%",
        )


def display_price_info(snapshot: dict) -> None:
    """Affiche prix moyen et prix marché."""
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Prix moyen d'achat", f"{snapshot.get('avg_buy_price', 0):,.2f} €")
    with col2:
        st.metric("Prix marché actuel", f"{snapshot.get('market_price', 0):,.2f} €")
