"""
InvestX – SaaS DCA Crypto Multi-utilisateur
Configuration de l'application via variables d'environnement.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Paramètres globaux de l'application, chargés depuis .env."""

    # ── App ──
    app_env: str = Field("development", alias="APP_ENV")
    app_base_url: str = Field("http://localhost:8000", alias="APP_BASE_URL")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # ── Firebase / GCP ──
    firebase_project_id: str = Field(..., alias="FIREBASE_PROJECT_ID")
    google_application_credentials: str | None = Field(
        None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )

    # ── Stripe ──
    stripe_secret_key: str = Field(..., alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field("", alias="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = Field(..., alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id: str = Field(..., alias="STRIPE_PRICE_ID")
    stripe_success_url: str = Field(
        "http://localhost:8501/Subscription?success=true",
        alias="STRIPE_SUCCESS_URL",
    )
    stripe_cancel_url: str = Field(
        "http://localhost:8501/Subscription?canceled=true",
        alias="STRIPE_CANCEL_URL",
    )

    # ── Telegram ──
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_mode: bool = Field(False, alias="TELEGRAM_WEBHOOK_MODE")
    telegram_webhook_secret: str = Field("", alias="TELEGRAM_WEBHOOK_SECRET")

    # ── Binance ──
    binance_base_url: str = Field(
        "https://api.binance.com", alias="BINANCE_BASE_URL"
    )

    # ── Defaults ──
    default_timezone: str = Field("Europe/Paris", alias="DEFAULT_TIMEZONE")
    allowed_symbols: str = Field(
        "BTCUSDC,ETHUSDC,BNBUSDC,ADAUSDC,SOLUSDC", alias="ALLOWED_SYMBOLS"
    )

    @property
    def allowed_symbols_list(self) -> list[str]:
        return [s.strip() for s in self.allowed_symbols.split(",") if s.strip()]

    model_config = {
        "env_file": (".env", "backend/.env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()  # type: ignore[call-arg]
