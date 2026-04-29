# =============================================================================
# models/rapport_model.py — Schéma MongoDB via Beanie
# StrokeAI | Historique rapports + patients
# =============================================================================

from datetime import datetime, timezone
from typing import Any, Optional
from beanie import Document, Indexed
from pydantic import Field


class RapportDocument(Document):
    """
    Un document = une prédiction + rapport IA pour un patient.
    Stocké dans la collection 'rapports' de la DB strokeai.
    """

    # ── Identification ────────────────────────────────────────────────────────
    axe: int                          # 1, 2 ou 3
    patient_nom: str                  # nom saisi par le médecin
    patient_prenom: str               # prénom

    # ── Données cliniques brutes (variables selon l'axe) ─────────────────────
    patient_data: dict[str, Any]      # features brutes du formulaire wizard

    # ── Résultat du modèle ML ────────────────────────────────────────────────
    prediction: dict[str, Any]        # probabilité, verdict, threshold...

    # ── Rapport IA généré ────────────────────────────────────────────────────
    rapport_texte: str                # texte Markdown généré par phi3:mini
    modele_llm: str = "phi3:mini"     # modèle utilisé

    # ── Métadonnées ───────────────────────────────────────────────────────────
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    medecin_nom: Optional[str] = None  # pour plus tard (auth)

    class Settings:
        name = "rapports"             # nom de la collection MongoDB


class Settings:
    name = "rapports"
