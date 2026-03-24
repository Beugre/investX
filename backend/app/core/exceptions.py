"""
Exceptions métier centralisées.
"""

from __future__ import annotations

from fastapi import HTTPException, status


class NotAuthenticated(HTTPException):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class Forbidden(HTTPException):
    def __init__(self, detail: str = "Access denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFound(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequest(HTTPException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class SubscriptionInactive(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required",
        )


class BinanceError(Exception):
    """Erreur lors d'une opération Binance."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class SecretManagerError(Exception):
    """Erreur lors d'une opération Secret Manager."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
