# =============================================================================
# services/history_service.py — CRUD rapports MongoDB via Beanie
# StrokeAI | Sauvegarde + récupération historique patients
# =============================================================================

from datetime import datetime, timezone
from typing import Any, Optional
from bson import ObjectId
from models.rapport_model import RapportDocument


# -----------------------------------------------------------------------------
# Sauvegarde
# -----------------------------------------------------------------------------

async def save_rapport(
    axe: int,
    patient_nom: str,
    patient_prenom: str,
    patient_data: dict[str, Any],
    prediction: dict[str, Any],
    rapport_texte: str,
    medecin_nom: Optional[str] = None,
    client_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
) -> str:
    """
    Sauvegarde un rapport généré dans MongoDB.
    Retourne l'ID du document créé.
    """
    from beanie import PydanticObjectId

    doc = RapportDocument(
        axe=axe,
        patient_nom=patient_nom.strip().upper(),
        patient_prenom=patient_prenom.strip().capitalize(),
        patient_data=patient_data,
        prediction=prediction,
        rapport_texte=rapport_texte,
        medecin_nom=medecin_nom,
        client_id=PydanticObjectId(client_id) if client_id else None,
        doctor_id=PydanticObjectId(doctor_id) if doctor_id else None,
    )
    await doc.insert()
    return str(doc.id)


# -----------------------------------------------------------------------------
# Récupération
# -----------------------------------------------------------------------------

async def get_all_rapports(
    axe: Optional[int] = None,
    patient_nom: Optional[str] = None,
    limit: int = 50,
    doctor_id: Optional[str] = None,
) -> list[dict]:
    """
    Récupère la liste des rapports, triés par date décroissante.
    Filtres optionnels : axe (1/2/3), nom patient.
    """
    query: dict[str, Any] = {}

    if axe is not None:
        query["axe"] = axe

    if patient_nom:
        query["patient_nom"] = {"$regex": patient_nom.strip().upper(), "$options": "i"}

    if doctor_id:
        from bson import ObjectId
        query["doctor_id"] = ObjectId(doctor_id)

    rapports = await RapportDocument.find(query)\
        .sort(-RapportDocument.created_at)\
        .limit(limit)\
        .to_list()

    return [_serialize(r) for r in rapports]


async def get_rapport_by_id(rapport_id: str) -> Optional[dict]:
    """Récupère un rapport complet par son ID MongoDB."""
    try:
        doc = await RapportDocument.get(ObjectId(rapport_id))
        return _serialize(doc) if doc else None
    except Exception:
        return None


async def get_rapports_by_patient(
    patient_nom: str,
    patient_prenom: str,
) -> list[dict]:
    """Récupère tous les rapports d'un patient (tous axes confondus)."""
    rapports = await RapportDocument.find({
        "patient_nom":    patient_nom.strip().upper(),
        "patient_prenom": {"$regex": patient_prenom.strip(), "$options": "i"},
    }).sort(-RapportDocument.created_at).to_list()

    return [_serialize(r) for r in rapports]


# -----------------------------------------------------------------------------
# Suppression
# -----------------------------------------------------------------------------

async def delete_rapport(rapport_id: str) -> bool:
    """Supprime un rapport par ID. Retourne True si supprimé."""
    try:
        doc = await RapportDocument.get(ObjectId(rapport_id))
        if doc:
            await doc.delete()
            return True
        return False
    except Exception:
        return False


# -----------------------------------------------------------------------------
# Serializer interne
# -----------------------------------------------------------------------------

def _serialize(doc: RapportDocument) -> dict:
    """Convertit un document Beanie en dict JSON-serializable."""
    return {
        "id":             str(doc.id),
        "axe":            doc.axe,
        "patient_nom":    doc.patient_nom,
        "patient_prenom": doc.patient_prenom,
        "patient_data":   doc.patient_data,
        "prediction":     doc.prediction,
        "rapport_texte":  doc.rapport_texte,
        "modele_llm":     doc.modele_llm,
        "medecin_nom":    doc.medecin_nom,
        "client_id":      str(doc.client_id) if doc.client_id else None,
        "doctor_id":      str(doc.doctor_id) if doc.doctor_id else None,
        "created_at":     doc.created_at.isoformat(),
    }
