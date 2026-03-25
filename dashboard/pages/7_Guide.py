"""
InvestX – Guide de démarrage pas-à-pas.

8 étapes pour configurer complètement votre bot DCA crypto.
"""

import streamlit as st
from components.auth_guard import require_auth

st.set_page_config(page_title="InvestX – Guide", page_icon="📖", layout="wide")

require_auth()

st.title("📖 Guide de démarrage")
st.markdown(
    "Suivez ces **8 étapes** pour configurer votre bot DCA crypto. "
    "Chaque étape est détaillée ci-dessous."
)

st.divider()

# ═══════════════════════════════════════════
# Étape 1 – Créer un compte InvestX
# ═══════════════════════════════════════════
with st.expander("1️⃣  Créer un compte InvestX", expanded=False):
    st.markdown(
        """
**Objectif** : créer votre identifiant sur la plateforme.

1. Sur la **page d'accueil**, cliquez sur l'onglet **Créer un compte**.
2. Renseignez votre **email** et un **mot de passe** (6 caractères min.).
3. Confirmez le mot de passe puis cliquez sur **Créer un compte**.
4. Vous êtes automatiquement connecté ✅

> 💡 Votre mot de passe est stocké de manière sécurisée via Firebase Authentication.
"""
    )

# ═══════════════════════════════════════════
# Étape 2 – S'abonner
# ═══════════════════════════════════════════
with st.expander("2️⃣  S'abonner (activer votre accès)", expanded=False):
    st.markdown(
        """
**Objectif** : activer votre abonnement pour débloquer le bot DCA.

1. Rendez-vous dans **💳 Subscription** via le menu latéral.
2. Cliquez sur **S'abonner** – vous serez redirigé vers la page de paiement Stripe.
3. Renseignez vos informations de paiement.
4. Une fois le paiement validé, votre statut passera à **Actif** ✅

> 💡 Vous pouvez annuler à tout moment depuis la même page.
"""
    )

# ═══════════════════════════════════════════
# Étape 3 – Créer un compte Binance
# ═══════════════════════════════════════════
with st.expander("3️⃣  Créer un compte Binance", expanded=False):
    st.markdown(
        """
**Objectif** : ouvrir un compte sur l'exchange Binance.

1. Rendez-vous sur [binance.com](https://www.binance.com/).
2. Cliquez sur **S'inscrire** et créez votre compte avec email + mot de passe.
3. Complétez la **vérification d'identité** (KYC) :
   - Fournissez une pièce d'identité (carte d'identité ou passeport).
   - Prenez un selfie pour la vérification faciale.
4. Une fois vérifié, votre compte est prêt ✅

> ⚠️ La vérification KYC peut prendre de quelques minutes à 24h selon le volume.
"""
    )

# ═══════════════════════════════════════════
# Étape 4 – Créer une clé API Binance
# ═══════════════════════════════════════════
with st.expander("4️⃣  Créer une clé API Binance", expanded=False):
    st.markdown(
        """
**Objectif** : permettre à InvestX d'acheter de la crypto pour vous, de façon sécurisée.

1. Sur Binance, cliquez sur votre icône de profil → **Gestion des API** (ou allez sur [binance.com/en/my/settings/api-management](https://www.binance.com/en/my/settings/api-management)).
2. Cliquez sur **Créer une API** → choisissez **System generated**.
3. Donnez un label (ex : *InvestX Bot*) et validez par email / 2FA.
4. Vous obtenez une **API Key** et une **Secret Key**.

**⚙️ Configuration des permissions :**
- ✅ **Enable Reading** (lecture) – activé par défaut
- ✅ **Enable Spot & Margin Trading** – **à activer manuellement**
- ❌ **Enable Withdrawals** – **NE PAS activer** (InvestX n'a pas besoin de retirer vos fonds)

**🔒 Restriction IP (obligatoire) :**
- Dans les paramètres de l'API, restreignez l'accès à l'IP du serveur InvestX : `213.199.41.168`
- ⚠️ **Sans cette restriction IP, Binance ne permet pas d'activer le Spot & Margin Trading.**

5. Copiez la **API Key** et la **Secret Key** – vous en aurez besoin à l'étape 6.

> ⚠️ La Secret Key n'est affichée qu'**une seule fois**. Sauvegardez-la dans un endroit sûr.
>
> 🔐 Vos clés sont chiffrées (AES-256) dans notre base de données. Nous ne pouvons ni retirer vos fonds ni accéder à votre solde sans votre autorisation.
"""
    )

