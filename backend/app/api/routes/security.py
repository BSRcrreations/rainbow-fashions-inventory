from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.security import DestructiveSecurityRead
from app.services.destructive_action_service import DestructiveActionService


router = APIRouter(prefix="/security", tags=["Security"])


@router.get("/destructive-actions", response_model=DestructiveSecurityRead)
def destructive_security(db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return DestructiveActionService(db).security(current_user)
