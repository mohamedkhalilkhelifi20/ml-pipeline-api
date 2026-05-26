# =============================================================================
# rendezvous/schemas.py
# =============================================================================

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RendezVousCreate(BaseModel):
    client_id:  str
    date_heure: datetime   # ISO 8601 — envoyé par le frontend (heure locale)
    motif:      Optional[str] = None


class RendezVousUpdate(BaseModel):
    client_id:  Optional[str]      = None
    date_heure: Optional[datetime] = None
    motif:      Optional[str]      = None


class RendezVousOut(BaseModel):
    id:           str
    client_id:    str
    client_nom:   str
    doctor_id:    str
    doctor_nom:   str
    secretary_id: str
    date_heure:   str      # ISO string renvoyé tel quel
    duree:        int
    motif:        Optional[str]
    statut:       str
    created_at:   str
