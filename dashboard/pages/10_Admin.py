"""
Page 10 – Dashboard Admin (réservé à l'administrateur).
"""

import streamlit as st
import pandas as pd

from components.auth_guard import require_auth
from services.api_client import admin_overview, admin_list_users, admin_recent_orders, check_admin

st.set_page_config(page_title="Admin – InvestX", page_icon="🔐", layout="wide")

token = require_auth()
if not token:
    st.stop()

# Vérifier accès admin
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = check_admin(token)

if not st.session_state.get("is_admin", False):
    st.error("⛔ Accès refusé : vous n'êtes pas administrateur.")
    st.stop()

st.title("🔐 Dashboard Admin")

# ── Vue d'ensemble ──
try:
    overview = admin_overview(token)

    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Utilisateurs total", overview.get("total_users", 0))
    c2.metric("⚙️ DCA v1 actifs", overview.get("dca_v1_active", 0))
    c3.metric("🚀 DCA v2 actifs", overview.get("dca_v2_active", 0))

    st.divider()

    # ── Liste des utilisateurs ──
    st.subheader("👥 Utilisateurs")
    users = admin_list_users(token)
    if users:
        df = pd.DataFrame(users)
        cols = ["email", "display_name", "dca_v1_enabled", "dca_v2_enabled",
                "subscription_plan", "subscription_status"]
        display_cols = [c for c in cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.info("Aucun utilisateur.")

    st.divider()

    # ── Derniers ordres ──
    st.subheader("📋 Derniers ordres (tous utilisateurs)")
    orders = admin_recent_orders(token, limit=50)
    if orders:
        df_orders = pd.DataFrame(orders)
        cols = ["email", "symbol", "quantity", "price", "amount_eur",
                "exchange", "created_at"]
        display_cols = [c for c in cols if c in df_orders.columns]
        st.dataframe(df_orders[display_cols], use_container_width=True)
    else:
        st.info("Aucun ordre récent.")

except Exception as e:
    st.error(f"Erreur : {e}")
