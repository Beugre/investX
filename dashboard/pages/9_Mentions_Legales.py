"""
Page 9 – Mentions légales, CGU et Politique de confidentialité.
"""

import streamlit as st
from components.auth_guard import require_auth

st.set_page_config(page_title="Mentions légales – InvestX", page_icon="📜", layout="wide")

# Pas de require_auth ici : pages juridiques accessibles publiquement
# (on le laisse disponible pour les visiteurs non connectés aussi)

st.title("📜 Mentions légales")

tab_cgu, tab_privacy, tab_risk = st.tabs([
    "Conditions Générales d'Utilisation",
    "Politique de confidentialité",
    "Avertissement sur les risques",
])

# ═══════════════════════════════════════════
# CGU
# ═══════════════════════════════════════════
with tab_cgu:
    st.markdown(
        """
## Conditions Générales d'Utilisation

**Dernière mise à jour : 25 mars 2026**

### 1. Objet

Les présentes Conditions Générales d'Utilisation (CGU) régissent l'accès et
l'utilisation du service InvestX, accessible à l'adresse **investxbot.com**.

InvestX est un outil d'automatisation d'achats récurrents de cryptomonnaies
(DCA – Dollar-Cost Averaging) via l'API Binance.

### 2. Éditeur du service

- **Nom** : *[À compléter – nom ou raison sociale]*
- **Adresse** : *[À compléter]*
- **Email** : contact@investxbot.com
- **Hébergeur** : Contabo GmbH, Aschauer Straße 32a, 81549 München, Allemagne

### 3. Inscription et compte utilisateur

- L'inscription est ouverte à toute personne physique majeure (18 ans minimum).
- L'utilisateur s'engage à fournir des informations exactes et à maintenir
  la confidentialité de ses identifiants.
- Chaque utilisateur est responsable de l'activité sur son compte.

### 4. Description du service

InvestX fournit :
- Un tableau de bord pour configurer et suivre des achats DCA automatisés
- La connexion à un compte Binance via clés API (lecture + trading Spot uniquement)
- Des notifications Telegram optionnelles
- Un suivi de performance (PnL, historique, graphiques)

### 5. Abonnement et paiement

- L'accès au service nécessite un abonnement payant géré via Stripe.
- Les prix sont affichés en EUR ou USD avant paiement.
- L'abonnement est renouvelé automatiquement sauf annulation.
- L'utilisateur peut annuler à tout moment depuis la page Abonnement.

### 6. Responsabilités

**InvestX ne fournit PAS de conseil en investissement.**

- InvestX est un outil technique d'exécution automatisée d'ordres d'achat.
- L'utilisateur est seul responsable de ses décisions d'investissement.
- InvestX ne garantit aucun rendement ni performance.
- InvestX ne peut être tenu responsable des pertes financières liées à
  l'utilisation du service ou à la volatilité des marchés cryptos.

### 7. Sécurité des clés API

- Les clés API Binance sont chiffrées (AES-256 / Fernet) et stockées de
  manière sécurisée.
- InvestX ne demande jamais l'activation des retraits sur les clés API.
- L'utilisateur est responsable de la configuration correcte des permissions
  et restrictions IP de ses clés API.

### 8. Résiliation

- L'utilisateur peut supprimer son compte à tout moment.
- InvestX se réserve le droit de suspendre un compte en cas d'utilisation abusive.

### 9. Limitation de responsabilité

InvestX est fourni "tel quel". Dans les limites permises par la loi :
- Aucune garantie de disponibilité ininterrompue du service
- Aucune garantie de performance des investissements
- Responsabilité limitée au montant des abonnements payés au cours des 12 derniers mois

### 10. Droit applicable

Les présentes CGU sont régies par le droit français. Tout litige sera soumis
aux tribunaux compétents de Paris.
"""
    )

