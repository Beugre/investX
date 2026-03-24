"""
Page 6 – Paramètres généraux.
"""

import streamlit as st

from components.auth_guard import require_auth, get_email, get_uid

st.set_page_config(page_title="Settings – InvestX", page_icon="🛠")
st.title("🛠 Paramètres")

token = require_auth()
if not token:
    st.stop()

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
