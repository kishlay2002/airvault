import secrets
from uuid import UUID

import bcrypt
import structlog
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import SensitivityTier

logger = structlog.get_logger()

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


class AuthService:
    """API key authentication and user resolution."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a cryptographically secure API key."""
        return f"vm_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key with bcrypt."""
        return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_api_key(api_key: str, hashed: str) -> bool:
        """Verify an API key against its bcrypt hash."""
        return bcrypt.checkpw(api_key.encode(), hashed.encode())

    @staticmethod
    async def resolve_user(api_key: str, db: AsyncSession) -> dict:
        """Resolve API key to user record.

        Returns dict with: id, username, clearance, is_active
        Raises HTTPException if key is invalid or user is inactive.
        """
        # Strip "Bearer " prefix if present
        if api_key.startswith("Bearer "):
            api_key = api_key[7:]

        result = await db.execute(
            text("SELECT id, username, clearance, api_key_hash, is_active FROM users WHERE is_active = true")
        )
        rows = result.fetchall()

        for row in rows:
            user_id, username, clearance, stored_hash, is_active = row
            if AuthService.verify_api_key(api_key, stored_hash):
                logger.info("user_authenticated", username=username, clearance=clearance)
                return {
                    "id": str(user_id),
                    "username": username,
                    "clearance": SensitivityTier(clearance),
                    "is_active": is_active,
                }

        logger.warning("authentication_failed", key_prefix=api_key[:8] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )
