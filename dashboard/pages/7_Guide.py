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
    "Suivez ces étapes pour configurer votre bot DCA crypto. "
    "InvestX supporte **Binance** et **Revolut X** — choisissez l'exchange qui vous convient."
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
with st.expander("3️⃣  Créer un compte sur votre exchange", expanded=False):
    tab_binance, tab_revolut = st.tabs(["🟡 Binance", "🔵 Revolut X"])

    with tab_binance:
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

    with tab_revolut:
        st.markdown(
            """
**Objectif** : activer Revolut X pour trader des cryptos.

1. Si vous n'avez pas encore Revolut, téléchargez l'app sur [revolut.com](https://www.revolut.com/) et créez un compte.
2. **Téléchargez l'app Revolut X** :
   - 📱 [App Store (iOS)](https://apps.apple.com/app/revolut-x/id6504628674)
   - 📱 [Google Play (Android)](https://play.google.com/store/apps/details?id=com.revolut.exchange)
   - 💻 Ou accédez à [x.revolut.com](https://x.revolut.com) depuis un navigateur
3. Connectez-vous avec votre compte Revolut existant.
4. Votre compte est prêt ✅

> 💡 Revolut X est l'application de trading dédiée de Revolut. Elle est **séparée** de l'app Revolut principale.
> Si vous avez déjà un compte Revolut vérifié, l'activation est immédiate.
"""
        )

# ═══════════════════════════════════════════
# Étape 4 – Créer une clé API Binance
# ═══════════════════════════════════════════
with st.expander("4️⃣  Créer une clé API", expanded=False):
    tab_binance4, tab_revolut4 = st.tabs(["🟡 Binance", "🔵 Revolut X"])

    with tab_binance4:
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

    with tab_revolut4:
        st.markdown(
            """
**Objectif** : permettre à InvestX d'acheter de la crypto pour vous via Revolut X.

**C'est super simple, InvestX fait le plus dur pour vous !**

1. Sur InvestX, allez dans **🔗 Intégrations** → section **Revolut X**.
2. Cliquez sur **🔑 Générer mes clés Ed25519** — InvestX génère automatiquement vos clés de sécurité.
3. **Copiez la clé publique** affichée.
4. Allez dans **Revolut X** → **Paramètres API** → **+ Ajouter**.
5. Donnez un nom (ex: `InvestX`), **collez la clé publique**.
6. Cochez **"Voir mes ordres spot"** et **"Ordre spot"**.
7. Cliquez **Enregistrer** dans Revolut X.
8. Copiez la **Clé API** affichée par Revolut X (ex: `Syjv***590d`).
9. Retournez sur InvestX et collez cette Clé API dans le formulaire → **Connecter**.

> 💡 Pas besoin de générer de clés vous-même — InvestX s'occupe de tout !
>
> 🔐 Vos clés sont chiffrées (AES-256) côté serveur. Revolut X ne permet pas les retraits via API — vos fonds sont en sécurité.
"""
        )

# ═══════════════════════════════════════════
# Étape 5 – Recharger en USDC
# ═══════════════════════════════════════════
with st.expander("5️⃣  Recharger votre compte en fonds", expanded=False):
    tab_binance5, tab_revolut5 = st.tabs(["🟡 Binance (USDC)", "🔵 Revolut X (EUR / USDC)"])

    with tab_binance5:
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

    with tab_revolut5:
        st.markdown(
            """
**Objectif** : avoir des fonds disponibles sur votre compte **Revolut X**.

⚠️ **Important** : Revolut X utilise un portefeuille séparé de votre compte Revolut principal. Il faut transférer des fonds vers ce portefeuille.

**Option A – DCA en EUR :**
1. Ouvrez l'app **Revolut**.
2. Allez dans **Cryptos** → **Compte Cryptos · EUR**.
3. Appuyez sur **Ajouter** ou **Transférer**.
4. Sélectionnez votre **compte EUR principal** comme source.
5. Entrez le montant à transférer (ex : 300 €) et confirmez.

**Option B – DCA en USDC :**
1. Transférez de l'USDC vers votre compte Revolut X.
2. Vous pouvez acheter de l'USDC directement dans l'app Revolut, ou en recevoir depuis un wallet externe.
3. Les paires disponibles en USDC : `BTC-USDC`, `ETH-USDC`, `SOL-USDC`.

> ✅ Les transferts internes Revolut sont **instantanés et gratuits**.
>
> 💡 Le bot InvestX achète depuis votre solde Revolut X (EUR ou USDC selon la paire choisie). Assurez-vous que ce solde est suffisant.
>
> Par exemple, si votre DCA quotidien est de 10 €, prévoyez au moins **300 €** (ou 300 USDC) pour un mois.
>
> ⚠️ Avoir des fonds sur votre compte Revolut principal **ne suffit pas** — il faut les transférer vers Revolut X.
"""
        )

