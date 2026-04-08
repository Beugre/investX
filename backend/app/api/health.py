"""Endpoint de santé avec vérifications système."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])

_start_time = datetime.now(timezone.utc)


@router.get("/health")
async def health_check():
    """Retourne le statut de santé avec uptime et checks."""
    now = datetime.now(timezone.utc)
    uptime_seconds = (now - _start_time).total_seconds()

    checks = {}

    # Check Firestore
    try:
        from app.services import firestore_service
        firestore_service.get_user("health_check_probe")
        checks["firestore"] = "ok"
    except Exception as e:
        checks["firestore"] = f"error: {e}"

    # Check Scheduler
    try:
        from app.scheduler.runner import scheduler
        checks["scheduler"] = "running" if scheduler.running else "stopped"
    except Exception:
        checks["scheduler"] = "unknown"

    overall = "ok" if all(
        v in ("ok", "running") for v in checks.values()
    ) else "degraded"

    return {
        "status": overall,
        "service": "investx-backend",
        "uptime_seconds": round(uptime_seconds),
        "checks": checks,
        "timestamp": now.isoformat(),
    }


@router.get("/health/scheduler")
async def scheduler_health():
    """Détail des jobs du scheduler (next_run, état)."""
    from app.scheduler.runner import scheduler

    if not scheduler.running:
        return {"status": "stopped", "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {"status": "running", "jobs": jobs}
