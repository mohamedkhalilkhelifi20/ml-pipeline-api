# =============================================================================
# clients/schemas.py — Pydantic schemas pour les clients/patients
# =============================================================================

from pydantic import BaseModel
from typing import Optional


class ClientCreate(BaseModel):
    nom:            str
    prenom:         str
    doctor_id:      str          # ID du médecin assigné
    date_naissance: Optional[str] = None
    sexe:           Optional[str] = None
    telephone:      Optional[str] = None
    adresse:        Optional[str] = None
    notes:          Optional[str] = None


class ClientOut(BaseModel):
    id:             str
    nom:            str
    prenom:         str
    date_naissance: Optional[str]
    sexe:           Optional[str]
    telephone:      Optional[str]
    adresse:        Optional[str]
    notes:          Optional[str]
    doctor_id:      str
    doctor_name:    Optional[str]   # Full name du médecin (join)
    secretary_id:   str
    secretary_name: Optional[str]   # Full name de la secrétaire (join)
    created_at:     str
