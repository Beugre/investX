"""
Composants tableaux pour le dashboard.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def display_orders_table(orders: list[dict]) -> None:
    """Affiche un tableau d'ordres."""
    if not orders:
        st.info("Aucun ordre pour le moment.")
        return

    df = pd.DataFrame(orders)
    columns_display = [
        "executed_at", "symbol", "side", "amount_eur",
        "quantity", "price", "status", "source",
    ]
    available = [c for c in columns_display if c in df.columns]
    st.dataframe(df[available], use_container_width=True, hide_index=True)


def display_snapshots_table(snapshots: list[dict]) -> None:
    """Affiche un tableau de snapshots portfolio."""
    if not snapshots:
        st.info("Aucun snapshot disponible.")
        return

    df = pd.DataFrame(snapshots)
    columns_display = [
        "captured_at", "symbol", "quantity_total", "invested_total_eur",
        "avg_buy_price", "market_price", "market_value_eur",
        "pnl_value_eur", "pnl_percent",
    ]
    available = [c for c in columns_display if c in df.columns]
    st.dataframe(df[available], use_container_width=True, hide_index=True)
