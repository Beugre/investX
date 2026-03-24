"""
Page 3 – Gestion de l'abonnement.
"""

import streamlit as st
from streamlit.components.v1 import html as st_html

from components.auth_guard import require_auth
from services.api_client import (
    get_subscription_status,
    create_checkout_session,
    create_customer_portal,
    sync_subscription,
)

st.set_page_config(page_title="Subscription – InvestX", page_icon="💳")
st.title("💳 Abonnement")

token = require_auth()
if not token:
    st.stop()

# ── Détecter le retour de Stripe Checkout ──
try:
    params = st.query_params
    is_success = params.get("success") == "true"
    is_canceled = params.get("canceled") == "true"
except Exception:
    is_success = False
    is_canceled = False

if is_success:
    with st.spinner("🔄 Synchronisation de votre abonnement..."):
        try:
            sync_subscription(token)
        except Exception:
            pass
    st.success("✅ Paiement effectué avec succès ! Votre abonnement est maintenant actif.")
    try:
        st.query_params.clear()
    except Exception:
        pass

if is_canceled:
    st.warning("❌ Le paiement a été annulé.")
    try:
        st.query_params.clear()
    except Exception:
        pass

# ── Charger le statut ──
try:
    sub = get_subscription_status(token)
except Exception as e:
    st.error(f"Erreur : {e}")
    st.stop()

status = sub.get("status", "none")

# ── Affichage statut ──
st.subheader("Statut actuel")

if status == "active":
    st.success("✅ Abonnement actif")
    period_end = sub.get("current_period_end")
    if period_end:
        st.info(f"Renouvellement : {period_end}")
    if sub.get("cancel_at_period_end"):
        st.warning("⚠️ L'abonnement sera annulé à la fin de la période.")
elif status == "none":
    st.warning("Vous n'avez pas encore d'abonnement.")
else:
    st.error(f"Statut : {status}")

st.divider()

# ── Actions ──
col1, col2 = st.columns(2)

with col1:
    if status == "none" or status in ("canceled", "incomplete"):
        if st.button("🛒 S'abonner", type="primary", use_container_width=True):
            try:
                result = create_checkout_session(token)
                checkout_url = result.get("checkout_url", "")
                if checkout_url:
                    # Ouvrir automatiquement dans un nouvel onglet
                    st_html(
                        f'<script>window.open("{checkout_url}", "_blank");</script>',
                        height=0,
                    )
                    # Bouton de fallback bien visible
                    st.markdown(
                        f"""
                        <div style="text-align: center; margin: 24px 0;">
                            <a href="{checkout_url}" target="_blank"
                               style="display: inline-block;
                                      background: linear-gradient(135deg, #FF4B4B 0%, #FF6B35 100%);
                                      color: white;
                                      padding: 16px 40px;
                                      border-radius: 12px;
                                      text-decoration: none;
                                      font-size: 20px;
                                      font-weight: bold;
                                      box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);">
                                💳 Procéder au paiement
                            </a>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.info(
                        "💡 Une fenêtre de paiement Stripe devrait s'ouvrir. "
                        "Si elle a été bloquée par votre navigateur, "
                        "cliquez sur le bouton ci-dessus."
                    )
                else:
                    st.error("Impossible de créer la session de paiement.")
            except Exception as e:
                st.error(f"Erreur : {e}")

with col2:
    if status in ("active", "past_due"):
        if st.button("🔧 Gérer mon abonnement", use_container_width=True):
            try:
                result = create_customer_portal(token)
                portal_url = result.get("portal_url", "")
                if portal_url:
                    st_html(
                        f'<script>window.open("{portal_url}", "_blank");</script>',
                        height=0,
                    )
                    st.markdown(
                        f"""
                        <div style="text-align: center; margin: 24px 0;">
                            <a href="{portal_url}" target="_blank"
                               style="display: inline-block;
                                      background: linear-gradient(135deg, #4B8BFF 0%, #357BFF 100%);
                                      color: white;
                                      padding: 16px 40px;
                                      border-radius: 12px;
                                      text-decoration: none;
                                      font-size: 20px;
                                      font-weight: bold;
                                      box-shadow: 0 4px 15px rgba(75, 139, 255, 0.4);">
                                🔧 Portail Stripe
                            </a>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.error("Impossible d'ouvrir le portail.")
            except Exception as e:
                st.error(f"Erreur : {e}")

# ── Sync manuel ──
st.divider()
st.caption("Problème d'affichage ? Synchronisez votre abonnement.")
if st.button("🔄 Synchroniser", use_container_width=False):
    with st.spinner("Synchronisation..."):
        try:
            sync_subscription(token)
            st.success("Synchronisation terminée !")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
