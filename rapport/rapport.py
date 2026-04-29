# =============================================================================
# rapport/rapport.py — Endpoints rapport IA + sauvegarde automatique MongoDB
# StrokeAI — Streaming SSE pour les 3 axes
# =============================================================================

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional
from services.rapport_service import (
    generer_rapport_axe1,
    generer_rapport_axe2,
    generer_rapport_axe3,
)
from services.history_service import save_rapport

router = APIRouter(prefix="/rapport", tags=["Rapport IA — phi3:mini"])


# -----------------------------------------------------------------------------
# Schema d'entrée
# -----------------------------------------------------------------------------

class RapportRequest(BaseModel):
    patient:        dict[str, Any]
    prediction:     dict[str, Any]
    patient_nom:    Optional[str] = "Inconnu"
    patient_prenom: Optional[str] = "Inconnu"
    medecin_nom:    Optional[str] = None


# -----------------------------------------------------------------------------
# Helper SSE — encode chaque chunk en JSON pour éviter les problèmes de \n
# -----------------------------------------------------------------------------

async def _to_sse(generator, axe: int, body: RapportRequest):
    """
    Stream le rapport chunk par chunk en SSE.
    Accumule le texte complet puis sauvegarde en MongoDB à la fin.
    """
    rapport_complet = ""
    try:
        async for chunk in generator:
            rapport_complet += chunk
            data = json.dumps({"text": chunk}, ensure_ascii=False)
            yield f"data: {data}\n\n"

        # ── Sauvegarde MongoDB après fin du stream ────────────────────────
        try:
            rapport_id = await save_rapport(
                axe=axe,
                patient_nom=body.patient_nom or "Inconnu",
                patient_prenom=body.patient_prenom or "Inconnu",
                patient_data=body.patient,
                prediction=body.prediction,
                rapport_texte=rapport_complet,
                medecin_nom=body.medecin_nom,
            )
            # Envoie l'ID MongoDB au frontend
            meta = json.dumps({"saved": True, "rapport_id": rapport_id}, ensure_ascii=False)
            yield f"data: {meta}\n\n"
        except Exception as e:
            # Sauvegarde échouée — on log mais on ne bloque pas
            print(f"⚠️ Sauvegarde MongoDB échouée : {e}")

        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.post("/axe1")
async def rapport_axe1(body: RapportRequest):
    try:
        generator = generer_rapport_axe1(body.patient, body.prediction)
        return StreamingResponse(
            _to_sse(generator, axe=1, body=body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/axe2")
async def rapport_axe2(body: RapportRequest):
    try:
        generator = generer_rapport_axe2(body.patient, body.prediction)
        return StreamingResponse(
            _to_sse(generator, axe=2, body=body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/axe3")
async def rapport_axe3(body: RapportRequest):
    try:
        generator = generer_rapport_axe3(body.patient, body.prediction)
        return StreamingResponse(
            _to_sse(generator, axe=3, body=body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))