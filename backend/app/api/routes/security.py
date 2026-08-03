from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.security import DestructiveSecurityRead
from app.schemas.backup import BackupStatusRead
from app.services.backup_status_service import BackupStatusService
from app.core.config import get_settings
from app.services.destructive_action_service import DestructiveActionService


router = APIRouter(prefix="/security", tags=["Security"])


@router.get("/destructive-actions", response_model=DestructiveSecurityRead)
def destructive_security(db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return DestructiveActionService(db).security(current_user)


@router.get("/backup-status", response_model=BackupStatusRead)
def backup_status(_: User = Depends(require_owner)) -> BackupStatusRead:
    """Operational backup state for owners; credentials and server paths are excluded."""
    return BackupStatusService(get_settings().backup_status_dir).status()
