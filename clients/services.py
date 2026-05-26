# =============================================================================
# clients/services.py — CRUD patients + serialisation
# =============================================================================

import random
import string
from datetime import datetime, timezone
from typing import Optional

from beanie import PydanticObjectId
from models.client_model import ClientDocument
from models.user_model import UserDocument, Role
from models.rapport_model import RapportDocument


# ── Génération du numéro dossier ──────────────────────────────────────────────

def _generate_numero_dossier() -> str:
    """PAT-YYYYMM-XXXX  (XXXX = 4 caractères alphanumériques aléatoires)."""
    now    = datetime.now(timezone.utc)
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"PAT-{now.strftime('%Y%m')}-{suffix}"


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
) -> ClientDocument:
    doctor = await UserDocument.get(PydanticObjectId(doctor_id))
    if not doctor or doctor.role != Role.DOCTOR:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Médecin introuvable")

    # Garantit l'unicité du numéro dossier
    while True:
        numero = _generate_numero_dossier()
        if not await ClientDocument.find_one(ClientDocument.numero_dossier == numero):
            break

    nom_clean    = nom.strip().upper()
    prenom_clean = prenom.strip().capitalize()
    client = ClientDocument(
        numero_dossier=numero,
        nom=nom_clean,
        prenom=prenom_clean,
        full_name=f"{prenom_clean} {nom_clean}",
        date_naissance=date_naissance,
        sexe=sexe,
        telephone=telephone,
        adresse=adresse,
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
        "id":               str(client.id),
        "numero_dossier":   client.numero_dossier,
        "full_name":        client.full_name,
        "nom":              client.nom,
        "prenom":           client.prenom,
        "date_naissance":   client.date_naissance,
        "sexe":             client.sexe,
        "telephone":        client.telephone,
        "adresse":          client.adresse,
        "doctor_id":        str(client.doctor_id),
        "doctor_name":      doctor.full_name if doctor else None,
        "secretary_id":     str(client.secretary_id),
        "secretary_name":   secretary.full_name if secretary else None,
        "created_at":       client.created_at.isoformat(),
    }


async def get_client_rapports(client_id: str) -> list[dict]:
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
        "client_id":      str(doc.client_id) if doc.client_id else None,
        "doctor_id":      str(doc.doctor_id) if doc.doctor_id else None,
        "patient_data":   doc.patient_data,
        "prediction":     doc.prediction,
        "rapport_texte":  doc.rapport_texte,
        "modele_llm":     doc.modele_llm,
        "note_medecin":   doc.note_medecin,
        "documents_lab":  [d.model_dump() for d in doc.documents_lab],
        "medecin_nom":    doc.medecin_nom,
        "created_at":     doc.created_at.isoformat(),
    }
