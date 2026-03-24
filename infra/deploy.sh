#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────
# InvestX – Script de déploiement sur VPS (Ubuntu/Debian)
# Usage : scp deploy.sh user@VPS_IP:/tmp/ && ssh user@VPS_IP 'bash /tmp/deploy.sh'
#   OU : ssh user@VPS_IP 'bash -s' < deploy.sh
#
# Prérequis : git, Python 3.10+, nginx, accès sudo
# Ports utilisés : 8600 (backend), 8601 (dashboard), 80/443 (nginx)
# ────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuration ──
APP_USER="investx"
APP_DIR="/opt/investx"
REPO_URL="https://github.com/Beugre/investX.git"
BRANCH="main"
PYTHON_BIN="python3.10"                                  # ← Adapter si besoin

# ── Couleurs ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[DEPLOY]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Vérifications ──
[[ $EUID -eq 0 ]] || err "Ce script doit être exécuté en root (sudo)."
command -v $PYTHON_BIN &>/dev/null || err "$PYTHON_BIN introuvable. Installez-le : apt install python3.10 python3.10-venv"

# ──────────────────────────────────────────────────────────
# 1. Créer l'utilisateur système
# ──────────────────────────────────────────────────────────
log "1/8 – Création de l'utilisateur $APP_USER..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" "$APP_USER"
    log "  Utilisateur $APP_USER créé."
else
    log "  Utilisateur $APP_USER existe déjà."
fi

# ──────────────────────────────────────────────────────────
# 2. Installer les paquets système
# ──────────────────────────────────────────────────────────
log "2/8 – Installation des paquets système..."
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx git curl

# ──────────────────────────────────────────────────────────
# 3. Cloner ou mettre à jour le code
# ──────────────────────────────────────────────────────────
log "3/8 – Récupération du code..."
if [[ -d "$APP_DIR/.git" ]]; then
    cd "$APP_DIR"
    sudo -u "$APP_USER" git fetch origin "$BRANCH"
    sudo -u "$APP_USER" git reset --hard "origin/$BRANCH"
    log "  Code mis à jour (git pull)."
else
    mkdir -p "$APP_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    log "  Code cloné."
fi

# ──────────────────────────────────────────────────────────
# 4. Créer le virtualenv & installer les dépendances
# ──────────────────────────────────────────────────────────
log "4/8 – Création du virtualenv & installation des dépendances..."
if [[ ! -d "$APP_DIR/venv" ]]; then
    sudo -u "$APP_USER" $PYTHON_BIN -m venv "$APP_DIR/venv"
fi
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip -q
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt" -q
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/dashboard/requirements.txt" -q
log "  Dépendances installées."

# ──────────────────────────────────────────────────────────
# 5. Fichiers de configuration
# ──────────────────────────────────────────────────────────
log "5/8 – Vérification des fichiers de configuration..."

if [[ ! -f "$APP_DIR/backend/.env" ]]; then
    warn "  ⚠️  $APP_DIR/backend/.env manquant !"
    warn "  Copiez .env.example et configurez vos clés :"
    warn "    cp $APP_DIR/backend/.env.example $APP_DIR/backend/.env"
    warn "    nano $APP_DIR/backend/.env"
fi

if [[ ! -f "$APP_DIR/backend/firebase-service-account.json" ]]; then
    warn "  ⚠️  firebase-service-account.json manquant !"
    warn "  Uploadez-le : scp firebase-service-account.json $APP_USER@VPS:$APP_DIR/backend/"
fi

if [[ ! -d "$APP_DIR/dashboard/.streamlit" ]]; then
    mkdir -p "$APP_DIR/dashboard/.streamlit"
    chown "$APP_USER:$APP_USER" "$APP_DIR/dashboard/.streamlit"
fi

if [[ ! -f "$APP_DIR/dashboard/.streamlit/secrets.toml" ]]; then
    warn "  ⚠️  dashboard/.streamlit/secrets.toml manquant !"
    warn "  Créez-le avec FIREBASE_API_KEY et API_BASE_URL"
fi

# ──────────────────────────────────────────────────────────
# 6. Certificat SSL auto-signé (si pas Let's Encrypt)
# ──────────────────────────────────────────────────────────
log "6/8 – Certificat SSL..."
if [[ ! -f /etc/ssl/certs/investx-selfsigned.crt ]]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/investx-selfsigned.key \
        -out /etc/ssl/certs/investx-selfsigned.crt \
        -subj "/CN=investx-vps" 2>/dev/null
    log "  Certificat auto-signé créé."
else
    log "  Certificat SSL déjà présent."
fi

# ──────────────────────────────────────────────────────────
# 7. Services systemd
# ──────────────────────────────────────────────────────────
log "7/8 – Installation des services systemd..."

cp "$APP_DIR/infra/systemd/backend.service"   /etc/systemd/system/investx-backend.service
cp "$APP_DIR/infra/systemd/dashboard.service"  /etc/systemd/system/investx-dashboard.service

systemctl daemon-reload
systemctl enable investx-backend investx-dashboard

# Redémarrer les services
systemctl restart investx-backend
sleep 2
systemctl restart investx-dashboard

log "  Services installés et démarrés."

# Vérification
for svc in investx-backend investx-dashboard; do
    if systemctl is-active --quiet "$svc"; then
        log "  ✅ $svc est actif."
    else
        warn "  ❌ $svc n'est pas actif ! Vérifiez : journalctl -u $svc -n 50"
    fi
done

# ──────────────────────────────────────────────────────────
# 8. Nginx
# ──────────────────────────────────────────────────────────
log "8/8 – Configuration Nginx..."

cp "$APP_DIR/infra/nginx.conf" /etc/nginx/sites-available/investx

if [[ ! -L /etc/nginx/sites-enabled/investx ]]; then
    ln -s /etc/nginx/sites-available/investx /etc/nginx/sites-enabled/investx
fi

# Tester et recharger
nginx -t && systemctl reload nginx
log "  Nginx configuré et rechargé."

# ──────────────────────────────────────────────────────────
# Résumé
# ──────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════"
echo "   🎉  InvestX déployé avec succès !"
echo "════════════════════════════════════════════════════"
echo ""
echo "  Backend  : http://127.0.0.1:8600  (systemd: investx-backend)"
echo "  Dashboard: http://127.0.0.1:8601  (systemd: investx-dashboard)"
echo "  Nginx    : https://YOUR_DOMAIN_OR_IP"
echo ""
echo "  Commandes utiles :"
echo "    sudo systemctl status investx-backend"
echo "    sudo systemctl status investx-dashboard"
echo "    sudo journalctl -u investx-backend -f"
echo "    sudo journalctl -u investx-dashboard -f"
echo ""
echo "  ⚠️  N'oubliez pas de :"
echo "    1. Configurer backend/.env avec vos clés de production"
echo "    2. Uploader firebase-service-account.json"
echo "    3. Créer dashboard/.streamlit/secrets.toml"
echo "    4. Remplacer YOUR_DOMAIN_OR_IP dans /etc/nginx/sites-available/investx"
echo "    5. (Optionnel) Obtenir un certificat Let's Encrypt :"
echo "       certbot --nginx -d votre-domaine.com"
echo "════════════════════════════════════════════════════"
