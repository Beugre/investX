"""
Schémas Pydantic – Telegram.
"""

from __future__ import annotations

from pydantic import BaseModel


class TelegramLink(BaseModel):
    chat_id: str
    username: str | None = None


class TelegramSettingsRead(BaseModel):
    enabled: bool = False
    chat_id: str | None = None
    username: str | None = None
    notify_orders: bool = True
    notify_errors: bool = True
    notify_subscription: bool = True


class TelegramSettingsUpdate(BaseModel):
    enabled: bool
    notify_orders: bool
    notify_errors: bool
    notify_subscription: bool
