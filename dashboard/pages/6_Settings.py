"""
Page 6 – Paramètres généraux.
"""

import streamlit as st

from components.auth_guard import require_auth, get_email, get_uid
from components.constants import ALERT_SYMBOLS, COMMON_TIMEZONES
from services.api_client import get_user_profile, update_user_profile, list_alerts, create_alert, delete_alert

st.set_page_config(page_title="Settings – InvestX", page_icon="🛠")
st.title("🛠 Paramètres")

token = require_auth()
if not token:
    st.stop()

# ── Profil ──
st.subheader("👤 Profil")

current_profile = {}
try:
    current_profile = get_user_profile(token)
except Exception:
    pass

current_name = current_profile.get("display_name") or ""

with st.form("profile_form"):
    display_name = st.text_input("Nom complet", value=current_name)
    save_profile = st.form_submit_button("💾 Enregistrer")

    if save_profile:
        if not display_name.strip():
            st.error("Le nom ne peut pas être vide.")
        else:
            try:
                update_user_profile(token, {"display_name": display_name.strip()})
                st.success("✅ Nom mis à jour !")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")

st.divider()

st.subheader("Informations du compte")
st.write(f"**Email :** {get_email()}")
st.write(f"**UID :** {get_uid()}")

st.divider()

st.subheader("Timezone")
current_tz = current_profile.get("timezone", "Europe/Paris")
selected_tz = st.selectbox("Timezone", COMMON_TIMEZONES, index=COMMON_TIMEZONES.index(current_tz) if current_tz in COMMON_TIMEZONES else 0)
if selected_tz != current_tz:
    if st.button("💾 Enregistrer la timezone"):
        try:
            update_user_profile(token, {"timezone": selected_tz})
            st.success(f"✅ Timezone mise à jour : {selected_tz}")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

st.divider()

st.subheader("🔔 Alertes de prix")
st.caption("Recevez une notification Telegram quand un prix est atteint.")

with st.form("alert_form"):
    col_s, col_p, col_d = st.columns([2, 2, 1])
    with col_s:
        alert_symbol = st.selectbox("Paire", ALERT_SYMBOLS, key="alert_sym")
    with col_p:
        alert_price = st.number_input("Prix cible", min_value=0.01, step=10.0, key="alert_px")
    with col_d:
        alert_dir = st.selectbox("Direction", ["above", "below"], format_func=lambda x: "📈 Au-dessus" if x == "above" else "📉 En-dessous", key="alert_dir")
    if st.form_submit_button("➕ Créer l'alerte"):
        try:
            create_alert(token, alert_symbol, alert_price, alert_dir)
            st.success("✅ Alerte créée !")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

try:
    alerts = list_alerts(token)
    if alerts:
        for a in alerts:
            icon = "📈" if a.get("direction") == "above" else "📉"
            status = "✅ Déclenchée" if a.get("triggered") else "⏳ Active"
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{icon} **{a.get('symbol')}** — {a.get('target_price', 0):,.2f} ({status})")
            with col2:
                if not a.get("triggered") and st.button("🗑️", key=f"del_{a.get('id')}"):
                    try:
                        delete_alert(token, a["id"])
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
    else:
        st.info("Aucune alerte configurée.")
except Exception as e:
    st.warning(f"Impossible de charger les alertes : {e}")

st.divider()

st.subheader("Déconnexion")
if st.button("🚪 Se déconnecter", type="primary"):
    from services.session_manager import clear_session
    clear_session()
    st.rerun()
