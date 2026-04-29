from pydantic import BaseModel, Field
from typing import Literal


# OopCompanion:suppressRename


# ─────────────────────────────────────────────────────────────────────────────
# INPUT — 10 variables cliniques IST
# Features OHE reconstruites dans le service (20 colonnes au total)
# ─────────────────────────────────────────────────────────────────────────────

class Axe3FdeadInput(BaseModel):

    # ── Démographie ───────────────────────────────────────────────────────────
    AGE: float = Field(
        ..., ge=16, le=99,
        description="Âge du patient en années (16–99)"
    )
    SEX: Literal["M", "F"] = Field(
        ...,
        description="Sexe : M=Homme, F=Femme"
    )

    # ── Clinique à l'admission ────────────────────────────────────────────────
    RSBP: float = Field(
        ..., ge=60, le=300,
        description="Tension artérielle systolique à l'admission (mmHg)"
    )
    RDELAY: float = Field(
        ..., ge=0, le=48,
        description="Délai entre AVC et admission (heures)"
    )
    RDEF_SCORE: int = Field(
        ..., ge=0, le=8,
        description=(
            "Score de déficits neurologiques RDEF1–RDEF8 : "
            "somme des déficits présents (paralysie faciale, bras, jambe, "
            "dysphasie, hémianopsie, déglutition, conscience, autre). "
            "0=aucun déficit, 8=tous les déficits"
        )
    )
    RCONSC: Literal["F", "D", "U"] = Field(
        ...,
        description=(
            "État de conscience à l'admission : "
            "F=Alerte (Fully conscious), "
            "D=Somnolent (Drowsy), "
            "U=Inconscient (Unconscious)"
        )
    )
    RATRIAL: Literal["Y", "N"] = Field(
        ...,
        description="Fibrillation auriculaire : Y=Oui, N=Non"
    )
    STYPE: Literal["LACS", "PACS", "TACS", "POCS", "OTH"] = Field(
        ...,
        description=(
            "Type d'AVC (IST classification) : "
            "LACS=Lacunar (24%), PACS=Partial Anterior (40.4%), "
            "TACS=Total Anterior (23.9%), POCS=Posterior (11.5%), OTH=Autre"
        )
    )

    # ── Traitement administré ─────────────────────────────────────────────────
    RXASP: Literal["Y", "N"] = Field(
        ...,
        description="Aspirine administrée : Y=Oui, N=Non"
    )
    RXHEP: Literal["H", "L", "M", "N"] = Field(
        ...,
        description=(
            "Héparine administrée : "
            "H=Haute dose, L=Faible dose, M=Dose moyenne, N=Aucune"
        )
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "AGE": 72,
                "SEX": "M",
                "RSBP": 160,
                "RDELAY": 3.5,
                "RDEF_SCORE": 5,
                "RCONSC": "D",
                "RATRIAL": "Y",
                "STYPE": "TACS",
                "RXASP": "Y",
                "RXHEP": "L"
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# INPUT DDEAD — mêmes 10 variables cliniques que FDEAD
# Alias propre pour la lisibilité des routes et de la doc Swagger
# ─────────────────────────────────────────────────────────────────────────────

Axe3DdeadInput = Axe3FdeadInput


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT FDEAD — décès à 6 mois
# ─────────────────────────────────────────────────────────────────────────────

class Axe3FdeadOutput(BaseModel):
    probability: float = Field(
        ...,
        description="Probabilité de décès à 6 mois (0–1)"
    )
    prediction: int = Field(
        ...,
        description="0=Survie probable, 1=Décès probable"
    )
    threshold: float = Field(
        ...,
        description="Seuil de décision utilisé (optimisé Recall) — 0.25"
    )
    verdict: str = Field(
        ...,
        description="Survie probable / Décès probable"
    )
    risk_level: str = Field(
        ...,
        description="Faible / Modéré / Élevé"
    )


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT DDEAD — décès à 14 jours
# ─────────────────────────────────────────────────────────────────────────────

class Axe3DdeadOutput(BaseModel):
    probability: float = Field(
        ...,
        description="Probabilité de décès à 14 jours (0–1)"
    )
    prediction: int = Field(
        ...,
        description="0=Survie probable, 1=Décès probable"
    )
    threshold: float = Field(
        ...,
        description="Seuil de décision utilisé (optimisé Recall) — 0.20"
    )
    verdict: str = Field(
        ...,
        description="Survie probable / Décès probable"
    )
    risk_level: str = Field(
        ...,
        description="Faible / Modéré / Élevé"
    )
