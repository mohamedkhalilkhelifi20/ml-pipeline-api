import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from axe2.schemas import Axe2Input, Axe2Output

# ─────────────────────────────────────────────────────────────────────────────
# Chargement du modèle au démarrage (module level — même pattern qu'Axe 1/3)
# Modèle : CalibratedClassifierCV (Platt scaling sur LogisticRegression)
# Multiclasse : 0=léger, 1=modéré, 2=sévère
# Logique seuil : si P(sévère) >= 0.30 → sévère, sinon argmax
# ─────────────────────────────────────────────────────────────────────────────

MODEL_PATH = Path(__file__).parent.parent / "models" / "pipeline_final.pkl"


# ─────────────────────────────────────────────────────────────────────────────
# Patch de compatibilité sklearn 1.6.1 → 1.8.0
# SimpleImputer a renommé _fill_dtype en _fit_dtype entre ces versions.
# On parcourt récursivement tous les estimateurs du bundle pour corriger
# l'attribut manquant avant le premier appel à predict_proba.
# ─────────────────────────────────────────────────────────────────────────────

def _patch_simple_imputers(obj, visited=None):
    """Patch récursif : ajoute _fill_dtype si absent sur tout SimpleImputer."""
    from sklearn.impute import SimpleImputer
    if visited is None:
        visited = set()
    obj_id = id(obj)
    if obj_id in visited:
        return
    visited.add(obj_id)

    if isinstance(obj, SimpleImputer):
        if not hasattr(obj, "_fill_dtype") and hasattr(obj, "_fit_dtype"):
            obj._fill_dtype = obj._fit_dtype
        elif not hasattr(obj, "_fill_dtype"):
            obj._fill_dtype = None

    # Parcourt les sous-estimateurs
    for attr in ("estimators_", "calibrated_classifiers_", "estimator",
                 "base_estimator", "steps", "named_steps"):
        child = getattr(obj, attr, None)
        if child is None:
            continue
        if isinstance(child, list):
            for item in child:
                _patch_simple_imputers(item, visited)
        elif isinstance(child, dict):
            for item in child.values():
                _patch_simple_imputers(item, visited)
        elif hasattr(child, "__dict__"):
            _patch_simple_imputers(child, visited)

    # Pipeline : itère sur les steps
    if hasattr(obj, "steps"):
        for _, step in obj.steps:
            _patch_simple_imputers(step, visited)


_bundle      = joblib.load(MODEL_PATH)
_model       = _bundle["model"]
_patch_simple_imputers(_model)  # ← appliqué une seule fois au chargement
_threshold   = _bundle["threshold"]     # 0.30
_features    = _bundle["features"]      # 41 colonnes OHE
_severe_cl   = _bundle["severe_class"]  # 2
_label_map   = _bundle["label_map"]     # {0: 'leger', 1: 'modere', 2: 'severe'}

_SEVERITY_FR = {"leger": "Léger", "modere": "Modéré", "severe": "Sévère"}


# ─────────────────────────────────────────────────────────────────────────────
# Feature builder : reconstruit les 41 colonnes OHE depuis les inputs bruts
#
# Logique RDEF (encodage IST) :
#   "Y" → RDEF_v2=1, RDEF_uncertain=0  (déficit confirmé)
#   "N" → RDEF_v2=0, RDEF_uncertain=0  (absent)
#   "C" → RDEF_v2=0, RDEF_uncertain=1  (cannot assess)
#
# Features calculées :
#   n_deficits_confirmed = somme des RDEF_v2
#   n_deficits_uncertain = somme des RDEF_uncertain
#   deficit_ratio        = n_confirmed / (n_confirmed + n_uncertain + ε)
# ─────────────────────────────────────────────────────────────────────────────

def _encode_rdef(val: str) -> tuple[int, int]:
    """Retourne (rdef_v2, rdef_uncertain) selon le statut IST."""
    if val == "Y":
        return 1, 0
    elif val == "C":
        return 0, 1
    else:  # "N"
        return 0, 0


