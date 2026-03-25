"""
Page 6 – Paramètres généraux.
"""

import streamlit as st

from components.auth_guard import require_auth, get_email, get_uid
from services.api_client import get_user_profile, update_user_profile

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
st.info("Timezone par défaut : **Europe/Paris**")
st.caption("La modification de timezone sera disponible dans une prochaine version.")

st.divider()

st.subheader("Déconnexion")
if st.button("🚪 Se déconnecter", type="primary"):
    from services.session_manager import clear_session
    clear_session()
    st.rerun()
