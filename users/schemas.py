# =============================================================================
# users/schemas.py — Pydantic schemas pour les profils utilisateurs
# =============================================================================

from pydantic import BaseModel
from typing import Optional


class DoctorOut(BaseModel):
    id:         str
    full_name:  str
    email:      str
    specialite: Optional[str]


class UserUpdateRequest(BaseModel):
    full_name:  Optional[str] = None
    specialite: Optional[str] = None