# ═══════════════════════════════════════════
# Politique de confidentialité
# ═══════════════════════════════════════════
with tab_privacy:
    st.markdown(
        """
## Politique de confidentialité (RGPD)

**Dernière mise à jour : 25 mars 2026**

### 1. Responsable du traitement

- **Nom** : *[À compléter]*
- **Email** : contact@investxbot.com

### 2. Données collectées

| Donnée | Finalité | Base légale |
|--------|----------|-------------|
| Email | Authentification, communication | Contrat |
| Nom, prénom | Personnalisation de l'interface | Contrat |
| Clés API Binance (chiffrées) | Exécution des ordres DCA | Contrat |
| Chat ID Telegram | Notifications | Consentement |
| Historique des ordres | Suivi de performance | Contrat |
| Adresse IP | Sécurité, rate limiting | Intérêt légitime |

### 3. Stockage et sécurité

- Les données sont stockées sur **Google Cloud Firestore** (UE) et un serveur
  **Contabo** (Allemagne).
- Les clés API Binance sont chiffrées avec **AES-256 (Fernet)**.
- Les mots de passe sont gérés par **Firebase Authentication** (hachage bcrypt).
- L'accès aux données est restreint et journalisé.

### 4. Durée de conservation

- **Données de compte** : conservées tant que le compte est actif, supprimées
  dans les 30 jours suivant la demande de suppression.
- **Historique des ordres** : conservé tant que le compte est actif.
- **Logs techniques** : 90 jours maximum.

### 5. Vos droits (RGPD)

Conformément au RGPD, vous disposez des droits suivants :
- **Accès** : consulter vos données personnelles
- **Rectification** : corriger vos données (page Paramètres)
- **Suppression** : demander la suppression de votre compte et données
- **Portabilité** : obtenir vos données dans un format structuré
- **Opposition** : vous opposer au traitement de vos données

Pour exercer vos droits : **contact@investxbot.com**

### 6. Cookies

InvestX utilise uniquement des cookies **techniques** (session Streamlit).
Aucun cookie publicitaire ou de tracking n'est utilisé.

### 7. Sous-traitants

| Sous-traitant | Service | Localisation |
|---------------|---------|-------------|
| Google (Firebase) | Auth + base de données | UE |
| Contabo | Hébergement serveur | Allemagne |
| Stripe | Paiements | UE/US |
| Telegram | Notifications | International |
| Binance | Exécution des ordres | International |

### 8. Transferts hors UE

Certaines données peuvent être transférées vers Stripe (US) et Binance
(international). Ces transferts sont encadrés par les clauses contractuelles
types de la Commission européenne.

### 9. Contact DPO

Pour toute question relative à vos données personnelles :
**contact@investxbot.com**
"""
    )

# ═══════════════════════════════════════════
# Avertissement risques
# ═══════════════════════════════════════════
with tab_risk:
    st.markdown(
        """
## ⚠️ Avertissement sur les risques

### Risques liés aux cryptomonnaies

**L'investissement en cryptomonnaies comporte des risques significatifs,
notamment un risque de perte totale du capital investi.**

- Les marchés des cryptomonnaies sont **extrêmement volatils**
- Les prix peuvent varier de façon significative en quelques heures
- Les performances passées **ne garantissent pas** les résultats futurs
- Les cryptomonnaies ne sont pas garanties par un État ou une institution

### InvestX n'est PAS un conseiller en investissement

- InvestX est un **outil technique** d'automatisation d'ordres
- Aucune recommandation d'achat ou de vente n'est formulée
- L'utilisateur est **seul responsable** de ses décisions d'investissement
- InvestX ne garantit **aucun rendement**

### Recommandations

- N'investissez que de l'argent que vous pouvez vous permettre de **perdre**
- Diversifiez vos investissements
- Formez-vous avant d'investir
- Consultez un conseiller financier agréé si nécessaire

### Cadre réglementaire

InvestX n'est pas enregistré en tant que Prestataire de Services sur Actifs
Numériques (PSAN) auprès de l'AMF. Le service est un outil technique
d'exécution automatique et ne constitue pas une activité de gestion pour
compte de tiers.
"""
    )
