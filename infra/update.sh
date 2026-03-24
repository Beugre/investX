#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────
# InvestX – Mise à jour rapide (pull + restart)
# Usage : sudo bash /opt/investx/infra/update.sh
# ────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/opt/investx"
APP_USER="investx"
BRANCH="main"

GREEN='\033[0;32m'
NC='\033[0m'
log() { echo -e "${GREEN}[UPDATE]${NC} $*"; }

[[ $EUID -eq 0 ]] || { echo "Exécutez avec sudo." >&2; exit 1; }

log "Pull du code..."
cd "$APP_DIR"
sudo -u "$APP_USER" git fetch origin "$BRANCH"
sudo -u "$APP_USER" git reset --hard "origin/$BRANCH"

log "Mise à jour des dépendances..."
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt" -q
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/dashboard/requirements.txt" -q

log "Redémarrage des services..."
systemctl restart investx-backend
sleep 2
systemctl restart investx-dashboard

for svc in investx-backend investx-dashboard; do
    if systemctl is-active --quiet "$svc"; then
        log "  ✅ $svc est actif."
    else
        log "  ❌ $svc a échoué ! → journalctl -u $svc -n 30"
    fi
done

log "Mise à jour terminée !"
