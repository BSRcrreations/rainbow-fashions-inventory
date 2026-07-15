from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import unauthorized
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserRead


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.db.query(User).filter(User.email == payload.email).first()
        if not user or not verify_password(payload.password, user.password_hash):
            raise unauthorized("Invalid email or password")
        if not user.is_active:
            raise unauthorized("User account is inactive")

        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        token = create_access_token(str(user.id), {"role": user.role.value, "store_id": str(user.store_id) if user.store_id else None})
        return TokenResponse(access_token=token, user=UserRead.model_validate(user))
