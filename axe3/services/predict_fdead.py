import joblib
import pandas as pd
from pathlib import Path
from axe3.schemas import Axe3FdeadInput, Axe3FdeadOutput

# ─────────────────────────────────────────────────────────────────────────────
# Chargement du modèle au démarrage (module level — même pattern qu'Axe 1)
# Pipeline : SMOTE → LogisticRegression
# À l'inférence : on appelle directement named_steps["model"]
# car SMOTE n'intervient qu'au training
# ─────────────────────────────────────────────────────────────────────────────

MODEL_PATH = Path(__file__).parent.parent / "models" / "best_model_fdead_artifact.pkl"

_bundle    = joblib.load(MODEL_PATH)
_pipeline  = _bundle["pipeline"]
_threshold = _bundle["threshold"]   # 0.25
_features  = _bundle["features"]    # 20 colonnes OHE exactes attendues par le modèle
_model     = _pipeline.named_steps["model"]

# Mapping conscience → valeur numérique (tel qu'encodé à l'entraînement)
_RCONSC_MAP = {"F": 0, "D": 1, "U": 2}


# ─────────────────────────────────────────────────────────────────────────────
# Feature builder : reconstruit le vecteur OHE à partir des 10 inputs bruts
# Ordre des colonnes imposé par _features (liste extraite du pkl)
# ─────────────────────────────────────────────────────────────────────────────

def _build_feature_vector(d: dict) -> pd.DataFrame:
    row = {
        # ── Numériques ────────────────────────────────────────────────────────
        "num__AGE"        : d["AGE"],
        "num__RSBP"       : d["RSBP"],
        "num__RDELAY"     : d["RDELAY"],
        "num__RDEF_SCORE" : d["RDEF_SCORE"],
        "num__RCONSC_NUM" : _RCONSC_MAP[d["RCONSC"]],

        # ── SEX (OHE) ─────────────────────────────────────────────────────────
        "cat__SEX_F"      : 1 if d["SEX"] == "F" else 0,
        "cat__SEX_M"      : 1 if d["SEX"] == "M" else 0,

        # ── RATRIAL (OHE) ─────────────────────────────────────────────────────
        "cat__RATRIAL_N"  : 1 if d["RATRIAL"] == "N" else 0,
        "cat__RATRIAL_Y"  : 1 if d["RATRIAL"] == "Y" else 0,

        # ── STYPE (OHE) ───────────────────────────────────────────────────────
        "cat__STYPE_LACS" : 1 if d["STYPE"] == "LACS" else 0,
        "cat__STYPE_OTH"  : 1 if d["STYPE"] == "OTH"  else 0,
        "cat__STYPE_PACS" : 1 if d["STYPE"] == "PACS" else 0,
        "cat__STYPE_POCS" : 1 if d["STYPE"] == "POCS" else 0,
        "cat__STYPE_TACS" : 1 if d["STYPE"] == "TACS" else 0,

        # ── RXASP (OHE) ───────────────────────────────────────────────────────
        "cat__RXASP_N"    : 1 if d["RXASP"] == "N" else 0,
        "cat__RXASP_Y"    : 1 if d["RXASP"] == "Y" else 0,

        # ── RXHEP (OHE) ───────────────────────────────────────────────────────
        "cat__RXHEP_H"    : 1 if d["RXHEP"] == "H" else 0,
        "cat__RXHEP_L"    : 1 if d["RXHEP"] == "L" else 0,
        "cat__RXHEP_M"    : 1 if d["RXHEP"] == "M" else 0,
        "cat__RXHEP_N"    : 1 if d["RXHEP"] == "N" else 0,
    }
    # Réordonne selon l'ordre exact du training
    return pd.DataFrame([row])[_features]


def _risk_level(prob: float) -> str:
    if prob < 0.30:
        return "Faible"
    elif prob < 0.55:
        return "Modéré"
    else:
        return "Élevé"


# ─────────────────────────────────────────────────────────────────────────────
# Fonction de prédiction principale
# ─────────────────────────────────────────────────────────────────────────────

def predict_fdead(data: Axe3FdeadInput) -> Axe3FdeadOutput:
    raw        = data.model_dump()
    X          = _build_feature_vector(raw)
    proba      = float(_model.predict_proba(X)[0][1])
    prediction = int(proba >= _threshold)

    return Axe3FdeadOutput(
        probability=round(proba, 4),
        prediction=prediction,
        threshold=_threshold,
        verdict="Décès probable" if prediction == 1 else "Survie probable",
        risk_level=_risk_level(proba),
    )
