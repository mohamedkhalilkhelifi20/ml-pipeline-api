# =============================================================================
# models/rendezvous_model.py
# =============================================================================

from datetime import datetime, timezone
from typing import Optional
from beanie import Document, PydanticObjectId
from pydantic import Field


class RendezVousDocument(Document):
    client_id:    PydanticObjectId
    doctor_id:    PydanticObjectId
    secretary_id: PydanticObjectId
    date_heure:   datetime           # heure de début, stockée en UTC naïf
    duree:        int = 30           # durée en minutes (fixe 30)
    motif:        Optional[str] = None
    statut:       str = "confirme"   # confirme | annule | termine
    created_at:   datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    class Settings:
        name = "rendezvous"
