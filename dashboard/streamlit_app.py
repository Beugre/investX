"""
InvestX – Dashboard Streamlit (page d'accueil / login).
"""

import streamlit as st
from services.auth_client import sign_in_with_email_password, sign_up_with_email_password
from services.api_client import init_onboarding
from services.session_manager import try_restore_session, save_session, clear_session

st.set_page_config(
    page_title="InvestX – DCA Crypto",
    page_icon="📈",
    layout="wide",
)

st.title("📈 InvestX – DCA Crypto Automatisé")


def _login_form():
    """Formulaire de connexion."""
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

    with tab_signup:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Mot de passe", type="password", key="signup_pwd")
            password2 = st.text_input(
                "Confirmer le mot de passe", type="password", key="signup_pwd2"
            )
            submitted = st.form_submit_button("Créer un compte")

            if submitted:
                if password != password2:
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

                        st.success("✅ Compte créé et connecté !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur : {e}")


def _logged_in_home():
    """Page d'accueil pour utilisateur connecté."""
    st.success(f"Connecté en tant que **{st.session_state.get('email', '')}**")

    st.markdown("""
    ### Bienvenue sur InvestX 👋

    Utilisez le menu latéral pour naviguer :

    - **📊 Dashboard** – Vue d'ensemble de votre portfolio
    - **⚙️ DCA Config** – Configurer votre achat automatique
    - **💳 Subscription** – Gérer votre abonnement
    - **🔗 Integrations** – Binance & Telegram
    - **📜 History** – Historique de vos ordres
    - **🛠 Settings** – Paramètres
    """)

    if st.button("🚪 Se déconnecter"):
        clear_session()
        st.rerun()


# ── Routage ── restauration automatique de session
status = try_restore_session()
if status == "loading":
    st.info("⏳ Chargement de la session...")
    st.stop()
elif status == "restored":
    _logged_in_home()
else:
    _login_form()
