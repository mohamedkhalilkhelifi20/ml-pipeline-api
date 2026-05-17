# =============================================================================
# rapport/rapport.py — Endpoints rapport IA (rétro-compatibilité frontend)
# =============================================================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional
from services.rapport_service import (
    generer_rapport_axe1,
    generer_rapport_axe2,
    generer_rapport_axe3,
)
from rapport.streaming import sse_stream_and_save, SSE_HEADERS

router = APIRouter(prefix="/rapport", tags=["Rapport IA"])


class RapportRequest(BaseModel):
    patient:        dict[str, Any]
    prediction:     dict[str, Any]
    patient_nom:    Optional[str] = "Inconnu"
    patient_prenom: Optional[str] = "Inconnu"
    medecin_nom:    Optional[str] = None
    client_id:      Optional[str] = None
    doctor_id:      Optional[str] = None


def _sse_response(generator, axe: int, body: RapportRequest):
    stream = sse_stream_and_save(
        generator=generator,
        axe=axe,
        patient_nom=body.patient_nom or "Inconnu",
        patient_prenom=body.patient_prenom or "Inconnu",
        patient_data=body.patient,
        prediction=body.prediction,
        medecin_nom=body.medecin_nom,
        client_id=body.client_id,
        doctor_id=body.doctor_id,
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/axe1")
async def rapport_axe1(body: RapportRequest):
    try:
        return _sse_response(generer_rapport_axe1(body.patient, body.prediction), 1, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/axe2")
async def rapport_axe2(body: RapportRequest):
    try:
        return _sse_response(generer_rapport_axe2(body.patient, body.prediction), 2, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/axe3")
async def rapport_axe3(body: RapportRequest):
    try:
        return _sse_response(generer_rapport_axe3(body.patient, body.prediction), 3, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
