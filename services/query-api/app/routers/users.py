from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import UserOut, UserCreate, UserUpdate
from app.services.auth import AuthService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    """List all users."""
    result = await db.execute(
        text("SELECT id, username, clearance, is_active, created_at FROM users ORDER BY created_at DESC")
    )
    rows = result.fetchall()
    return [
        UserOut(id=row[0], username=row[1], clearance=row[2], is_active=row[3], created_at=row[4])
        for row in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new user with a generated API key.

    The API key is returned ONCE in the response. Store it securely.
    """
    # Check duplicate
    existing = await db.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": body.username},
    )
    if existing.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{body.username}' already exists",
        )

    api_key = AuthService.generate_api_key()
    api_key_hash = AuthService.hash_api_key(api_key)

    result = await db.execute(
        text("""
            INSERT INTO users (username, clearance, api_key_hash)
            VALUES (:username, :clearance, :api_key_hash)
            RETURNING id, username, clearance, is_active, created_at
        """),
        {
            "username": body.username,
            "clearance": body.clearance.value,
            "api_key_hash": api_key_hash,
        },
    )
    await db.commit()
    row = result.fetchone()

    return {
        "id": str(row[0]),
        "username": row[1],
        "clearance": row[2],
        "is_active": row[3],
        "created_at": row[4].isoformat(),
        "api_key": api_key,  # Returned ONCE — not stored in plaintext
        "warning": "Store this API key securely. It will not be shown again.",
    }


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Update a user's clearance level or active status."""
    updates = []
    params: dict = {"user_id": str(user_id)}

    if body.clearance is not None:
        updates.append("clearance = :clearance")
        params["clearance"] = body.clearance.value
    if body.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = body.is_active

    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    query = f"UPDATE users SET {', '.join(updates)} WHERE id = :user_id RETURNING id, username, clearance, is_active, created_at"
    result = await db.execute(text(query), params)
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.commit()
    return UserOut(id=row[0], username=row[1], clearance=row[2], is_active=row[3], created_at=row[4])


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate a user (soft delete)."""
    result = await db.execute(
        text("UPDATE users SET is_active = false WHERE id = :user_id RETURNING id"),
        {"user_id": str(user_id)},
    )
    if not result.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.commit()
