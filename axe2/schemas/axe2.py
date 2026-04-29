from pydantic import BaseModel, Field
from typing import Literal


# ─────────────────────────────────────────────────────────────────────────────
# INPUT — Variables cliniques IST pour la sévérité de l'AVC (Axe 2)
# 41 features reconstruites dans le service à partir des inputs bruts
#
# Logique RDEF : chaque déficit neurologique a 3 états IST :
#   "Y" = présent (confirmé)    → RDEF_v2=1, RDEF_uncertain=0
#   "N" = absent                → RDEF_v2=0, RDEF_uncertain=0
#   "C" = cannot assess         → RDEF_v2=0, RDEF_uncertain=1
# ─────────────────────────────────────────────────────────────────────────────

class Axe2Input(BaseModel):

    # ── Démographie & admission ───────────────────────────────────────────────
    AGE: float = Field(
        ..., ge=16, le=99,
        description="Âge du patient en années (16–99)"
    )
    SEX: Literal["M", "F"] = Field(
        ...,
        description="Sexe : M=Homme, F=Femme"
    )
    RSBP: float = Field(
        ..., ge=60, le=300,
        description="Tension artérielle systolique à l'admission (mmHg)"
    )
    RDELAY: float = Field(
        ..., ge=0, le=48,
        description="Délai entre AVC et admission (heures)"
    )

    # ── Déficits neurologiques RDEF1–RDEF8 ───────────────────────────────────
    # Y=présent, N=absent, C=cannot assess (incertain)
    RDEF1: Literal["Y", "N", "C"] = Field(
        ..., description="Paralysie faciale : Y=Oui, N=Non, C=Incertain"
    )
    RDEF2: Literal["Y", "N", "C"] = Field(
        ..., description="Faiblesse bras : Y=Oui, N=Non, C=Incertain"
    )
    RDEF3: Literal["Y", "N", "C"] = Field(
        ..., description="Faiblesse jambe : Y=Oui, N=Non, C=Incertain"
    )
    RDEF4: Literal["Y", "N", "C"] = Field(
        ..., description="Dysphasie (trouble langage) : Y=Oui, N=Non, C=Incertain"
    )
    RDEF5: Literal["Y", "N", "C"] = Field(
        ..., description="Hémianopsie (trouble vision) : Y=Oui, N=Non, C=Incertain"
    )
    RDEF6: Literal["Y", "N", "C"] = Field(
        ..., description="Trouble déglutition : Y=Oui, N=Non, C=Incertain"
    )
    RDEF7: Literal["Y", "N", "C"] = Field(
        ..., description="Trouble conscience : Y=Oui, N=Non, C=Incertain"
    )
    RDEF8: Literal["Y", "N", "C"] = Field(
        ..., description="Autre déficit neurologique : Y=Oui, N=Non, C=Incertain"
    )

    # ── Variables cliniques additionnelles ────────────────────────────────────
    STYPE: Literal["LACS", "PACS", "TACS", "POCS", "OTH"] = Field(
        ...,
        description=(
            "Type d'AVC : LACS=Lacunar (24%), PACS=Partial Anterior (40.4%), "
            "TACS=Total Anterior (23.9%), POCS=Posterior (11.5%), OTH=Autre"
        )
    )
    RSLEEP: Literal["Y", "N"] = Field(
        ...,
        description="AVC survenu pendant le sommeil : Y=Oui, N=Non"
    )
    RATRIAL: Literal["Y", "N"] = Field(
        ...,
        description="Fibrillation auriculaire : Y=Oui, N=Non"
    )
    RCT: Literal["Y", "N"] = Field(
        ...,
        description="Scanner cérébral réalisé : Y=Oui, N=Non"
    )
    RVISINF: Literal["Y", "N"] = Field(
        ...,
        description="Infarctus visible au scanner : Y=Oui, N=Non"
    )
    RHEP24: Literal["Y", "N"] = Field(
        ...,
        description="Héparine dans les 24h avant randomisation : Y=Oui, N=Non"
    )
    RASP3: Literal["Y", "N"] = Field(
        ...,
        description="Aspirine dans les 3j avant randomisation : Y=Oui, N=Non"
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "AGE": 72, "SEX": "M", "RSBP": 170, "RDELAY": 4.0,
                "RDEF1": "Y", "RDEF2": "Y", "RDEF3": "Y",
                "RDEF4": "Y", "RDEF5": "Y", "RDEF6": "Y",
                "RDEF7": "N", "RDEF8": "C",
                "STYPE": "TACS", "RSLEEP": "N", "RATRIAL": "Y",
                "RCT": "Y", "RVISINF": "Y", "RHEP24": "N", "RASP3": "N"
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT — même structure qu'Axe1Output + champs spécifiques multiclasse
# ─────────────────────────────────────────────────────────────────────────────

class Axe2Output(BaseModel):
    severity: str = Field(
        ...,
        description="Classe prédite : leger / modere / severe"
    )
    severity_label: str = Field(
        ...,
        description="Label lisible : Léger / Modéré / Sévère"
    )
    prediction: int = Field(
        ...,
        description="Classe numérique : 0=léger, 1=modéré, 2=sévère"
    )
    probability_severe: float = Field(
        ...,
        description="Probabilité classe sévère (seuil prioritaire = 0.30)"
    )
    probability_modere: float = Field(
        ...,
        description="Probabilité classe modérée"
    )
    probability_leger: float = Field(
        ...,
        description="Probabilité classe légère"
    )
    threshold: float = Field(
        ...,
        description="Seuil de décision pour la classe sévère"
    )
    deficit_summary: dict = Field(
        ...,
        description="Résumé : n_confirmed, n_uncertain, deficit_ratio"
    )
