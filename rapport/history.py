# =============================================================================
# routers/history.py — Endpoints historique rapports
# StrokeAI | GET/DELETE rapports sauvegardés
#
# Endpoints :
#   GET  /history                          — liste tous les rapports
#   GET  /history/{rapport_id}             — détail un rapport
#   GET  /history/patient/{nom}/{prenom}   — rapports d'un patient
#   DELETE /history/{rapport_id}           — supprimer un rapport
# =============================================================================

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.history_service import (
    get_all_rapports,
    get_rapport_by_id,
    get_rapports_by_patient,
    delete_rapport,
)

router = APIRouter(prefix="/history", tags=["Historique"])


# -----------------------------------------------------------------------------
# GET /history — liste avec filtres optionnels
# -----------------------------------------------------------------------------

@router.get("/")
async def list_rapports(
    axe:         Optional[int] = Query(None, description="Filtrer par axe (1, 2 ou 3)"),
    patient_nom: Optional[str] = Query(None, description="Filtrer par nom patient"),
    limit:       int           = Query(50,   description="Nombre max de résultats"),
):
    """
    Retourne la liste des rapports triés par date décroissante.
    Exemples :
      GET /history
      GET /history?axe=1
      GET /history?patient_nom=BEN+ALI
      GET /history?axe=1&limit=10
    """
    rapports = await get_all_rapports(axe=axe, patient_nom=patient_nom, limit=limit)
    return {
        "total":   len(rapports),
        "rapports": rapports,
    }


# -----------------------------------------------------------------------------
# GET /history/patient/{nom}/{prenom} — historique d'un patient
# -----------------------------------------------------------------------------

@router.get("/patient/{patient_nom}/{patient_prenom}")
async def rapports_patient(patient_nom: str, patient_prenom: str):
    """
    Retourne tous les rapports d'un patient (tous axes).
    Exemple : GET /history/patient/BEN+ALI/Mohamed
    """
    rapports = await get_rapports_by_patient(patient_nom, patient_prenom)
    if not rapports:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun rapport trouvé pour {patient_prenom} {patient_nom}",
        )
    return {
        "patient":  f"{patient_prenom} {patient_nom.upper()}",
        "total":    len(rapports),
        "rapports": rapports,
    }


# -----------------------------------------------------------------------------
# GET /history/{rapport_id} — détail complet
# -----------------------------------------------------------------------------

@router.get("/{rapport_id}")
async def get_rapport(rapport_id: str):
    """
    Retourne un rapport complet par son ID MongoDB.
    Exemple : GET /history/663f1a2b...
    """
    rapport = await get_rapport_by_id(rapport_id)
    if not rapport:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    return rapport


# -----------------------------------------------------------------------------
# DELETE /history/{rapport_id} — suppression
# -----------------------------------------------------------------------------

@router.delete("/{rapport_id}")
async def supprimer_rapport(rapport_id: str):
    """
    Supprime un rapport par ID.
    Exemple : DELETE /history/663f1a2b...
    """
    deleted = await delete_rapport(rapport_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    return {"message": "Rapport supprimé", "id": rapport_id}
