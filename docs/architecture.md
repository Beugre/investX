# InvestX – Architecture

## Vue d'ensemble

InvestX est un SaaS MVP de DCA crypto multi-utilisateur.

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Streamlit   │────▶│  FastAPI     │────▶│  Firestore       │
│  Dashboard   │     │  Backend     │     │  (données métier)│
└─────────────┘     └──────┬──────┘     └──────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
      ┌──────────┐  ┌──────────┐  ┌──────────────┐
      │  Stripe  │  │  Binance │  │  Secret       │
      │  (paiement)│ │  (trading)│ │  Manager     │
      └──────────┘  └──────────┘  └──────────────┘
              │
              ▼
      ┌──────────┐
      │ Telegram │
      │  (notifs)│
      └──────────┘
```

## Composants

| Composant | Techno | Port | Rôle |
|-----------|--------|------|------|
| Backend | FastAPI | 8000 | API, logique métier, scheduler |
| Dashboard | Streamlit | 8501 | Interface utilisateur |
| Auth | Firebase Auth | – | Authentification |
| DB | Firestore | – | Données applicatives |
| Secrets | Secret Manager | – | Credentials Binance |
| Paiement | Stripe | – | Abonnements |
| Trading | Binance API | – | Achats DCA |
| Notifications | Telegram Bot | – | Alertes |

## Flux principaux

### Inscription
1. Utilisateur crée un compte (Streamlit → Firebase Auth)
2. Backend initialise le profil Firestore (`POST /onboarding/init`)

### Abonnement
1. Utilisateur clique "S'abonner" → Stripe Checkout
2. Webhook Stripe → Backend met à jour subscription dans Firestore

### Connexion Binance
1. Utilisateur saisit API key/secret
2. Backend valide credentials + vérifie pas de retrait
3. Stockage dans Secret Manager (jamais en clair dans Firestore)

### DCA quotidien
1. Scheduler vérifie toutes les minutes
2. Pour chaque utilisateur : check abonnement, config, heure, verrou
3. Récupère credentials depuis Secret Manager
4. Passe l'ordre market buy via Binance API
5. Sauvegarde ordre + snapshot + notification Telegram
