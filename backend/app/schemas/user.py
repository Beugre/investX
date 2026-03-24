"""
Schémas Pydantic – Utilisateur.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    uid: str
    email: str
    display_name: str | None = None
    is_active: bool = True
    timezone: str = "Europe/Paris"
    role: str = "user"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str | None = None
    timezone: str = Field(default="Europe/Paris")


class OnboardingResponse(BaseModel):
    uid: str
    message: str = "User initialized"
