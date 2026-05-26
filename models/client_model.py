# =============================================================================
# models/client_model.py — Patient lié à un médecin
# =============================================================================

from datetime import datetime, timezone
from typing import Optional
from beanie import Document, PydanticObjectId
from pydantic import Field


class ClientDocument(Document):
    # ── Numéro dossier unique ─────────────────────────────────────────────────
    numero_dossier: str                   # ex: PAT-202505-A3F1

    # ── Identité ──────────────────────────────────────────────────────────────
    nom:            str
    prenom:         str
    full_name:      str                   # "{prenom} {nom}" — champ de recherche/affichage
    date_naissance: Optional[str] = None  # "YYYY-MM-DD"
    sexe:           Optional[str] = None  # "M" | "F"
    telephone:      Optional[str] = None
    adresse:        Optional[str] = None

    # ── Relations ─────────────────────────────────────────────────────────────
    doctor_id:    PydanticObjectId
    secretary_id: PydanticObjectId

    # ── Métadonnées ───────────────────────────────────────────────────────────
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "clients"
