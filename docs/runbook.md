# InvestX – Runbook

## Démarrage local

### Prérequis
- Python 3.11+
- Compte Firebase avec Firestore activé
- Compte Stripe (mode test)
- Projet GCP avec Firestore activé
- Service account JSON avec permissions Firestore

### Installation

```bash
# Cloner et installer
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copier et remplir les variables d'environnement
cp .env.example .env
# Éditer .env avec vos credentials

# Lancer le backend
uvicorn app.main:app --reload --port 8000
```

```bash
# Dashboard (autre terminal)
cd dashboard
pip install -r requirements.txt
streamlit run Accueil.py
```

### Variables d'environnement à configurer
- `FIREBASE_PROJECT_ID` : ID de votre projet Firebase
- `GOOGLE_APPLICATION_CREDENTIALS` : chemin vers le fichier service account
- `STRIPE_SECRET_KEY` : clé secrète Stripe (sk_test_...)
- `STRIPE_WEBHOOK_SECRET` : secret webhook (whsec_...)
- `STRIPE_PRICE_ID` : ID du prix d'abonnement
- `TELEGRAM_BOT_TOKEN` : token du bot Telegram
- `TELEGRAM_WEBHOOK_SECRET` : secret du webhook Telegram si `TELEGRAM_WEBHOOK_MODE=true`
- `ENCRYPTION_KEY` : clé symétrique utilisée pour chiffrer les credentials exchange

### Secrets Streamlit
Créer `dashboard/.streamlit/secrets.toml` :
```toml
FIREBASE_API_KEY = "AIza..."
```

## Déploiement VPS

### 1. Installer les services systemd
```bash
sudo cp infra/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable investx-backend investx-dashboard
sudo systemctl start investx-backend investx-dashboard
```

### 2. Configurer Nginx
```bash
sudo cp infra/nginx.conf /etc/nginx/sites-available/investx
sudo ln -s /etc/nginx/sites-available/investx /etc/nginx/sites-enabled/
sudo certbot --nginx -d your-domain.com
sudo systemctl reload nginx
```

### 3. Configurer le webhook Stripe
- URL : `https://your-domain.com/api/billing/webhook`
- Événements : checkout.session.completed, customer.subscription.*, invoice.*

## Monitoring

### Vérifier la santé
```bash
curl http://localhost:8000/health
```

### Logs
```bash
journalctl -u investx-backend -f
journalctl -u investx-dashboard -f
```

### Lancer un cycle DCA manuellement
```bash
curl -X POST http://localhost:8000/internal/run-dca-cycle
```

## Troubleshooting

| Problème | Solution |
|----------|----------|
| Token Firebase invalide | Vérifier GOOGLE_APPLICATION_CREDENTIALS |
| Webhook Stripe 400 | Vérifier STRIPE_WEBHOOK_SECRET |
| Lecture/écriture des secrets chiffrés impossible | Vérifier Firestore et la variable `ENCRYPTION_KEY` |
| Binance order failed | Vérifier que l'API key a la permission trading |
| Telegram ne fonctionne pas | Vérifier TELEGRAM_BOT_TOKEN et chat_id |
