import pickle
import pandas as pd
from pathlib import Path
from axe1.schemas.axe1 import Axe1Input, Axe1Output

MODEL_PATH = Path(__file__).parent.parent / "models" / "pipeline_final.pkl"

with open(MODEL_PATH, "rb") as f:
    _bundle = pickle.load(f)

_pipeline  = _bundle["pipeline"]
_threshold = _bundle["threshold"]
_features  = _bundle["features"]


def _engineer(d: dict) -> dict:
    return {
        "cardio_risk_score"   : d["hypertension"] + d["diabetes"] + d["high cholesterol"] + d["smoke"],
        "age_CHD"             : d["age"] * d["Coronary Heart Disease"],
        "pulse_pressure"      : d["Systolic blood pressure"] - d["Diastolic blood pressure"],
        "depression_insurance": d["depression"] * d["Health Insurance"],
        "fat_ratio"           : d["Total saturated fatty acids"] / (d["Total polyunsaturated fatty acids"] + 1e-6),
        "fiber_cholesterol"   : d["Dietary fiber"] * d["high cholesterol"],
        "smoke_hypertension"  : d["smoke"] * d["hypertension"],
        "smoke_diabetes"      : d["smoke"] * d["diabetes"],
    }


def predict_stroke(data: Axe1Input) -> Axe1Output:
    raw        = data.model_dump(by_alias=True)
    engineered = _engineer(raw)
    df         = pd.DataFrame([{**raw, **engineered}])[_features]
    proba      = float(_pipeline.predict_proba(df)[0][1])
    prediction = int(proba >= _threshold)

    return Axe1Output(
        probability=round(proba, 4),
        prediction=prediction,
        threshold=_threshold,
        verdict="Risque élevé" if prediction == 1 else "Faible risque",
        engineered_features={k: round(float(v), 4) for k, v in engineered.items()},
    )
