"""
Schémas Pydantic – Telegram.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TelegramLinkRequestRead(BaseModel):
    link_code: str
    expires_at: datetime
    bot_url: str


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
