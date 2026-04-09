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
    generate_revolutx_keys,
    connect_revolutx,
    validate_revolutx,
    disconnect_revolutx,
    get_active_exchange,
    set_active_exchange,
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
            st.session_state["confirm_disconnect_binance"] = True

    if st.session_state.get("confirm_disconnect_binance"):
        st.warning("⚠️ Êtes-vous sûr de vouloir déconnecter Binance ? Vos clés API seront supprimées.")
        c1, c2, _ = st.columns([1, 1, 3])
        with c1:
            if st.button("✅ Confirmer", key="confirm_disconnect_bn"):
                try:
                    disconnect_binance(token)
                    st.session_state.pop("confirm_disconnect_binance", None)
                    st.success("Binance déconnecté")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        with c2:
            if st.button("❌ Annuler", key="cancel_disconnect_bn"):
                st.session_state.pop("confirm_disconnect_binance", None)
                st.rerun()
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
            st.session_state["confirm_disconnect_rx"] = True

    if st.session_state.get("confirm_disconnect_rx"):
        st.warning("⚠️ Êtes-vous sûr de vouloir déconnecter Revolut X ? Vos clés seront supprimées.")
        c1, c2, _ = st.columns([1, 1, 3])
        with c1:
            if st.button("✅ Confirmer", key="confirm_disconnect_rx"):
                try:
                    disconnect_revolutx(token)
                    st.session_state.pop("confirm_disconnect_rx", None)
                    st.success("Revolut X déconnecté")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        with c2:
            if st.button("❌ Annuler", key="cancel_disconnect_rx"):
                st.session_state.pop("confirm_disconnect_rx", None)
                st.rerun()
else:
    st.warning("Revolut X non connecté.")

    # ── Étape 1 : Générer les clés Ed25519 ──
    st.markdown("### Étape 1 — Générer vos clés de sécurité")
    st.markdown(
        "Revolut X utilise des clés **Ed25519** pour sécuriser l'accès API. "
        "Cliquez ci-dessous pour générer automatiquement votre paire de clés."
    )

    if st.button("🔑 Générer mes clés Ed25519", key="rx_gen_keys"):
        try:
            keys = generate_revolutx_keys(token)
            st.session_state["rx_public_key"] = keys["public_key_pem"]
            st.session_state["rx_private_key"] = keys["private_key_pem"]
        except Exception as e:
            st.error(f"Erreur lors de la génération : {e}")

    if st.session_state.get("rx_public_key"):
        st.success("✅ Clés générées !")

        st.markdown("### Étape 2 — Copiez la clé publique dans Revolut X")
        st.markdown(
            "1. Allez dans **Revolut X** → **Paramètres API** → **+ Ajouter**\n"
            "2. Donnez un nom (ex: `InvestX`)\n"
            "3. **Copiez la clé publique ci-dessous** et collez-la dans le champ \"Clé publique\"\n"
            "4. Cochez **Ordre spot** (et \"Voir mes ordres spot\")\n"
            "5. Cliquez **Enregistrer**"
        )
        st.code(st.session_state["rx_public_key"], language=None)

        st.markdown("### Étape 3 — Entrez l'API Key de Revolut X")
        st.markdown(
            "Après avoir enregistré dans Revolut X, copiez la **Clé API** affichée "
            "(ex: `Syjv***590d`) et collez-la ci-dessous."
        )

        with st.form("revolutx_connect_form"):
            rx_api_key = st.text_input("API Key Revolut X")
            st.text_area(
                "Clé privée Ed25519 (auto-générée ✅)",
                value=st.session_state["rx_private_key"],
                height=100,
                disabled=True,
            )
            rx_submitted = st.form_submit_button("🔗 Connecter Revolut X")

            if rx_submitted:
                if not rx_api_key:
                    st.error("Veuillez entrer l'API Key de Revolut X.")
                else:
                    try:
                        connect_revolutx(
                            token, rx_api_key,
                            st.session_state["rx_private_key"].strip(),
                        )
                        # Nettoyage session
                        st.session_state.pop("rx_public_key", None)
                        st.session_state.pop("rx_private_key", None)
                        st.success("✅ Revolut X connecté !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur : {e}")
    else:
        st.info(
            "💡 Vous pouvez aussi coller manuellement votre clé privée "
            "si vous l'avez déjà générée vous-même."
        )
        with st.expander("🔧 Connexion manuelle (utilisateurs avancés)"):
            with st.form("revolutx_manual_form"):
                rx_api_key_m = st.text_input("API Key Revolut X", key="rx_api_m")
                rx_private_key_m = st.text_area(
                    "Clé privée Ed25519 (PEM)",
                    height=150,
                    placeholder="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
                    key="rx_pk_m",
                )
                rx_submitted_m = st.form_submit_button("🔗 Connecter")

                if rx_submitted_m:
                    if not rx_api_key_m or not rx_private_key_m:
                        st.error("Veuillez remplir les deux champs.")
                    else:
                        try:
                            connect_revolutx(token, rx_api_key_m, rx_private_key_m.strip())
                            st.success("✅ Revolut X connecté !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erreur : {e}")

# ═══════════════ EXCHANGE ACTIF ════════════════
if is_connected and rx_connected:
    st.divider()
    st.header("⚙️ Exchange actif")
    st.markdown(
        "Vous avez **deux exchanges connectés**. "
        "Choisissez lequel utiliser pour vos achats DCA :"
    )

    try:
        current_exchange = get_active_exchange(token)
    except Exception:
        current_exchange = "binance"

    exchange_options = {
        "binance": "🟡 Binance (USDC)",
        "revolutx": "🔵 Revolut X (EUR)",
    }
    current_index = 0 if current_exchange == "binance" else 1

    selected = st.radio(
        "Exchange pour les achats DCA",
        options=list(exchange_options.keys()),
        format_func=lambda x: exchange_options[x],
        index=current_index,
        horizontal=True,
        key="exchange_selector",
    )

    if selected != current_exchange:
        try:
            set_active_exchange(token, selected)
            st.success(f"✅ Exchange actif : **{exchange_options[selected]}**")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
    else:
        st.info(f"🟢 Exchange actif : **{exchange_options[current_exchange]}**")
elif is_connected:
    st.divider()
    st.info(f"🟢 Exchange actif : **🟡 Binance (USDC)**")
elif rx_connected:
    st.divider()
    st.info("🟢 Exchange actif : **🔵 Revolut X (EUR)**")

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
