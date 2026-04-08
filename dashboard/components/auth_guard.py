"""
Auth guard – vérifie que l'utilisateur est connecté dans Streamlit.
"""

from __future__ import annotations

import streamlit as st

_HIDE_ADMIN_NAV = """
<style>
    [data-testid="stSidebarNav"] li:last-child { display: none !important; }
</style>
"""


def _inject_admin_visibility():
    """Cache le lien Admin dans la sidebar si l'utilisateur n'est pas admin."""
    # Vérifier le statut admin si pas encore fait
    if "is_admin" not in st.session_state:
        token = st.session_state.get("token", "")
        if token:
            from services.api_client import check_admin
            st.session_state["is_admin"] = check_admin(token)
        else:
            st.session_state["is_admin"] = False

    if not st.session_state["is_admin"]:
        st.markdown(_HIDE_ADMIN_NAV, unsafe_allow_html=True)


def require_auth() -> str | None:
    """Vérifie que l'utilisateur est authentifié.
    Restaure automatiquement la session depuis localStorage si nécessaire.
    Retourne le token si OK, sinon affiche un message et arrête.
    """
    from services.session_manager import try_restore_session

    status = try_restore_session()
    if status == "loading":
        retries = st.session_state.get("_auth_retries", 0) + 1
        st.session_state["_auth_retries"] = retries
        if retries > 2:
            st.warning("🔒 Veuillez vous connecter pour accéder à cette page.")
            st.stop()
            return None
        st.info("⏳ Chargement de la session...")
        st.stop()
        return None

    st.session_state.pop("_auth_retries", None)

    if "user" not in st.session_state or not st.session_state.get("token"):
        st.warning("🔒 Veuillez vous connecter pour accéder à cette page.")
        st.stop()
        return None

    _inject_admin_visibility()
    return st.session_state["token"]


def get_token() -> str:
    """Retourne le token de l'utilisateur connecté."""
    return st.session_state.get("token", "")


def get_uid() -> str:
    """Retourne le uid de l'utilisateur connecté."""
    return st.session_state.get("uid", "")


def get_email() -> str:
    """Retourne l'email de l'utilisateur connecté."""
    return st.session_state.get("email", "")
