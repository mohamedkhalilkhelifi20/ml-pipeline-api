# =============================================================================
# clients/services.py — CRUD clients MongoDB
# =============================================================================

from typing import Optional
from bson import ObjectId
from beanie import PydanticObjectId
from models.client_model import ClientDocument
from models.user_model import UserDocument, Role
from models.rapport_model import RapportDocument


# ── Création ──────────────────────────────────────────────────────────────────

async def create_client(
    nom: str,
    prenom: str,
    doctor_id: str,
    secretary_id: str,
    date_naissance: Optional[str] = None,
    sexe: Optional[str] = None,
    telephone: Optional[str] = None,
    adresse: Optional[str] = None,
    notes: Optional[str] = None,
) -> ClientDocument:
    doctor = await UserDocument.get(PydanticObjectId(doctor_id))
    if not doctor or doctor.role != Role.DOCTOR:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Médecin introuvable")

    client = ClientDocument(
        nom=nom.strip().upper(),
        prenom=prenom.strip().capitalize(),
        date_naissance=date_naissance,
        sexe=sexe,
        telephone=telephone,
        adresse=adresse,
        notes=notes,
        doctor_id=PydanticObjectId(doctor_id),
        secretary_id=PydanticObjectId(secretary_id),
    )
    await client.insert()
    return client


# ── Lecture ───────────────────────────────────────────────────────────────────

async def get_client(client_id: str) -> Optional[ClientDocument]:
    try:
        return await ClientDocument.get(PydanticObjectId(client_id))
    except Exception:
        return None


async def list_clients_by_doctor(doctor_id: str) -> list[ClientDocument]:
    return await ClientDocument.find(
        ClientDocument.doctor_id == PydanticObjectId(doctor_id)
    ).sort(-ClientDocument.created_at).to_list()


async def list_clients_by_secretary(secretary_id: str) -> list[ClientDocument]:
    return await ClientDocument.find(
        ClientDocument.secretary_id == PydanticObjectId(secretary_id)
    ).sort(-ClientDocument.created_at).to_list()


# ── Serializer avec joins ─────────────────────────────────────────────────────

async def serialize_client(client: ClientDocument) -> dict:
    doctor    = await UserDocument.get(client.doctor_id)
    secretary = await UserDocument.get(client.secretary_id)
    return {
        "id":             str(client.id),
        "nom":            client.nom,
        "prenom":         client.prenom,
        "date_naissance": client.date_naissance,
        "sexe":           client.sexe,
        "telephone":      client.telephone,
        "adresse":        client.adresse,
        "notes":          client.notes,
        "doctor_id":      str(client.doctor_id),
        "doctor_name":    doctor.full_name if doctor else None,
        "secretary_id":   str(client.secretary_id),
        "secretary_name": secretary.full_name if secretary else None,
        "created_at":     client.created_at.isoformat(),
    }


async def get_client_rapports(client_id: str) -> list[dict]:
    """Tous les rapports ML liés à ce client."""
    rapports = await RapportDocument.find(
        RapportDocument.client_id == PydanticObjectId(client_id)
    ).sort(-RapportDocument.created_at).to_list()

    return [_serialize_rapport(r) for r in rapports]


def _serialize_rapport(doc: RapportDocument) -> dict:
    return {
        "id":             str(doc.id),
        "axe":            doc.axe,
        "patient_nom":    doc.patient_nom,
        "patient_prenom": doc.patient_prenom,
        "prediction":     doc.prediction,
        "rapport_texte":  doc.rapport_texte,
        "modele_llm":     doc.modele_llm,
        "created_at":     doc.created_at.isoformat(),
    }