# ═══════════════════════════════════════════
# Étape 6 – Connecter Binance à InvestX
# ═══════════════════════════════════════════
with st.expander("6️⃣  Connecter votre exchange à InvestX", expanded=False):
    tab_binance6, tab_revolut6 = st.tabs(["🟡 Binance", "🔵 Revolut X"])

    with tab_binance6:
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

    with tab_revolut6:
        st.markdown(
            """
**Objectif** : connecter Revolut X à InvestX.

Si vous avez suivi l'étape 4 (onglet Revolut X), vos clés sont déjà générées et configurées ! Sinon :

1. Sur InvestX, allez dans **🔗 Intégrations** → section **Revolut X**.
2. Cliquez **🔑 Générer mes clés Ed25519**.
3. Copiez la clé publique et enregistrez-la dans Revolut X.
4. Copiez l'API Key de Revolut X et collez-la dans le formulaire InvestX.
5. Cliquez **Connecter** → **Connecté ✅**.

> 💡 Si vous connectez les deux exchanges, vous pouvez choisir lequel utiliser via le sélecteur **"Exchange actif"** en bas de la page Intégrations.
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
   - **Trading Pair** : la crypto à acheter
     - *Binance* : `BTCUSDC`, `ETHUSDC`, `SOLUSDC`, `BNBUSDC`, `ADAUSDC`
     - *Revolut X (EUR)* : `BTC-EUR`, `ETH-EUR`, `SOL-EUR`, `BNB-EUR`, `ADA-EUR`
     - *Revolut X (USDC)* : `BTC-USDC`, `ETH-USDC`, `SOL-USDC`
   - **Amount** : montant à investir chaque jour (ex : `10` en USDC pour Binance, `10` en EUR ou USDC pour Revolut X)
   - **Frequency** : fréquence d'achat (`daily` = une fois par jour)
   - **Execution Time** : heure d'exécution (format UTC, ex : `14:00`)
   - **Enabled** : activez le bot ✅

3. **Mode avancé – DCA RSI v2** (optionnel) :
   - Activez le mode RSI pour que le bot ajuste le montant investi selon les indicateurs de marché.
   - Si le RSI est bas (marché survendu), le bot achète **plus**.
   - Si le RSI est haut (marché suracheté), le bot achète **moins** ou **skip**.

4. Cliquez sur **Sauvegarder**.

> 💡 Vous pouvez utiliser la case **Force Rebuy** pour forcer un achat immédiat (utile si vous avez changé l'heure d'exécution).
>
> ⚙️ Si vous changez d'exchange, pensez à mettre à jour votre **Trading Pair** (les formats sont différents entre Binance et Revolut X).
"""
    )

# ═══════════════════════════════════════════
# Étape 8 – Configurer Telegram (optionnel)
# ═══════════════════════════════════════════
with st.expander("8️⃣  Configurer les notifications Telegram (optionnel)", expanded=False):
    st.markdown(
        """
**Objectif** : recevoir une notification Telegram à chaque achat du bot.

1. Sur InvestX, allez dans **🔗 Intégrations** → section **Telegram**.
2. Cliquez sur le bouton pour **ouvrir le bot Telegram InvestX**.
3. Telegram lance automatiquement le bot avec votre **code sécurisé de liaison**.
4. Le bot confirme que votre compte est bien connecté à InvestX ✅
5. Revenez sur InvestX puis cliquez sur **J'ai envoyé le code au bot**.
6. Activez les notifications que vous souhaitez recevoir.
7. Cliquez sur **Tester la notification** pour vérifier que tout fonctionne ✅

> 💡 Les notifications incluent : paire achetée, montant, prix, PnL actuel.
>
> 💡 Ce nouveau système évite les erreurs de saisie et relie automatiquement le bon compte Telegram au bon compte InvestX.
>
> Vous pouvez désactiver les notifications à tout moment depuis la section Telegram.
"""
    )

st.divider()

st.info(
    "💬 Besoin d'aide ? Contactez le support via Telegram : **@InvestX_The_Bot** "
    "ou envoyez un email."
)
