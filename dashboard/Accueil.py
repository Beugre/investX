"""
InvestX – Page d'accueil.

Avant connexion : mini landing page + formulaires login/signup.
Après connexion : accueil personnalisé + barre de progression onboarding.
"""

import streamlit as st
from services.auth_client import (
    sign_in_with_email_password,
    sign_up_with_email_password,
    send_password_reset_email,
    send_email_verification,
)
from services.api_client import (
    init_onboarding,
    get_subscription_status,
    get_binance_status,
    get_telegram_settings,
    get_dca_config,
    get_user_profile,
    update_user_profile,
)
from services.session_manager import try_restore_session, save_session, clear_session

st.set_page_config(
    page_title="Accueil – InvestX",
    page_icon="📈",
    layout="wide",
)


# ══════════════════════════════════════════════════════
# Landing page (visiteur non connecté)
# ══════════════════════════════════════════════════════

def _landing_page():
    """Mini landing page + formulaires login/signup."""

    # ── Hero ──
    st.markdown(
        """
        <div style="text-align:center; padding: 1rem 0 2rem 0;">
            <h1 style="font-size:2.8rem; margin-bottom:0.3rem;">📈 InvestX</h1>
            <p style="font-size:1.3rem; color:#888; margin-top:0;">
                Investissez en crypto automatiquement, sans effort.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 3 blocs valeur ──
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🤖 DCA Automatisé")
        st.markdown(
            "Achetez du Bitcoin & Ethereum chaque jour au meilleur moment. "
            "Le bot s'occupe de tout, 24h/24."
        )
    with col2:
        st.markdown("### 🧠 Stratégie RSI Intelligente")
        st.markdown(
            "Le mode avancé ajuste le montant investi selon le RSI, le MVRV "
            "et le régime de marché. Achetez plus quand c'est bas."
        )
    with col3:
        st.markdown("### 📊 Suivi en Temps Réel")
        st.markdown(
            "Dashboard avec courbes, PnL, historique des achats. "
            "Notifications Telegram à chaque exécution."
        )

    st.divider()

    # ── Disclaimer ──
    st.caption(
        "⚠️ **Avertissement** : L'investissement en cryptomonnaies comporte des risques "
        "de perte en capital. Les performances passées ne garantissent pas les résultats "
        "futurs. InvestX ne fournit pas de conseil en investissement."
    )

    st.divider()

    # ── Comment ça marche ──
    st.markdown("### 🚀 Comment ça marche ?")
    steps = [
        ("1️⃣", "Créez votre compte InvestX"),
        ("2️⃣", "Connectez votre compte Binance via API"),
        ("3️⃣", "Choisissez votre montant quotidien"),
        ("4️⃣", "Le bot achète pour vous chaque jour"),
    ]
    cols = st.columns(4)
    for i, (icon, text) in enumerate(steps):
        with cols[i]:
            st.markdown(f"**{icon}**")
            st.markdown(text)

    st.divider()

    # ── Formulaires connexion ──
    st.subheader("🔐 Connexion")

    tab_login, tab_signup = st.tabs(["Se connecter", "Créer un compte"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter")

            if submitted:
                try:
                    result = sign_in_with_email_password(email, password)
                    save_session(
                        token=result["idToken"],
                        uid=result["localId"],
                        email=email,
                        refresh_token=result.get("refreshToken", ""),
                    )
                    st.success("✅ Connecté !")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

        # ── Mot de passe oublié ──
        with st.expander("🔑 Mot de passe oublié ?"):
            reset_email = st.text_input("Entrez votre email", key="reset_email")
            if st.button("Envoyer le lien de réinitialisation"):
                if not reset_email:
                    st.warning("Veuillez saisir votre email.")
                else:
                    try:
                        send_password_reset_email(reset_email)
                        st.success("📧 Un email de réinitialisation a été envoyé ! Vérifiez votre boîte de réception.")
                    except Exception as e:
                        st.error(f"❌ Erreur : {e}")

    with tab_signup:
        with st.form("signup_form"):
            first_name = st.text_input("Prénom", key="signup_first_name")
            last_name = st.text_input("Nom", key="signup_last_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Mot de passe", type="password", key="signup_pwd")
            password2 = st.text_input(
                "Confirmer le mot de passe", type="password", key="signup_pwd2"
            )
            submitted = st.form_submit_button("Créer un compte")

            if submitted:
                if not first_name or not last_name:
                    st.error("Le prénom et le nom sont obligatoires.")
                elif password != password2:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                else:
                    try:
                        result = sign_up_with_email_password(email, password)
                        save_session(
                            token=result["idToken"],
                            uid=result["localId"],
                            email=email,
                            refresh_token=result.get("refreshToken", ""),
                        )

                        # Initialiser le profil dans Firestore
                        try:
                            init_onboarding(result["idToken"])
                        except Exception:
                            pass

                        # Enregistrer le display_name
                        display_name = f"{first_name} {last_name}".strip()
                        try:
                            update_user_profile(
                                result["idToken"],
                                {"display_name": display_name},
                            )
                        except Exception:
                            pass

                        # Envoyer l'email de vérification
                        try:
                            send_email_verification(result["idToken"])
                        except Exception:
                            pass

                        st.success("✅ Compte créé ! Un email de vérification a été envoyé.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur : {e}")


# ══════════════════════════════════════════════════════
# Page d'accueil connecté
# ══════════════════════════════════════════════════════

def _logged_in_home():
    """Accueil personnalisé avec barre de progression onboarding."""
    token = st.session_state.get("token", "")
    email = st.session_state.get("email", "")

    # Récupérer le display_name depuis le profil
    display_name = ""
    try:
        profile = get_user_profile(token)
        display_name = profile.get("display_name") or ""
    except Exception:
        pass

    greeting = display_name if display_name else email

    st.markdown(
        f"""
        <div style="text-align:center; padding: 0.5rem 0 1rem 0;">
            <h1 style="font-size:2.4rem; margin-bottom:0.2rem;">📈 InvestX</h1>
            <p style="font-size:1.3rem;">Bonjour {greeting} 👋</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Barre de progression onboarding ──
    st.subheader("🏁 Votre progression")

    check_account = True  # connecté = OK

    check_sub = False
    try:
        sub = get_subscription_status(token)
        check_sub = sub.get("status") == "active"
    except Exception:
        pass

    check_binance = False
    try:
        bs = get_binance_status(token)
        check_binance = bs.get("is_connected", False)
    except Exception:
        pass

    check_dca = False
    try:
        dca = get_dca_config(token)
        check_dca = dca.get("enabled", False) if dca else False
    except Exception:
        pass

    check_telegram = False
    try:
        tg = get_telegram_settings(token)
        check_telegram = bool(tg.get("chat_id"))
    except Exception:
        pass

    total_steps = 5
    done = sum([check_account, check_sub, check_binance, check_dca, check_telegram])
    progress = done / total_steps

    st.progress(progress, text=f"{done}/{total_steps} étapes complétées")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        icon = "✅" if check_account else "⬜"
        st.markdown(f"**{icon} Compte**")
        if check_account:
            st.caption("Créé")
        else:
            st.caption("Créer un compte")

    with col2:
        icon = "✅" if check_sub else "⬜"
        st.markdown(f"**{icon} Abonnement**")
        if check_sub:
            st.caption("Actif")
        else:
            st.caption("[→ S'abonner](Subscription)")

    with col3:
        icon = "✅" if check_binance else "⬜"
        st.markdown(f"**{icon} Binance**")
        if check_binance:
            st.caption("Connecté")
        else:
            st.caption("[→ Connecter](Integrations)")

    with col4:
        icon = "✅" if check_dca else "⬜"
        st.markdown(f"**{icon} DCA**")
        if check_dca:
            st.caption("Activé")
        else:
            st.caption("[→ Configurer](DCA_Config)")

    with col5:
        icon = "✅" if check_telegram else "⬜"
        st.markdown(f"**{icon} Telegram**")
        if check_telegram:
            st.caption("Lié")
        else:
            st.caption("[→ Configurer](Integrations)")

    if done == total_steps:
        st.success("🎉 Tout est configuré ! Votre bot DCA est opérationnel.")
    elif done >= 3:
        st.info("💡 Presque terminé ! Consultez le **📖 Guide** dans le menu pour compléter la configuration.")
    else:
        st.warning("👉 Suivez le **📖 Guide** dans le menu latéral pour démarrer pas-à-pas.")

    st.divider()

    # ── Navigation rapide ──
    st.subheader("🧭 Navigation rapide")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.page_link("pages/1_Dashboard.py", label="📊 Dashboard")
        st.page_link("pages/2_DCA_Config.py", label="⚙️ Config DCA")
    with c2:
        st.page_link("pages/3_Subscription.py", label="💳 Abonnement")
        st.page_link("pages/4_Integrations.py", label="🔗 Intégrations")
    with c3:
        st.page_link("pages/5_History.py", label="📜 Historique")
        st.page_link("pages/7_Guide.py", label="📖 Guide démarrage")

    st.divider()

    if st.button("🚪 Se déconnecter"):
        clear_session()
        st.rerun()


# ── CSS : masquer la sidebar quand non connecté ──
_HIDE_SIDEBAR_NAV = """
<style>
    [data-testid="stSidebarNav"] { display: none; }
</style>
"""


# ── Routage ── restauration automatique de session
status = try_restore_session()
if status == "loading":
    st.info("⏳ Chargement de la session...")
    st.stop()
elif status == "restored":
    _logged_in_home()
else:
    st.markdown(_HIDE_SIDEBAR_NAV, unsafe_allow_html=True)
    _landing_page()

# ── Footer global ──
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.85rem;'>"
    "© 2026 InvestX · "
    "<a href='/Mentions_Legales' target='_self' style='color:#888;'>Mentions légales</a> · "
    "<a href='/FAQ' target='_self' style='color:#888;'>FAQ</a>"
    "</div>",
    unsafe_allow_html=True,
)
