"""
Client d'authentification Firebase pour Streamlit.
Utilise l'API REST Firebase Auth pour le login email/password.
"""

from __future__ import annotations

import requests
import streamlit as st

# À configurer via les secrets Streamlit ou variables d'environnement
FIREBASE_API_KEY = st.secrets.get("FIREBASE_API_KEY", "") if hasattr(st, "secrets") else ""


def sign_in_with_email_password(email: str, password: str) -> dict:
    """Authentifie un utilisateur via Firebase Auth REST API.
    Retourne {idToken, localId (uid), email, refreshToken, ...}
    """
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    response = requests.post(url, json=payload, timeout=10)
    data = response.json()

    if response.status_code != 200:
        error_msg = data.get("error", {}).get("message", "Authentication failed")
        raise Exception(error_msg)

    return data


def sign_up_with_email_password(email: str, password: str) -> dict:
    """Crée un nouveau compte via Firebase Auth REST API."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    response = requests.post(url, json=payload, timeout=10)
    data = response.json()

    if response.status_code != 200:
        error_msg = data.get("error", {}).get("message", "Sign up failed")
        raise Exception(error_msg)

    return data


def send_password_reset_email(email: str) -> None:
    """Envoie un email de réinitialisation de mot de passe via Firebase Auth."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
    payload = {
        "requestType": "PASSWORD_RESET",
        "email": email,
    }
    response = requests.post(url, json=payload, timeout=10)
    data = response.json()
    if response.status_code != 200:
        error_msg = data.get("error", {}).get("message", "Password reset failed")
        raise Exception(error_msg)


def refresh_token(refresh_token_str: str) -> dict:
    """Rafraîchit le token Firebase."""
    url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_str,
    }
    response = requests.post(url, data=payload, timeout=10)
    data = response.json()
    if response.status_code != 200:
        raise Exception("Token refresh failed")
    return data
