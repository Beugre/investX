# InvestX – SaaS DCA Crypto Multi-utilisateur

Automatisez vos achats DCA crypto sur Binance avec un abonnement mensuel.

## Fonctionnalités

- 🔐 Authentification Firebase (email/password)
- 💳 Abonnement Stripe (checkout + webhooks)
- 🟡 Connexion Binance (API trading only, sans retrait)
- 🔒 Stockage sécurisé des clés via Google Secret Manager
- ⚙️ Configuration DCA (paire, montant, heure)
- 🤖 Scheduler automatique (achats quotidiens)
- 📊 Dashboard Streamlit (KPIs, historique, portfolio)
- 📱 Notifications Telegram
- 📝 Logs d'audit

## Stack technique

| Composant | Technologie |
|-----------|------------|
| Backend | Python / FastAPI |
| Dashboard | Streamlit |
| Auth | Firebase Auth |
| Base de données | Cloud Firestore |
| Secrets | Google Secret Manager |
| Paiement | Stripe Subscriptions |
| Trading | Binance API |
| Notifications | Telegram Bot API |
| Scheduler | APScheduler |

## Structure du projet

```
├── backend/          # API FastAPI + services + scheduler
├── dashboard/        # Interface Streamlit multipage
├── infra/            # Configs nginx, systemd, Firestore rules
├── docs/             # Documentation technique
└── README.md
```

## Démarrage rapide

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Remplir avec vos credentials
uvicorn app.main:app --reload --port 8000

# Dashboard (autre terminal)
cd dashboard
streamlit run streamlit_app.py
```

## Documentation

- [Architecture](docs/architecture.md)
- [Contrat API](docs/api_contract.md)
- [Schéma Firestore](docs/firestore_schema.md)
- [Runbook](docs/runbook.md)

## Paires supportées (MVP)

`BTCEUR` · `ETHEUR` · `BNBEUR` · `ADAEUR` · `SOLEUR`

## Sécurité

- Les clés Binance ne sont **jamais** stockées en clair dans Firestore
- API Binance **trading only** (pas de retrait)
- Chaque utilisateur ne voit que **ses propres données**
- Webhook Stripe vérifié par signature
- Les secrets ne sont jamais renvoyés au frontend

## Licence

Projet privé – Tous droits réservés.
