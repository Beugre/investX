"""
Page 8 – Foire Aux Questions.
"""

import streamlit as st
from components.auth_guard import require_auth

st.set_page_config(page_title="FAQ – InvestX", page_icon="❓", layout="wide")

require_auth()

st.title("❓ Foire Aux Questions")

st.divider()

# ── Général ──
st.subheader("📌 Général")

with st.expander("C'est quoi le DCA ?"):
    st.markdown(
        """
Le **DCA** (Dollar-Cost Averaging) est une stratégie d'investissement qui consiste
à acheter un montant fixe d'un actif à intervalles réguliers (ex : 10 $ de Bitcoin
chaque jour), quel que soit le prix.

**Avantages :**
- Réduit l'impact de la volatilité
- Pas besoin de « timer le marché »
- Discipline automatisée
- Réduit le stress émotionnel

C'est la stratégie la plus simple et la plus éprouvée pour investir en crypto sur
le long terme.
"""
    )

with st.expander("Quelles devises sont supportées sur chaque exchange ?"):
    st.markdown(
        """
InvestX supporte deux exchanges avec plusieurs devises :

**🟡 Binance – USDC** :
- **Liquidité** : Les paires USDC sur Binance ont la meilleure liquidité
- **Frais réduits** : Moins de spread et de slippage
- Vous convertissez vos EUR en USDC avant de commencer le DCA

**🔵 Revolut X – EUR ou USDC** :
- **EUR** : Achetez directement en euros, 0% de frais maker, transfert instantané depuis Revolut
- **USDC** : Paires disponibles : `BTC-USDC`, `ETH-USDC`, `SOL-USDC`
- Vous choisissez la devise (EUR ou USDC) lors de la configuration du DCA
"""
    )

with st.expander("Combien dois-je investir ?"):
    st.markdown(
        """
Il n'y a **pas de montant minimum** imposé par InvestX.
- **Binance** : minimum d'environ **5 USDC** par ordre.
- **Revolut X** : minimum d'environ **1 EUR** (ou **1 USDC**) par ordre.

**Recommandations :**
- Investissez uniquement de l'argent que vous pouvez vous permettre de perdre
- Commencez petit (5-20 €/jour) et augmentez progressivement
- Prévoyez un solde suffisant pour au moins 1 mois

Exemple : Si votre DCA quotidien est de 10 €, gardez au minimum **300 €/USDC** sur
votre compte exchange.
"""
    )

st.divider()

# ── Sécurité ──
st.subheader("🔐 Sécurité")

with st.expander("Mes fonds sont-ils en sécurité ?"):
    st.markdown(
        """
**Oui.** Voici comment nous protégeons vos fonds :

1. **Vos cryptos restent sur votre exchange** (Binance ou Revolut X) – InvestX n'a
   jamais accès à vos fonds directement.

2. **Clés API limitées** :
   - *Binance* : seul le Spot Trading est activé, les retraits sont **désactivés**.
   - *Revolut X* : seuls les ordres spot sont autorisés, les retraits via API sont **impossibles**.

3. **Restriction IP** (Binance) – Votre clé API est restreinte à l'IP du serveur InvestX.

4. **Chiffrement AES-256** – Vos clés API sont chiffrées dans notre base de données
   avec l'algorithme Fernet (AES-256). Elles ne sont jamais lisibles en clair.

5. **Pas de garde** – InvestX n'est pas un exchange, ni un wallet. Nous ne
   détenons jamais vos cryptomonnaies.
"""
    )

with st.expander("Que se passe-t-il si InvestX ferme ?"):
    st.markdown(
        """
**Rien ne change pour vos cryptos.** Elles restent sur votre exchange (Binance ou Revolut X).

- Supprimez simplement la clé API InvestX depuis votre exchange
- Vos achats DCA s'arrêteront automatiquement
- Vos cryptos restent disponibles sur votre compte
"""
    )

with st.expander("InvestX peut-il retirer mes fonds ?"):
    st.markdown(
        """
**Non, impossible.**

**🟡 Binance** : Lors de la configuration de la clé API :
- ❌ Le retrait (**Enable Withdrawals**) n'est **pas activé**
- ✅ Seul le trading Spot est autorisé
- 🔒 L'IP est restreinte au serveur InvestX

**🔵 Revolut X** : L'API Revolut X ne permet **aucun retrait** — seuls les ordres spot sont possibles.

Même en cas de compromission de nos serveurs, vos fonds sont protégés.
"""
    )

st.divider()

# ── Stratégie ──
st.subheader("🧠 Stratégie RSI v2")

with st.expander("C'est quoi la stratégie RSI ?"):
    st.markdown(
        """
La **stratégie RSI v2** est le mode avancé d'InvestX. Au lieu d'acheter un montant
fixe chaque jour, le bot **ajuste le montant** selon les conditions de marché :

- **RSI bas** (marché survendu) → Achète **plus** (c'est potentiellement les soldes)
- **RSI haut** (marché suracheté) → Achète **moins** ou **skip**
- **MVRV** : indicateur on-chain pour évaluer si Bitcoin est sur/sous-évalué
- **Régime de marché** (MA200) : détermine le split BTC/ETH

C'est du DCA intelligent : vous investissez plus quand les prix sont bas.
"""
    )

with st.expander("Quelle est la différence entre DCA classique et DCA RSI ?"):
    st.markdown(
        """
| | DCA Classique | DCA RSI v2 |
|---|---|---|
| Montant | Fixe chaque jour | Variable selon le marché |
| Indicateurs | Aucun | RSI, MVRV, MA200 |
| Paires | 1 paire au choix | BTC + ETH (split auto) |
| Complexité | Simple | Avancé |
| Performance historique | Bonne | Potentiellement meilleure |

Les deux sont disponibles dans InvestX. Commencez par le DCA classique si
vous débutez.
"""
    )

st.divider()

# ── Technique ──
st.subheader("⚙️ Technique")

with st.expander("À quelle heure le bot achète-t-il ?"):
    st.markdown(
        """
Vous configurez l'heure d'exécution dans la **page DCA Config** (en heure UTC).

- Le bot vérifie chaque minute si c'est l'heure d'acheter
- Un seul achat par jour (sauf si vous activez **Force Rebuy**)
- Les ordres sont des **market orders** (exécution immédiate au meilleur prix)
"""
    )

with st.expander("Pourquoi mon DCA n'a pas été exécuté ?"):
    st.markdown(
        """
Causes possibles :

1. **Solde insuffisant** – Vérifiez votre solde sur votre exchange (USDC sur Binance, EUR ou USDC sur Revolut X)
2. **Montant trop faible** – Minimum ~5 USDC (Binance) ou ~1 EUR (Revolut X)
3. **Exchange déconnecté** – Vérifiez la page Intégrations
4. **Abonnement inactif** – Vérifiez la page Subscription
5. **Heure non atteinte** – Le bot exécute à l'heure configurée (UTC)
6. **Déjà exécuté aujourd'hui** – Un seul achat/jour. Utilisez Force Rebuy.
"""
    )

st.divider()

st.caption(
    "💬 D'autres questions ? Contactez-nous via Telegram : **@InvestX_The_Bot**"
)
