# =============================================================================
# services/rapport_service.py — Génération rapport IA via OpenRouter
# StrokeAI | Axe 1 (NHANES) + Axe 2 + Axe 3 (IST)
# OpenRouter : https://openrouter.ai/api/v1
# =============================================================================

import os
import json
import httpx
from typing import AsyncGenerator

# ── Configuration ─────────────────────────────────────────────────────────────

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = (
    "Tu es un médecin neurologue expert en AVC (accidents vasculaires cérébraux). "
    "Tu rédiges des rapports médicaux UNIQUEMENT en français. "
    "Tu suis TOUJOURS exactement le format demandé avec les numéros de sections. "
    "Tu ne génères JAMAIS de contenu hors du format imposé. "
    "Tu es précis, professionnel, et concis (max 300 mots par rapport)."
)


# ── Streaming helper ───────────────────────────────────────────────────────────

async def _stream_openrouter(prompt: str) -> AsyncGenerator[str, None]:
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY non définie. "
            "Ajoutez-la dans le fichier .env du backend."
        )

    headers = {
        "Authorization":  f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":   "application/json",
        "HTTP-Referer":   "http://localhost:3000",
        "X-Title":        "StrokeAI",
    }

    payload = {
        "model":  OPENROUTER_MODEL,
        "stream": True,
        "messages": [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens":  900,
        "top_p":       0.9,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", OPENROUTER_URL, headers=headers, json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise ValueError(
                    f"OpenRouter error {response.status_code}: {body.decode()[:300]}"
                )
            async for raw_line in response.aiter_lines():
                line = raw_line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj   = json.loads(data)
                    delta = obj.get("choices", [{}])[0].get("delta", {})
                    text  = delta.get("content") or ""
                    if text:
                        yield text
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue


# ── Prompts ────────────────────────────────────────────────────────────────────

def _prompt_axe1(patient: dict, prediction: dict) -> str:
    genre     = "Masculin" if patient.get("gender") == 1 else "Féminin"
    age_map   = {1: "20–39 ans", 2: "40–59 ans", 3: "60 ans et plus"}
    age       = age_map.get(patient.get("age"), "Non renseigné")
    proba     = prediction.get("probability", 0) * 100
    verdict   = prediction.get("verdict", "Non disponible")
    threshold = prediction.get("threshold", 0.25)

    niveau = "ÉLEVÉ" if proba >= 70 else "MODÉRÉ" if proba >= 40 else "FAIBLE"

    facteurs = []
    if patient.get("hypertension") == 1:            facteurs.append("hypertension artérielle")
    if patient.get("diabetes") == 1:                 facteurs.append("diabète")
    if patient.get("high cholesterol") == 1:         facteurs.append("hypercholestérolémie")
    if patient.get("Coronary Heart Disease") == 1:   facteurs.append("maladie coronarienne")
    if patient.get("smoke") == 1:                    facteurs.append("tabagisme actif")
    if patient.get("alcohol") == 1:                  facteurs.append("consommation d'alcool")
    if patient.get("age", 0) == 3:                   facteurs.append("âge ≥ 60 ans")
    facteurs_str = ", ".join(facteurs) if facteurs else "aucun facteur majeur identifié"

    sbp     = patient.get("Systolic blood pressure", patient.get("systolic blood pressure", "N/A"))
    glucose = patient.get("Fasting Glucose", patient.get("fasting glucose", "N/A"))
    ldl     = patient.get("Low-density lipoprotein", "N/A")

    return f"""Rédige un rapport médical AVC pour ce patient. Suis EXACTEMENT ce format :

## DONNÉES PATIENT
- Genre : {genre} | Âge : {age}
- Pression systolique : {sbp} mmHg
- Glycémie à jeun : {glucose} mg/dL
- LDL : {ldl} mg/dL
- Facteurs de risque présents : {facteurs_str}

## RÉSULTAT MODÈLE ML (LightGBM — Dataset NHANES)
- Probabilité AVC : {proba:.1f}% | Niveau : {niveau}
- Verdict : {verdict} | Seuil décision : {threshold}

## FORMAT DE RÉPONSE OBLIGATOIRE (respecte exactement ces 4 sections) :

**1. SYNTHÈSE DU RISQUE**
[2 phrases maximum : niveau de risque, probabilité, signification clinique]

**2. FACTEURS DE RISQUE IDENTIFIÉS**
[Liste à puces des facteurs présents chez ce patient avec leur impact sur le risque AVC]

**3. RECOMMANDATIONS CLINIQUES**
[4 recommandations concrètes et personnalisées numérotées]

**4. AVERTISSEMENT**
Ce rapport est généré par un modèle d'intelligence artificielle (LightGBM entraîné sur le dataset NHANES). Il constitue uniquement un outil d'aide à la décision clinique et ne remplace en aucun cas le jugement du médecin ni un diagnostic médical officiel.
"""


def _prompt_axe2(patient: dict, prediction: dict) -> str:
    stype_map = {
        "PACS": "Partial Anterior Circulation Stroke (PACS)",
        "LACS": "Lacunar Stroke (LACS)",
        "TACS": "Total Anterior Circulation Stroke (TACS)",
        "POCS": "Posterior Circulation Stroke (POCS)",
        "OTH":  "Autre (OTH)",
    }
    rconsc_map = {
        "F": "Alerte (Fully conscious)",
        "D": "Somnolent (Drowsy)",
        "U": "Inconscient (Unconscious)",
    }

    severite   = prediction.get("severity_label", prediction.get("severity", "N/A"))
    p_severe   = prediction.get("probability_severe", 0) * 100
    p_modere   = prediction.get("probability_modere", 0) * 100
    p_leger    = prediction.get("probability_leger",  0) * 100
    age        = patient.get("AGE", "N/A")
    genre      = "Masculin" if patient.get("SEX") == "M" else "Féminin"
    rsbp       = patient.get("RSBP", "N/A")
    rconsc     = rconsc_map.get(patient.get("RCONSC", ""), "Non renseigné")
    stype      = stype_map.get(patient.get("STYPE", ""), patient.get("STYPE", "N/A"))
    ratrial    = "Oui" if patient.get("RATRIAL") == "Y" else "Non"
    rdelay     = patient.get("RDELAY", "N/A")

    # Nombre de déficits confirmés
    deficits = [k for k in ("RDEF1","RDEF2","RDEF3","RDEF4","RDEF5","RDEF6","RDEF7","RDEF8")
                if patient.get(k) == "Y"]
    rdef_str = f"{len(deficits)}/8 déficits confirmés" if deficits else "Aucun déficit confirmé"

    return f"""Rédige un rapport médical de sévérité AVC. Suis EXACTEMENT ce format :

## DONNÉES PATIENT (IST Edinburgh — 19 435 patients)
- Genre : {genre} | Âge : {age} ans
- État de conscience à l'admission : {rconsc}
- Type d'AVC (STYPE) : {stype}
- Pression systolique : {rsbp} mmHg
- Fibrillation auriculaire : {ratrial}
- Délai prise en charge : {rdelay}h
- Déficits neurologiques : {rdef_str}

## RÉSULTAT MODÈLE ML (Régression Logistique Calibrée — IST)
- Sévérité prédite : {severite.upper()}
- Probabilités → Léger : {p_leger:.1f}% | Modéré : {p_modere:.1f}% | Sévère : {p_severe:.1f}%

## FORMAT DE RÉPONSE OBLIGATOIRE :

**1. PROFIL DE SÉVÉRITÉ**
[2 phrases : sévérité prédite et implications immédiates pour la prise en charge]

**2. ÉLÉMENTS CLINIQUES CONTRIBUTIFS**
[Liste à puces des facteurs ayant contribué à ce niveau de sévérité]

**3. ORIENTATIONS THÉRAPEUTIQUES**
[4 recommandations de prise en charge adaptées à ce niveau de sévérité]

**4. AVERTISSEMENT**
Ce rapport est généré par un modèle d'intelligence artificielle entraîné sur le dataset IST Edinburgh. Il constitue uniquement un outil d'aide à la décision clinique et ne remplace pas le jugement du médecin ni un diagnostic médical officiel.
"""


def _prompt_axe3(patient: dict, prediction: dict) -> str:
    rconsc_map = {"F": "Alerte", "D": "Somnolent", "U": "Inconscient"}
    stype_map  = {
        "PACS": "Partial Anterior (PACS)",
        "LACS": "Lacunar (LACS)",
        "TACS": "Total Anterior (TACS) — forme la plus sévère",
        "POCS": "Posterior (POCS)",
        "OTH":  "Autre",
    }

    ddead   = prediction.get("ddead", {})
    fdead   = prediction.get("fdead", {})
    rconsc  = rconsc_map.get(patient.get("RCONSC", ""), "Non renseigné")
    stype   = stype_map.get(patient.get("STYPE", ""), patient.get("STYPE", "N/A"))

    p_ddead  = ddead.get("probability", 0) * 100
    p_fdead  = fdead.get("probability", 0) * 100
    v_ddead  = ddead.get("verdict", "N/A")
    v_fdead  = fdead.get("verdict", "N/A")
    rl_ddead = ddead.get("risk_level", "")
    rl_fdead = fdead.get("risk_level", "")

    risque_global = "CRITIQUE" if p_ddead >= 50 or p_fdead >= 60 else \
                    "ÉLEVÉ"    if p_ddead >= 30 or p_fdead >= 40 else "MODÉRÉ"

    return f"""Rédige un rapport pronostique de mortalité post-AVC. Suis EXACTEMENT ce format :

## DONNÉES PATIENT (IST Edinburgh)
- Âge : {patient.get("AGE", "N/A")} ans | Sexe : {"Masculin" if patient.get("SEX") == "M" else "Féminin"}
- État de conscience : {rconsc}
- Type d'AVC : {stype}
- Pression systolique : {patient.get("RSBP", "N/A")} mmHg
- Fibrillation auriculaire : {"Oui" if patient.get("RATRIAL") == "Y" else "Non"}
- Score déficits RDEF : {patient.get("RDEF_SCORE", "N/A")}/8
- Aspirine administrée : {"Oui" if patient.get("RXASP") == "Y" else "Non"}
- Héparine : {patient.get("RXHEP", "N/A")}

## RÉSULTATS MODÈLE ML (Régression Logistique — IST)
- Mortalité 14 jours (DDEAD) : {p_ddead:.1f}% → {v_ddead} ({rl_ddead})
- Mortalité 6 mois  (FDEAD)  : {p_fdead:.1f}% → {v_fdead} ({rl_fdead})
- Niveau de risque global    : {risque_global}

## FORMAT DE RÉPONSE OBLIGATOIRE :

**1. ÉVALUATION PRONOSTIQUE**
[2-3 phrases : risque de mortalité à court et moyen terme, signification clinique du niveau {risque_global}]

**2. FACTEURS PRONOSTIQUES DÉFAVORABLES**
[Liste à puces des éléments cliniques de ce patient contribuant au risque de mortalité]

**3. RECOMMANDATIONS DE SURVEILLANCE ET PRISE EN CHARGE**
[4 actions prioritaires concrètes adaptées au profil de ce patient]

**4. AVERTISSEMENT**
Ce rapport est généré par un modèle d'intelligence artificielle (Régression Logistique entraînée sur IST Edinburgh, 19 435 patients). Il constitue uniquement un outil d'aide à la décision clinique et ne remplace pas le jugement du médecin ni un diagnostic médical officiel.
"""


# ── API publique ───────────────────────────────────────────────────────────────

async def generer_rapport_axe1(patient: dict, prediction: dict) -> AsyncGenerator[str, None]:
    async for chunk in _stream_openrouter(_prompt_axe1(patient, prediction)):
        yield chunk


async def generer_rapport_axe2(patient: dict, prediction: dict) -> AsyncGenerator[str, None]:
    async for chunk in _stream_openrouter(_prompt_axe2(patient, prediction)):
        yield chunk


async def generer_rapport_axe3(patient: dict, prediction: dict) -> AsyncGenerator[str, None]:
    async for chunk in _stream_openrouter(_prompt_axe3(patient, prediction)):
        yield chunk
