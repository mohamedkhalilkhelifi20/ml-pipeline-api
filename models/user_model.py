# =============================================================================
# models/user_model.py
# =============================================================================

from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from beanie import Document, PydanticObjectId
from pydantic import Field


class Role(str, Enum):
    ADMIN     = "admin"
    DOCTOR    = "doctor"
    SECRETARY = "secretary"


class UserDocument(Document):
    email:              str
    hashed_password:    str
    full_name:          str
    role:               Role
    # médecin
    specialite:         Optional[str] = None
    # secrétaire
    assigned_doctor_id: Optional[PydanticObjectId] = None
    telephone:          Optional[str] = None
    adresse:            Optional[str] = None
    is_active:          bool = True
    created_at:         datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "users"
