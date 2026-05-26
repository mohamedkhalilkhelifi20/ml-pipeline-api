# =============================================================================
# rapport/history.py — Historique rapports (avec filtre par médecin)
#
# GET  /history                        — admin : tous les rapports
# GET  /history/mine                   — médecin : ses propres rapports
# GET  /history/{rapport_id}           — détail
# GET  /history/patient/{nom}/{prenom} — rapports d'un patient
# DELETE /history/{rapport_id}         — supprimer
# =============================================================================

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Any
from pydantic import BaseModel
from beanie import PydanticObjectId
from models.user_model import UserDocument, Role
from models.client_model import ClientDocument
from auth.security import get_current_user, require_roles
from services.history_service import (
    get_all_rapports,
    get_rapport_by_id,
    get_rapports_by_patient,
    delete_rapport,
    save_rapport,
)

router = APIRouter(prefix="/history", tags=["Historique"])

_any_staff = require_roles(Role.DOCTOR, Role.SECRETARY, Role.ADMIN)


# ── Liste rapports ────────────────────────────────────────────────────────────

@router.get("/")
async def list_rapports(
    axe:         Optional[int] = Query(None),
    patient_nom: Optional[str] = Query(None),
    limit:       int           = Query(50, le=200),
    current: UserDocument = Depends(_any_staff),
):
    # Le médecin ne voit que ses propres rapports ; admin voit tout
    doctor_id = str(current.id) if current.role == Role.DOCTOR else None

    rapports = await get_all_rapports(
        axe=axe,
        patient_nom=patient_nom,
        limit=limit,
        doctor_id=doctor_id,
    )
    return {"total": len(rapports), "rapports": rapports}


# ── Rapports du médecin connecté ──────────────────────────────────────────────

@router.get("/mine")
async def my_rapports(
    limit: int = Query(50, le=200),
    current: UserDocument = Depends(require_roles(Role.DOCTOR)),
):
    rapports = await get_all_rapports(doctor_id=str(current.id), limit=limit)
    return {"total": len(rapports), "rapports": rapports}


# ── Rapports d'un patient ─────────────────────────────────────────────────────

@router.get("/patient/{patient_nom}/{patient_prenom}")
async def rapports_patient(
    patient_nom: str,
    patient_prenom: str,
    current: UserDocument = Depends(_any_staff),
):
    rapports = await get_rapports_by_patient(patient_nom, patient_prenom)
    if not rapports:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun rapport pour {patient_prenom} {patient_nom}",
        )
    # Médecin : filtre sur ses rapports uniquement
    if current.role == Role.DOCTOR:
        rapports = [r for r in rapports if r.get("doctor_id") == str(current.id)]
    return {
        "patient":  f"{patient_prenom} {patient_nom.upper()}",
        "total":    len(rapports),
        "rapports": rapports,
    }


# ── Détail ────────────────────────────────────────────────────────────────────

@router.get("/{rapport_id}")
async def get_rapport(
    rapport_id: str,
    current: UserDocument = Depends(_any_staff),
):
    rapport = await get_rapport_by_id(rapport_id)
    if not rapport:
        raise HTTPException(status_code=404, detail="Rapport introuvable")

    if current.role == Role.DOCTOR and rapport.get("doctor_id") != str(current.id):
        raise HTTPException(status_code=403, detail="Ce rapport ne vous appartient pas")

    return rapport


# ── Enregistrer prédiction ML (sans texte IA) ────────────────────────────────

class MLSaveRequest(BaseModel):
    axe:          int
    client_id:    str
    patient_data: dict[str, Any]
    prediction:   dict[str, Any]


@router.post("/save-prediction", status_code=201)
async def save_ml_prediction(
    body: MLSaveRequest,
    current: UserDocument = Depends(require_roles(Role.DOCTOR, Role.ADMIN)),
):
    try:
        client = await ClientDocument.get(PydanticObjectId(body.client_id))
    except Exception:
        raise HTTPException(404, "Patient introuvable.")
    if not client:
        raise HTTPException(404, "Patient introuvable.")

    rapport_id = await save_rapport(
        axe=body.axe,
        patient_nom=client.nom,
        patient_prenom=client.prenom,
        patient_data=body.patient_data,
        prediction=body.prediction,
        rapport_texte="",
        medecin_nom=current.full_name,
        client_id=body.client_id,
        doctor_id=str(current.id),
    )
    return {"rapport_id": rapport_id, "message": "Rapport ML enregistré avec succès."}


# ── Suppression ───────────────────────────────────────────────────────────────

@router.delete("/{rapport_id}")
async def supprimer_rapport(
    rapport_id: str,
    current: UserDocument = Depends(require_roles(Role.DOCTOR, Role.ADMIN)),
):
    rapport = await get_rapport_by_id(rapport_id)
    if not rapport:
        raise HTTPException(status_code=404, detail="Rapport introuvable")

    if current.role == Role.DOCTOR and rapport.get("doctor_id") != str(current.id):
        raise HTTPException(status_code=403, detail="Ce rapport ne vous appartient pas")

    await delete_rapport(rapport_id)
    return {"message": "Rapport supprimé", "id": rapport_id}
