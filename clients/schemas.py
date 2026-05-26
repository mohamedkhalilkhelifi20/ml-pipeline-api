# =============================================================================
# clients/schemas.py
# =============================================================================

from pydantic import BaseModel
from typing import Optional


class ClientCreate(BaseModel):
    nom:            str
    prenom:         str
    doctor_id:      Optional[str] = None   # auto-rempli depuis assigned_doctor_id
    date_naissance: Optional[str] = None
    sexe:           Optional[str] = None
    telephone:      Optional[str] = None
    adresse:        Optional[str] = None


class ClientUpdate(BaseModel):
    nom:            Optional[str] = None
    prenom:         Optional[str] = None
    date_naissance: Optional[str] = None
    sexe:           Optional[str] = None
    telephone:      Optional[str] = None
    adresse:        Optional[str] = None


class ClientOut(BaseModel):
    id:               str
    numero_dossier:   str
    full_name:        str
    nom:              str
    prenom:           str
    date_naissance:   Optional[str]
    sexe:             Optional[str]
    telephone:        Optional[str]
    adresse:          Optional[str]
    doctor_id:        str
    doctor_name:      Optional[str]
    secretary_id:     str
    secretary_name:   Optional[str]
    created_at:       str
