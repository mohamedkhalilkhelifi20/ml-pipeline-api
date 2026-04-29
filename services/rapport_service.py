# =============================================================================
# rapport/rapport_service.py — Génération de rapport IA via Ollama (phi3:mini)
# StrokeAI | Axe 1 (NHANES) + Axe 2 + Axe 3 (IST)
# Ollama local : http://localhost:11434
# Modèle : phi3:mini — Microsoft, optimisé raisonnement structuré
# =============================================================================

import json
import httpx
from typing import AsyncGenerator

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:mini"

# -----------------------------------------------------------------------------
# System prompt — injecté dans chaque requête
# -----------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es un médecin neurologue expert en AVC (accidents vasculaires cérébraux).
Tu rédiges des rapports médicaux UNIQUEMENT en français.
Tu suis TOUJOURS exactement le format demandé avec les numéros de sections.
Tu ne génères JAMAIS de contenu hors du format imposé.
Tu es précis, professionnel, et concis (max 300 mots par rapport)."""

# -----------------------------------------------------------------------------
# Helper streaming
# -----------------------------------------------------------------------------

async def _stream_ollama(prompt: str) -> AsyncGenerator[str, None]:
    payload = {
        "model": OLLAMA_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.2,      # très bas = cohérence maximale
            "num_predict": 800,      # suffisant pour 4 sections
            "top_p": 0.9,
            "repeat_penalty": 1.1,  # évite les répétitions
        },
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream("POST", OLLAMA_URL, json=payload) as response:
            if response.status_code != 200:
                raise ValueError(
                    f"Ollama inaccessible (code {response.status_code}). "
                    f"Lance 'ollama serve' dans un terminal."
                )
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        text = data.get("response", "")
                        if text:
                            yield text
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue


# -----------------------------------------------------------------------------
# Prompt Axe 1 — Risque AVC (NHANES)
# -----------------------------------------------------------------------------

def _prompt_axe1(patient: dict, prediction: dict) -> str:
    genre      = "Masculin" if patient.get("gender") == 1 else "Féminin"
    age_map    = {1: "20–39 ans", 2: "40–59 ans", 3: "60 ans et plus"}
    age        = age_map.get(patient.get("age"), "Non renseigné")
    proba      = prediction.get("probabilite", 0) * 100
    verdict    = prediction.get("verdict", "Non disponible")
    threshold  = prediction.get("threshold", 0.25)

    # Niveau de risque lisible
    if proba >= 70:
        niveau = "ÉLEVÉ"
    elif proba >= 40:
        niveau = "MODÉRÉ"
    else:
        niveau = "FAIBLE"

    # Facteurs de risque présents
    facteurs = []
    if patient.get("hypertension") == 1:      facteurs.append("hypertension artérielle")
    if patient.get("diabetes") == 1:           facteurs.append("diabète")
    if patient.get("high cholesterol") == 1:   facteurs.append("hypercholestérolémie")
    if patient.get("Coronary Heart Disease") == 1: facteurs.append("maladie coronarienne")
    if patient.get("smoke") == 1:              facteurs.append("tabagisme actif")
    if patient.get("alcohol") == 1:            facteurs.append("consommation d'alcool")
    if patient.get("age", 0) == 3:             facteurs.append("âge ≥ 60 ans")
    facteurs_str = ", ".join(facteurs) if facteurs else "aucun facteur majeur identifié"

    sbp = patient.get("systolic blood pressure", "N/A")
    glucose = patient.get("fasting glucose", "N/A")
    hba1c = patient.get("glycohemoglobin", "N/A")
    ldl = patient.get("LDL", "N/A")
    hdl = patient.get("HDL", "N/A")

    return f"""Rédige un rapport médical AVC pour ce patient. Suis EXACTEMENT ce format :

## DONNÉES PATIENT
- Genre : {genre} | Âge : {age}
- Pression systolique : {sbp} mmHg
- Glycémie à jeun : {glucose} mg/dL | HbA1c : {hba1c}%
- LDL : {ldl} mg/dL | HDL : {hdl} mg/dL
- Facteurs de risque présents : {facteurs_str}

## RÉSULTAT MODÈLE ML (LightGBM — Dataset NHANES 4603 patients)
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


# -----------------------------------------------------------------------------
# Prompt Axe 2 — Sévérité AVC (IST)
# -----------------------------------------------------------------------------

