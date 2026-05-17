# =============================================================================
# models/client_model.py — Patient/Client lié à un médecin
# =============================================================================

from datetime import datetime, timezone
from typing import Optional
from beanie import Document, PydanticObjectId
from pydantic import Field


class ClientDocument(Document):
    # ── Identité ──────────────────────────────────────────────────────────────
    nom:              str
    prenom:           str
    date_naissance:   Optional[str] = None   # "YYYY-MM-DD"
    sexe:             Optional[str] = None   # "M" | "F"
    telephone:        Optional[str] = None
    adresse:          Optional[str] = None
    notes:            Optional[str] = None

    # ── Relations ─────────────────────────────────────────────────────────────
    doctor_id:    PydanticObjectId   # Médecin assigné
    secretary_id: PydanticObjectId   # Secrétaire créatrice

    # ── Métadonnées ───────────────────────────────────────────────────────────
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "clients"
