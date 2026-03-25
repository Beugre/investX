"""
Page 4 – Intégrations (Binance, Revolut X & Telegram).
"""

import streamlit as st

from components.auth_guard import require_auth
from services.api_client import (
    get_binance_status,
    connect_binance,
    validate_binance,
    disconnect_binance,
    get_revolutx_status,
    connect_revolutx,
    validate_revolutx,
    disconnect_revolutx,
    get_telegram_settings,
    link_telegram,
    test_telegram,
    update_telegram_settings,
)

st.set_page_config(page_title="Integrations – InvestX", page_icon="🔗")
st.title("🔗 Intégrations")

token = require_auth()
if not token:
    st.stop()

# ════════════════════ BINANCE ════════════════════
st.header("🟡 Binance")

try:
    binance_status = get_binance_status(token)
except Exception as e:
    st.error(f"Erreur Binance : {e}")
    binance_status = {}

is_connected = binance_status.get("is_connected", False)

if is_connected:
    st.success("✅ Binance connecté")
    st.write(f"Permissions validées : {'✅' if binance_status.get('permissions_validated') else '❌'}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Re-valider"):
            try:
                result = validate_binance(token)
                if result.get("valid") and result.get("safe"):
                    st.success("✅ Credentials valides")
                else:
                    st.warning(f"⚠️ {result.get('message', 'Issue detected')}")
            except Exception as e:
                st.error(f"Erreur : {e}")

    with col2:
        if st.button("🔌 Déconnecter Binance"):
            try:
                disconnect_binance(token)
                st.success("Binance déconnecté")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")
else:
    st.warning("Binance non connecté.")
    st.markdown("""
    **Instructions :**
    1. Allez sur [Binance API Management](https://www.binance.com/en/my/settings/api-management)
    2. Créez une API key **Trading Only** (sans retrait)
    3. Collez vos clés ci-dessous
    """)

    with st.form("binance_connect_form"):
        api_key = st.text_input("API Key")
        api_secret = st.text_input("API Secret", type="password")
        submitted = st.form_submit_button("🔗 Connecter Binance")

        if submitted:
            if not api_key or not api_secret:
                st.error("Veuillez remplir les deux champs.")
            else:
                try:
                    connect_binance(token, api_key, api_secret)
                    st.success("✅ Binance connecté !")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

st.divider()

# ════════════════════ REVOLUT X ════════════════════
st.header("🔵 Revolut X")

try:
    revolutx_status = get_revolutx_status(token)
except Exception as e:
    st.error(f"Erreur Revolut X : {e}")
    revolutx_status = {}

rx_connected = revolutx_status.get("is_connected", False)

if rx_connected:
    st.success("✅ Revolut X connecté")
    st.write(f"Permissions validées : {'✅' if revolutx_status.get('permissions_validated') else '❌'}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Re-valider", key="rx_validate"):
            try:
                result = validate_revolutx(token)
                if result.get("valid"):
                    st.success("✅ Credentials valides")
                else:
                    st.warning(f"⚠️ {result.get('message', 'Issue detected')}")
            except Exception as e:
                st.error(f"Erreur : {e}")

    with col2:
        if st.button("🔌 Déconnecter Revolut X", key="rx_disconnect"):
            try:
                disconnect_revolutx(token)
                st.success("Revolut X déconnecté")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")
else:
    st.warning("Revolut X non connecté.")
    st.markdown("""
    **Instructions :**
    1. Allez dans votre app Revolut → Hub → Revolut X
    2. Ouvrez **Paramètres API** et créez une clé API
    3. Générez une paire de clés **Ed25519** (la clé publique est enregistrée dans Revolut X)
    4. Collez votre **API Key** et votre **clé privée PEM** ci-dessous
    """)

    with st.form("revolutx_connect_form"):
        rx_api_key = st.text_input("API Key Revolut X")
        rx_private_key = st.text_area(
            "Clé privée Ed25519 (PEM)",
            height=150,
            placeholder="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
        )
        rx_submitted = st.form_submit_button("🔗 Connecter Revolut X")

        if rx_submitted:
            if not rx_api_key or not rx_private_key:
                st.error("Veuillez remplir les deux champs.")
            else:
                try:
                    connect_revolutx(token, rx_api_key, rx_private_key.strip())
                    st.success("✅ Revolut X connecté !")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

# ═══════════════ INFO EXCHANGE ACTIF ════════════════
if is_connected and rx_connected:
    st.divider()
    st.info(
        "💡 **Deux exchanges connectés** — L'exchange actif est celui connecté en dernier. "
        "Déconnectez l'un pour utiliser l'autre pour vos DCA."
    )

st.divider()

# ════════════════════ TELEGRAM ════════════════════
st.header("📱 Telegram")

try:
    tg = get_telegram_settings(token)
except Exception as e:
    st.error(f"Erreur Telegram : {e}")
    tg = {}

tg_linked = bool(tg.get("chat_id"))

if tg_linked:
    st.success(f"✅ Telegram lié (chat_id: {tg.get('chat_id')})")

    # Paramètres de notification
    with st.form("telegram_settings_form"):
        enabled = st.toggle("Notifications activées", value=tg.get("enabled", True))
        notify_orders = st.toggle("Notifier les achats", value=tg.get("notify_orders", True))
        notify_errors = st.toggle("Notifier les erreurs", value=tg.get("notify_errors", True))
        notify_sub = st.toggle("Notifier abonnement", value=tg.get("notify_subscription", True))
        submitted = st.form_submit_button("💾 Sauvegarder")

        if submitted:
            try:
                update_telegram_settings(token, {
                    "enabled": enabled,
                    "notify_orders": notify_orders,
                    "notify_errors": notify_errors,
                    "notify_subscription": notify_sub,
                })
                st.success("✅ Paramètres sauvegardés")
            except Exception as e:
                st.error(f"Erreur : {e}")

    if st.button("🔔 Tester la notification"):
        try:
            result = test_telegram(token)
            if result.get("success"):
                st.success("✅ Message de test envoyé !")
            else:
                st.warning(f"⚠️ {result.get('message', 'Échec')}")
        except Exception as e:
            st.error(f"Erreur : {e}")

else:
    st.warning("Telegram non lié.")
    st.markdown("""
    **Instructions :**
    1. Ouvrez le bot **[@InvestX_The_Bot](https://t.me/InvestX_The_Bot)** sur Telegram
    2. Cliquez sur **Démarrer** ou envoyez `/start`
    3. Le bot vous enverra votre **Chat ID** — copiez-le
    4. Collez-le ci-dessous
    """)

    with st.form("telegram_link_form"):
        chat_id = st.text_input("Chat ID Telegram")
        username = st.text_input("Nom d'utilisateur Telegram (optionnel)")
        submitted = st.form_submit_button("🔗 Lier Telegram")

        if submitted:
            if not chat_id:
                st.error("Veuillez entrer votre chat_id.")
            else:
                try:
                    link_telegram(token, chat_id, username or None)
                    st.success("✅ Telegram lié !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