# ═══════════════════════════════════════════
# Étape 5 – Recharger en USDC
# ═══════════════════════════════════════════
with st.expander("5️⃣  Recharger votre compte Binance en USDC", expanded=False):
    st.markdown(
        """
**Objectif** : déposer des fonds que le bot utilisera pour acheter de la crypto.

**Option A – Dépôt par carte bancaire / virement :**
1. Sur Binance, allez dans **Acheter des cryptos** → **Dépôt fiat** (EUR).
2. Effectuez un virement bancaire (SEPA) ou payez par carte.
3. Une fois les EUR crédités, convertissez-les en **USDC** :
   - Allez dans **Trade** → **Convert** → EUR → USDC.

**Option B – Transfert crypto :**
1. Si vous avez déjà des USDC sur un autre wallet, envoyez-les vers votre adresse de dépôt Binance.
2. Réseau recommandé : **Solana** (frais faibles) ou **Ethereum**.

> 💡 Le bot InvestX achète en **USDC** (stablecoin 1:1 avec le dollar). Assurez-vous d'avoir un solde USDC suffisant.
>
> Par exemple, si votre DCA quotidien est de 10 $, prévoyez au moins **300 USDC** pour un mois.
"""
    )

# ═══════════════════════════════════════════
# Étape 6 – Connecter Binance à InvestX
# ═══════════════════════════════════════════
with st.expander("6️⃣  Connecter Binance à InvestX", expanded=False):
    st.markdown(
        """
**Objectif** : renseigner vos clés API dans InvestX.

1. Sur InvestX, allez dans **🔗 Intégrations** via le menu latéral.
2. Dans la section **Binance**, entrez :
   - Votre **API Key**
   - Votre **Secret Key**
3. Cliquez sur **Connecter**.
4. Le système vérifie automatiquement vos permissions et affiche **Connecté ✅**.

> 🔐 Vos clés sont chiffrées côté serveur avec AES-256 (Fernet). Personne ne peut les lire en clair.
>
> Si vous voyez une erreur de permissions, retournez sur Binance et vérifiez que **Spot Trading** est bien activé (étape 4).
"""
    )

# ═══════════════════════════════════════════
# Étape 7 – Configurer le DCA
# ═══════════════════════════════════════════
with st.expander("7️⃣  Configurer votre DCA", expanded=False):
    st.markdown(
        """
**Objectif** : définir combien et quand le bot achète.

1. Allez dans **⚙️ DCA Config** via le menu latéral.
2. Configurez les paramètres :
   - **Trading Pair** : la crypto à acheter (ex : `BTCUSDC`, `ETHUSDC`)
   - **Amount** : montant en USDC à investir chaque jour (ex : `10`)
   - **Frequency** : fréquence d'achat (`daily` = une fois par jour)
   - **Execution Time** : heure d'exécution (format UTC, ex : `14:00`)
   - **Enabled** : activez le bot ✅

3. **Mode avancé – DCA RSI v2** (optionnel) :
   - Activez le mode RSI pour que le bot ajuste le montant investi selon les indicateurs de marché.
   - Si le RSI est bas (marché survendu), le bot achète **plus**.
   - Si le RSI est haut (marché suracheté), le bot achète **moins** ou **skip**.

4. Cliquez sur **Sauvegarder**.

> 💡 Vous pouvez utiliser la case **Force Rebuy** pour forcer un achat immédiat (utile si vous avez changé l'heure d'exécution).
"""
    )

# ═══════════════════════════════════════════
# Étape 8 – Configurer Telegram (optionnel)
# ═══════════════════════════════════════════
with st.expander("8️⃣  Configurer les notifications Telegram (optionnel)", expanded=False):
    st.markdown(
        """
**Objectif** : recevoir une notification Telegram à chaque achat du bot.

1. Ouvrez Telegram et recherchez le bot **@InvestX_The_Bot**.
2. Cliquez sur **Démarrer** (ou envoyez `/start`).
3. Envoyez la commande `/id` – le bot vous répond avec votre **Chat ID** (un nombre).
4. Copiez ce Chat ID.
5. Sur InvestX, allez dans **🔗 Intégrations** → section **Telegram**.
6. Collez votre **Chat ID** et cliquez sur **Enregistrer**.
7. Cliquez sur **Envoyer un message test** pour vérifier ✅

> 💡 Les notifications incluent : paire achetée, montant, prix, PnL actuel.
>
> Vous pouvez désactiver les notifications à tout moment en vidant le Chat ID.
"""
    )

st.divider()

st.info(
    "💬 Besoin d'aide ? Contactez le support via Telegram : **@InvestX_The_Bot** "
    "ou envoyez un email."
)
