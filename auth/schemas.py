# =============================================================================
# auth/schemas.py — L'inscription publique est UNIQUEMENT pour les médecins.
# Les secrétaires sont créées par leur médecin via POST /doctor/secretary.
# =============================================================================

from typing import Optional
from pydantic import BaseModel, field_validator


# ── Inscription publique (médecin uniquement) ─────────────────────────────────

class DoctorRegisterRequest(BaseModel):
    email:      str
    password:   str
    full_name:  str
    specialite: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit avoir au moins 8 caractères")
        return v

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v: str) -> str:
        return v.lower().strip()


# ── Création de secrétaire par le médecin ─────────────────────────────────────

class SecretaryCreateRequest(BaseModel):
    full_name:  str
    email:      str
    password:   str
    telephone:  Optional[str] = None
    adresse:    Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit avoir au moins 8 caractères")
        return v

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v: str) -> str:
        return v.lower().strip()


# ── Token / Profil ────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    full_name:    str
    user_id:      str


class UserOut(BaseModel):
    id:                 str
    email:              str
    full_name:          str
    role:               str
    specialite:         Optional[str] = None
    assigned_doctor_id: Optional[str] = None
    telephone:          Optional[str] = None
    adresse:            Optional[str] = None
    is_active:          bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Minimum 8 caractères")
        return v
