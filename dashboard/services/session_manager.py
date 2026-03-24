"""
Session manager – persiste la session Firebase via localStorage du navigateur.
Permet de rester connecté même après un rechargement de page.
"""

from __future__ import annotations

import json
import streamlit as st
from streamlit_js_eval import streamlit_js_eval


def _persist_to_local_storage():
    """Écrit le refresh_token + email dans localStorage.

    Appelée à chaque render quand l'utilisateur est connecté,
    ce qui garantit que localStorage est toujours à jour
    (contrairement à un appel unique au login suivi d'un st.rerun()).
    """
    rt = st.session_state.get("refresh_token", "")
    email = st.session_state.get("email", "")
    if rt:
        streamlit_js_eval(
            js_expressions=(
                f'(function(){{'
                f'localStorage.setItem("investx_rt",{json.dumps(rt)});'
                f'localStorage.setItem("investx_email",{json.dumps(email)});'
                f'return "saved";}})() '
            ),
            key="_persist_ls",
        )


def try_restore_session() -> str:
    """Tente de restaurer la session depuis localStorage.

    Returns
    -------
    "restored" – session active (session_state ou restaurée depuis localStorage)
    "loading"  – composant JS pas encore prêt (premier render)
    "no_token" – aucun refresh token stocké
    """
    # Déjà connecté dans cette session Streamlit
    if "user" in st.session_state and st.session_state.get("token"):
        # Persister dans localStorage à chaque render
        _persist_to_local_storage()
        return "restored"

    # Essayer de lire depuis localStorage
    raw = streamlit_js_eval(
        js_expressions=(
            'JSON.stringify({'
            'rt:localStorage.getItem("investx_rt"),'
            'email:localStorage.getItem("investx_email")'
            '})'
        ),
        key="_restore_ls",
    )

    # Valeur par défaut du composant avant que le JS s'exécute
    if raw is None or raw == 0:
        return "loading"

    if not raw:
        return "no_token"

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return "no_token"

    rt = data.get("rt")
    if not rt:
        return "no_token"

    # Échanger le refresh token contre un nouveau id_token
    try:
        from services.auth_client import refresh_token as _refresh

        result = _refresh(rt)
        st.session_state.update(
            {
                "token": result["id_token"],
                "uid": result["user_id"],
                "refresh_token": result["refresh_token"],
                "email": data.get("email") or "",
                "user": True,
            }
        )
        return "restored"
    except Exception:
        _clear_local_storage()
        return "no_token"


def save_session(token: str, uid: str, email: str, refresh_token: str):
    """Sauvegarde la session dans session_state.

    La persistance dans localStorage est faite automatiquement
    par _persist_to_local_storage() au prochain render.
    """
    st.session_state.update(
        {
            "token": token,
            "uid": uid,
            "email": email,
            "refresh_token": refresh_token,
            "user": True,
        }
    )


def clear_session():
    """Efface la session (session_state + localStorage)."""
    for key in ["user", "token", "uid", "email", "refresh_token"]:
        st.session_state.pop(key, None)
    _clear_local_storage()


def _clear_local_storage():
    streamlit_js_eval(
        js_expressions=(
            '(function(){'
            'localStorage.removeItem("investx_rt");'
            'localStorage.removeItem("investx_email");'
            'return "cleared";})()'
        ),
        key="_clear_ls",
    )
