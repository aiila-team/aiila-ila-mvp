"""
ILA — Auth API Endpoints
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
Generated with Claude assistance — reviewed by Likhitha
"""

from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.db.session import get_db
from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user_id,
)
from app.models import User, UserRole
from app.schemas.schema import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


# ─────────────────────────────────────────
# POST /api/v1/auth/login
# ─────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning(f"Failed login attempt for username: {payload.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    logger.info(f"User {user.username} logged in successfully")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ─────────────────────────────────────────
# POST /api/v1/auth/refresh
# ─────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(token: str, db: Session = Depends(get_db)):
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type — must be refresh token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


# ─────────────────────────────────────────
# GET /api/v1/auth/me
# ─────────────────────────────────────────

@router.get("/me", response_model=UserOut)
def get_me(
    current_user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# ─────────────────────────────────────────
# Helper: seed a default admin user (call once on startup)
# ─────────────────────────────────────────

def seed_default_user(db: Session):
    """Creates a default analyst account if no users exist. Remove after Day 1."""
    existing = db.query(User).first()
    if not existing:
        admin = User(
            username="likhitha",
            email="likhitha@aiila.in",
            hashed_password=hash_password("ila@2026"),
            full_name="Likhitha",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        logger.info("Default user 'likhitha' seeded — change password after first login!")