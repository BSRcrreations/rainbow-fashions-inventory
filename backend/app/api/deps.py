from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import unauthorized
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.enums import UserRole
from app.models.user import User


settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload.get("sub")))
    except (TypeError, ValueError):
        raise unauthorized("Invalid or expired access token")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise unauthorized("Invalid or inactive user")
    return user


def require_roles(*allowed_roles: UserRole):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            from app.core.exceptions import forbidden

            raise forbidden("You do not have permission to perform this action")
        return current_user

    return dependency


require_owner = require_roles(UserRole.OWNER)
require_manager_or_owner = require_roles(UserRole.OWNER, UserRole.MANAGER)
require_staff_or_above = require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.STAFF)