def _prompt_axe2(patient: dict, prediction: dict) -> str:
    rconsc_map = {
        "F": "Alerte — Fully conscious",
        "D": "Somnolent — Drowsy",
        "U": "Inconscient — Unconscious"
    }
    stype_map = {
        "PACS": "Partial Anterior Circulation Stroke (PACS)",
        "LACS": "Lacunar Stroke (LACS)",
        "TACS": "Total Anterior Circulation Stroke (TACS)",
        "POCS": "Posterior Circulation Stroke (POCS)",
    }

    rconsc     = rconsc_map.get(patient.get("RCONSC", ""), "Non renseigné")
    stype      = stype_map.get(patient.get("STYPE", ""), patient.get("STYPE", "Non renseigné"))
    severite   = prediction.get("severite", "N/A").upper()
    probas     = prediction.get("probabilites", {})
    age        = patient.get("AGE", "N/A")
    genre      = "Masculin" if patient.get("SEX") == "M" else "Féminin"
    rsbp       = patient.get("RSBP", "N/A")
    rdef       = patient.get("RDEF_SCORE", "N/A")
    ratrial    = "Oui" if patient.get("RATRIAL") == "Y" else "Non"
    rdelay     = patient.get("RDELAY", "N/A")

    return f"""Rédige un rapport médical de sévérité AVC. Suis EXACTEMENT ce format :

## DONNÉES PATIENT (IST Edinburgh — 19 435 patients)
- Genre : {genre} | Âge : {age} ans
- État de conscience à l'admission : {rconsc}
- Type d'AVC (STYPE) : {stype}
- Pression systolique : {rsbp} mmHg
- Fibrillation auriculaire : {ratrial}
- Délai prise en charge : {rdelay}h
- Score déficits neurologiques RDEF : {rdef}/8

## RÉSULTAT MODÈLE ML (Régression Logistique Calibrée)
- Sévérité prédite : {severite}
- Probabilités → Léger : {probas.get("leger", 0)*100:.1f}% | Modéré : {probas.get("modere", 0)*100:.1f}% | Sévère : {probas.get("severe", 0)*100:.1f}%

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


# -----------------------------------------------------------------------------
# Prompt Axe 3 — Mortalité post-AVC (IST)
# -----------------------------------------------------------------------------

def _prompt_axe3(patient: dict, prediction: dict) -> str:
    rconsc_map = {"F": "Alerte", "D": "Somnolent", "U": "Inconscient"}
    stype_map  = {
        "PACS": "Partial Anterior (PACS)",
        "LACS": "Lacunar (LACS)",
        "TACS": "Total Anterior (TACS) — forme la plus sévère",
        "POCS": "Posterior (POCS)",
    }

    ddead   = prediction.get("ddead", {})
    fdead   = prediction.get("fdead", {})
    rconsc  = rconsc_map.get(patient.get("RCONSC", ""), "Non renseigné")
    stype   = stype_map.get(patient.get("STYPE", ""), patient.get("STYPE", "N/A"))

    p_ddead = ddead.get("probabilite", 0) * 100
    p_fdead = fdead.get("probabilite", 0) * 100
    v_ddead = ddead.get("verdict", "N/A")
    v_fdead = fdead.get("verdict", "N/A")

    # Niveau de risque global
    risque_global = "CRITIQUE" if p_ddead >= 50 or p_fdead >= 60 else \
                    "ÉLEVÉ" if p_ddead >= 30 or p_fdead >= 40 else "MODÉRÉ"

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
- Mortalité 14 jours (DDEAD) : {p_ddead:.1f}% → {v_ddead}
- Mortalité 6 mois (FDEAD)   : {p_fdead:.1f}% → {v_fdead}
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


# -----------------------------------------------------------------------------
# API publique
# -----------------------------------------------------------------------------

async def generer_rapport_axe1(
    patient: dict, prediction: dict
) -> AsyncGenerator[str, None]:
    async for chunk in _stream_ollama(_prompt_axe1(patient, prediction)):
        yield chunk


async def generer_rapport_axe2(
    patient: dict, prediction: dict
) -> AsyncGenerator[str, None]:
    async for chunk in _stream_ollama(_prompt_axe2(patient, prediction)):
        yield chunk


async def generer_rapport_axe3(
    patient: dict, prediction: dict
) -> AsyncGenerator[str, None]:
    async for chunk in _stream_ollama(_prompt_axe3(patient, prediction)):
        yield chunk