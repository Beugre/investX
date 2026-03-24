"""
Dependencies FastAPI partagées.
"""

from __future__ import annotations

from app.core.auth_firebase import get_current_uid

# Ré-export pour usage dans les routers
__all__ = ["get_current_uid"]
