# =============================================================================
# models/rapport_model.py — Dossier médical complet d'une consultation
# =============================================================================

from datetime import datetime, timezone
from typing import Any, Optional
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class LabDocument(BaseModel):
    """Métadonnées d'un fichier laboratoire attaché à une consultation."""
    id:            str
    original_name: str
    content_type:  str
    size:          int
    uploaded_at:   str   # ISO datetime string


class RapportDocument(Document):
    """
    Une consultation = prédiction ML + rapport IA + note médecin + docs labo.
    """

    # ── Identification ────────────────────────────────────────────────────────
    axe:            int
    patient_nom:    str
    patient_prenom: str

    # ── Relations ─────────────────────────────────────────────────────────────
    client_id:  Optional[PydanticObjectId] = None
    doctor_id:  Optional[PydanticObjectId] = None

    # ── Données cliniques brutes (inputs formulaire ML) ───────────────────────
    patient_data: dict[str, Any]

    # ── Résultat ML ───────────────────────────────────────────────────────────
    prediction: dict[str, Any]

    # ── Rapport IA (généré par SSE) ───────────────────────────────────────────
    rapport_texte: str
    modele_llm:    str = "gemini-2.0-flash-001"

    # ── Note du médecin ───────────────────────────────────────────────────────
    note_medecin: Optional[str] = None

    # ── Documents laboratoire ─────────────────────────────────────────────────
    documents_lab: list[LabDocument] = Field(default_factory=list)

    # ── Métadonnées ───────────────────────────────────────────────────────────
    medecin_nom: Optional[str] = None
    created_at:  datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "rapports"
