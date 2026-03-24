"""
Composants formulaires réutilisables.
"""

from __future__ import annotations

import streamlit as st

ALLOWED_SYMBOLS = ["BTCUSDC", "ETHUSDC", "BNBUSDC", "ADAUSDC", "SOLUSDC"]
HOURS = list(range(24))
MINUTES = [0, 15, 30, 45]


def dca_config_form(current_config: dict | None = None) -> dict | None:
    """Formulaire de configuration DCA. Retourne les données si soumis."""
    config = current_config or {}

    with st.form("dca_config_form"):
        symbol = st.selectbox(
            "Paire",
            ALLOWED_SYMBOLS,
            index=ALLOWED_SYMBOLS.index(config.get("symbol", "BTCUSDC")),
        )
        daily_amount = st.number_input(
            "Montant quotidien ($)",
            min_value=0.5,
            max_value=10000.0,
            value=float(config.get("daily_amount_eur", 1.0)),
            step=0.5,
        )
        hour = st.selectbox(
            "Heure d'exécution",
            HOURS,
            index=config.get("execution_hour", 10),
        )
        minute = st.selectbox(
            "Minute d'exécution",
            MINUTES,
            index=MINUTES.index(config.get("execution_minute", 0))
            if config.get("execution_minute", 0) in MINUTES
            else 0,
        )
        enabled = st.toggle(
            "DCA activé",
            value=config.get("enabled", False),
        )

        submitted = st.form_submit_button("💾 Sauvegarder")

        if submitted:
            return {
                "enabled": enabled,
                "symbol": symbol,
                "daily_amount_eur": daily_amount,
                "execution_hour": hour,
                "execution_minute": minute,
                "timezone": "Europe/Paris",
                "mode": "simple",
            }

    return None