def _build_feature_vector(d: dict) -> tuple[pd.DataFrame, dict]:
    rdef_keys = ["RDEF1", "RDEF2", "RDEF3", "RDEF4", "RDEF5", "RDEF6", "RDEF7", "RDEF8"]

    rdef_v2        = []
    rdef_uncertain = []
    for key in rdef_keys:
        v2, unc = _encode_rdef(d[key])
        rdef_v2.append(v2)
        rdef_uncertain.append(unc)

    n_confirmed = sum(rdef_v2)
    n_uncertain = sum(rdef_uncertain)
    ratio       = n_confirmed / (n_confirmed + n_uncertain + 1e-6)

    stype = d["STYPE"]

    row = {
        # ── Numériques ────────────────────────────────────────────────────────
        "num__RDELAY"               : d["RDELAY"],
        "num__AGE"                  : d["AGE"],
        "num__RSBP"                 : d["RSBP"],
        # RDEF confirmés
        **{f"num__RDEF{i+1}_v2"         : rdef_v2[i]        for i in range(8)},
        # RDEF incertains
        **{f"num__RDEF{i+1}_uncertain"  : rdef_uncertain[i] for i in range(8)},
        # Features calculées
        "num__n_deficits_confirmed" : n_confirmed,
        "num__n_deficits_uncertain" : n_uncertain,
        "num__deficit_ratio"        : ratio,

        # ── SEX (OHE) ─────────────────────────────────────────────────────────
        "cat__SEX_F"     : 1 if d["SEX"] == "F" else 0,
        "cat__SEX_M"     : 1 if d["SEX"] == "M" else 0,

        # ── RSLEEP (OHE) ──────────────────────────────────────────────────────
        "cat__RSLEEP_N"  : 1 if d["RSLEEP"] == "N" else 0,
        "cat__RSLEEP_Y"  : 1 if d["RSLEEP"] == "Y" else 0,

        # ── RATRIAL (OHE) ─────────────────────────────────────────────────────
        "cat__RATRIAL_N" : 1 if d["RATRIAL"] == "N" else 0,
        "cat__RATRIAL_Y" : 1 if d["RATRIAL"] == "Y" else 0,

        # ── RCT (OHE) ─────────────────────────────────────────────────────────
        "cat__RCT_N"     : 1 if d["RCT"] == "N" else 0,
        "cat__RCT_Y"     : 1 if d["RCT"] == "Y" else 0,

        # ── RVISINF (OHE) ─────────────────────────────────────────────────────
        "cat__RVISINF_N" : 1 if d["RVISINF"] == "N" else 0,
        "cat__RVISINF_Y" : 1 if d["RVISINF"] == "Y" else 0,

        # ── RHEP24 (OHE) ──────────────────────────────────────────────────────
        "cat__RHEP24_N"  : 1 if d["RHEP24"] == "N" else 0,
        "cat__RHEP24_Y"  : 1 if d["RHEP24"] == "Y" else 0,

        # ── RASP3 (OHE) ───────────────────────────────────────────────────────
        "cat__RASP3_N"   : 1 if d["RASP3"] == "N" else 0,
        "cat__RASP3_Y"   : 1 if d["RASP3"] == "Y" else 0,

        # ── STYPE (OHE) ───────────────────────────────────────────────────────
        "cat__STYPE_LACS": 1 if stype == "LACS" else 0,
        "cat__STYPE_OTH" : 1 if stype == "OTH"  else 0,
        "cat__STYPE_PACS": 1 if stype == "PACS" else 0,
        "cat__STYPE_POCS": 1 if stype == "POCS" else 0,
        "cat__STYPE_TACS": 1 if stype == "TACS" else 0,
    }

    deficit_summary = {
        "n_confirmed"  : n_confirmed,
        "n_uncertain"  : n_uncertain,
        "deficit_ratio": round(ratio, 4),
    }

    return pd.DataFrame([row])[_features], deficit_summary


# ─────────────────────────────────────────────────────────────────────────────
# Logique de décision multiclasse avec seuil prioritaire sur la classe sévère
# ─────────────────────────────────────────────────────────────────────────────

def _decide(probas: np.ndarray) -> int:
    """
    Si P(sévère) >= threshold → sévère (recall_severe prioritaire).
    Sinon → argmax sur toutes les classes.
    """
    if probas[_severe_cl] >= _threshold:
        return _severe_cl
    return int(np.argmax(probas))


# ─────────────────────────────────────────────────────────────────────────────
# Fonction de prédiction principale
# ─────────────────────────────────────────────────────────────────────────────

def predict_axe2(data: Axe2Input) -> Axe2Output:
    raw               = data.model_dump()
    X, deficit_summary = _build_feature_vector(raw)
    probas            = _model.predict_proba(X)[0]
    prediction        = _decide(probas)
    severity          = _label_map[prediction]

    return Axe2Output(
        severity=severity,
        severity_label=_SEVERITY_FR[severity],
        prediction=prediction,
        probability_severe=round(float(probas[2]), 4),
        probability_modere=round(float(probas[1]), 4),
        probability_leger =round(float(probas[0]), 4),
        threshold=_threshold,
        deficit_summary=deficit_summary,
    )
