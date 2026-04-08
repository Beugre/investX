"""
Endpoints Alertes de prix : CRUD + vérification automatique.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth_firebase import get_current_uid
from app.core.constants import ALLOWED_SYMBOLS
from app.core.exceptions import BadRequest
from app.services import firestore_service

router = APIRouter(tags=["Alerts"])


class AlertCreate(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDC"])
    target_price: float = Field(..., gt=0)
    direction: str = Field(..., pattern="^(above|below)$")


class AlertRead(BaseModel):
    id: str = ""
    symbol: str = ""
    target_price: float = 0
    direction: str = "above"
    triggered: bool = False
    created_at: str = ""


@router.get("/alerts", response_model=list[AlertRead])
async def list_alerts(uid: str = Depends(get_current_uid)):
    """Liste les alertes de prix de l'utilisateur."""
    alerts = firestore_service.list_price_alerts(uid)
    return [AlertRead(**a) for a in alerts]


@router.post("/alerts", response_model=AlertRead)
async def create_alert(payload: AlertCreate, uid: str = Depends(get_current_uid)):
    """Crée une alerte de prix."""
    if payload.symbol not in ALLOWED_SYMBOLS:
        raise BadRequest(f"Symbol '{payload.symbol}' not allowed")
    alert = firestore_service.create_price_alert(
        uid, payload.symbol, payload.target_price, payload.direction,
    )
    return AlertRead(**alert)


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, uid: str = Depends(get_current_uid)):
    """Supprime une alerte de prix."""
    firestore_service.delete_price_alert(uid, alert_id)
    return {"status": "deleted"}
