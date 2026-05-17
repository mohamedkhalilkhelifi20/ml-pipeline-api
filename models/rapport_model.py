# =============================================================================
# models/rapport_model.py — Schéma MongoDB via Beanie
# StrokeAI | Historique rapports + patients
# =============================================================================

from datetime import datetime, timezone
from typing import Any, Optional
from beanie import Document, PydanticObjectId
from pydantic import Field


class RapportDocument(Document):
    """
    Un document = une prédiction + rapport IA pour un patient.
    Stocké dans la collection 'rapports' de la DB strokeai.
    """

    # ── Identification ────────────────────────────────────────────────────────
    axe:            int
    patient_nom:    str
    patient_prenom: str

    # ── Relations (optionnelles pour compatibilité ascendante) ────────────────
    client_id:  Optional[PydanticObjectId] = None   # Lien vers ClientDocument
    doctor_id:  Optional[PydanticObjectId] = None   # Médecin ayant généré le rapport

    # ── Données cliniques brutes ──────────────────────────────────────────────
    patient_data: dict[str, Any]

    # ── Résultat ML ───────────────────────────────────────────────────────────
    prediction: dict[str, Any]

    # ── Rapport IA ────────────────────────────────────────────────────────────
    rapport_texte: str
    modele_llm:    str = "phi3:mini"

    # ── Métadonnées ───────────────────────────────────────────────────────────
    medecin_nom: Optional[str] = None   # Conservé pour les anciens documents
    created_at:  datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "rapports"
