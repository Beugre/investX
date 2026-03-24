# InvestX – Contrat API

Base URL : `http://localhost:8000`

Authentification : Bearer token Firebase (`Authorization: Bearer <idToken>`)

---

## Health

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| GET | `/health` | Non | Health check |
| GET | `/` | Non | Info app |

## Users

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| GET | `/me` | Oui | Profil utilisateur |
| POST | `/onboarding/init` | Oui | Initialiser profil |
| GET | `/me/profile` | Oui | Alias de /me |

## Billing (Stripe)

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/billing/create-checkout-session` | Oui | Créer session Checkout |
| POST | `/billing/create-customer-portal-session` | Oui | Portail client |
| POST | `/billing/webhook` | Stripe sig | Webhook Stripe |
| GET | `/billing/status` | Oui | Statut abonnement |

## Binance

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/binance/connect` | Oui | Connecter Binance |
| POST | `/binance/validate` | Oui | Re-valider credentials |
| DELETE | `/binance/disconnect` | Oui | Déconnecter |
| GET | `/binance/status` | Oui | Statut connexion |

## DCA Config

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| GET | `/dca/config` | Oui | Lire config |
| PUT | `/dca/config` | Oui | Mettre à jour config |
| POST | `/dca/enable` | Oui | Activer DCA |
| POST | `/dca/disable` | Oui | Désactiver DCA |

## Portfolio

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| GET | `/portfolio/summary` | Oui | Résumé portfolio |
| GET | `/portfolio/history` | Oui | Historique snapshots |
| GET | `/orders` | Oui | Liste ordres |
| GET | `/orders/latest` | Oui | Dernier ordre |

## Telegram

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/telegram/link` | Oui | Lier Telegram |
| POST | `/telegram/test` | Oui | Test notification |
| GET | `/telegram/settings` | Oui | Lire paramètres |
| PUT | `/telegram/settings` | Oui | Modifier paramètres |

## Internal (Admin)

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/internal/run-dca-cycle` | Non* | Lancer cycle DCA |
| POST | `/internal/refresh-snapshots` | Non* | Refresh snapshots |
| POST | `/internal/reconcile-subscriptions` | Non* | Réconciliation |

*À protéger en production (IP whitelist, token interne)
