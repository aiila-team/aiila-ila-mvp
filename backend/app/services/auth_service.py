from sqlalchemy.orm import Session

from app.models import User
from app.schemas.user import UserCreate
from app.core.security import (
    hash_password,
    verify_password
)

def create_user(db: Session, user: UserCreate):
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hash_password(user.password)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

def authenticate_user(
    db: Session,
    username: str,
    password: str
):
    user = db.query(User).filter(
        User.username == username
    ).first()

    if not user:
        return None

    if not verify_password(
        password,
        user.hashed_password
    ):
        return None

    return user