# =============================================================================
# doctor/routes.py — Espace médecin
# =============================================================================

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Path
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Annotated, Any
from beanie import PydanticObjectId

from models.user_model import UserDocument, Role
from models.client_model import ClientDocument
from models.rapport_model import RapportDocument, LabDocument
from auth.security import require_roles
from auth.schemas import SecretaryCreateRequest, UserOut
from auth.security import hash_password
from clients import services as client_svc
from services.rapport_service import (
    generer_rapport_axe1,
    generer_rapport_axe2,
    generer_rapport_axe3,
)
from rapport.streaming import sse_stream_and_save, sse_stream_and_update, SSE_HEADERS

router = APIRouter(prefix="/doctor", tags=["Médecin"])

_only_doctor = require_roles(Role.DOCTOR, Role.ADMIN)

AxeNum = Annotated[int, Path(ge=1, le=3)]
_generators = {
    1: generer_rapport_axe1,
    2: generer_rapport_axe2,
    3: generer_rapport_axe3,
}

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")


# ── Helper : récupérer la secrétaire du médecin ───────────────────────────────

async def _get_secretary(doctor_id: PydanticObjectId) -> UserDocument | None:
    return await UserDocument.find_one(
        UserDocument.assigned_doctor_id == doctor_id,
        UserDocument.role == Role.SECRETARY,
    )


# ── Profil médecin ────────────────────────────────────────────────────────────

@router.get("/me")
async def doctor_profile(current: UserDocument = Depends(_only_doctor)):
    secretary = await _get_secretary(current.id)
    clients_count = await ClientDocument.find(
        ClientDocument.doctor_id == current.id
    ).count()

    return {
        "id":         str(current.id),
        "full_name":  current.full_name,
        "email":      current.email,
        "specialite": current.specialite,
        "nb_clients": clients_count,
        "secretary":  _sec_out(secretary),
    }


# ── Créer le compte secrétaire ────────────────────────────────────────────────

@router.post("/secretary", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_secretary(
    body: SecretaryCreateRequest,
    current: UserDocument = Depends(_only_doctor),
):
    existing = await UserDocument.find_one(UserDocument.email == body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email déjà utilisé")

    secretary = UserDocument(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name.strip(),
        role=Role.SECRETARY,
        assigned_doctor_id=current.id,
        telephone=body.telephone,
        adresse=body.adresse,
    )
    await secretary.insert()
    return _user_out(secretary)


# ── Mettre à jour la secrétaire ───────────────────────────────────────────────

class SecretaryUpdateRequest(BaseModel):
    full_name:    str | None = None
    telephone:    str | None = None
    adresse:      str | None = None
    new_password: str | None = None


@router.put("/secretary", response_model=UserOut)
async def update_secretary(
    body: SecretaryUpdateRequest,
    current: UserDocument = Depends(_only_doctor),
):
    secretary = await _get_secretary(current.id)
    if not secretary:
        raise HTTPException(status_code=404, detail="Aucune secrétaire assignée")

    if body.full_name:    secretary.full_name = body.full_name.strip()
    if body.telephone:    secretary.telephone = body.telephone
    if body.adresse:      secretary.adresse   = body.adresse
    if body.new_password:
        if len(body.new_password) < 8:
            raise HTTPException(status_code=422, detail="Mot de passe trop court (min 8 car.)")
        secretary.hashed_password = hash_password(body.new_password)

    await secretary.save()
    return _user_out(secretary)


# ── Désactiver / réactiver la secrétaire ──────────────────────────────────────

@router.delete("/secretary", status_code=status.HTTP_200_OK)
async def deactivate_secretary(current: UserDocument = Depends(_only_doctor)):
    secretary = await _get_secretary(current.id)
    if not secretary:
        raise HTTPException(status_code=404, detail="Aucune secrétaire assignée")
    secretary.is_active = False
    await secretary.save()
    return {"message": "Compte secrétaire désactivé"}


@router.post("/secretary/reactivate", status_code=status.HTTP_200_OK)
async def reactivate_secretary(current: UserDocument = Depends(_only_doctor)):
    secretary = await _get_secretary(current.id)
    if not secretary:
        raise HTTPException(status_code=404, detail="Aucune secrétaire assignée")
    secretary.is_active = True
    await secretary.save()
    return _user_out(secretary)


# ── Clients ───────────────────────────────────────────────────────────────────

@router.get("/clients")
async def my_clients(current: UserDocument = Depends(_only_doctor)):
    clients = await client_svc.list_clients_by_doctor(str(current.id))
    return {
        "total":   len(clients),
        "clients": [await client_svc.serialize_client(c) for c in clients],
    }


@router.get("/clients/{client_id}")
async def client_detail(client_id: str, current: UserDocument = Depends(_only_doctor)):
    client = await _own_client(client_id, current)
    return await client_svc.serialize_client(client)


@router.get("/clients/{client_id}/rapports")
async def client_rapports(client_id: str, current: UserDocument = Depends(_only_doctor)):
    await _own_client(client_id, current)
    rapports = await client_svc.get_client_rapports(client_id)
    return {"total": len(rapports), "rapports": rapports}


# ── Générer rapport SSE ───────────────────────────────────────────────────────

class RapportBody(BaseModel):
    patient:    dict[str, Any]
    prediction: dict[str, Any]


@router.post("/clients/{client_id}/rapport/{axe}")
async def generate_rapport(
    client_id: str,
    axe: AxeNum,
    body: RapportBody,
    current: UserDocument = Depends(_only_doctor),
):
    client = await _own_client(client_id, current)
    gen    = _generators[axe](body.patient, body.prediction)
    stream = sse_stream_and_save(
        generator=gen,
        axe=axe,
        patient_nom=client.nom,
        patient_prenom=client.prenom,
        patient_data=body.patient,
        prediction=body.prediction,
        medecin_nom=current.full_name,
        client_id=client_id,
        doctor_id=str(current.id),
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers=SSE_HEADERS)


# ── Générer rapport IA pour un rapport ML existant ───────────────────────────

@router.post("/rapports/{rapport_id}/generate-ia")
async def generate_ia_for_rapport(
    rapport_id: str,
    current: UserDocument = Depends(_only_doctor),
):
    rapport = await _own_rapport(rapport_id, current)
    axe: int = rapport.axe
    gen = _generators[axe](rapport.patient_data, rapport.prediction)
    stream = sse_stream_and_update(generator=gen, rapport_doc=rapport)
    return StreamingResponse(stream, media_type="text/event-stream", headers=SSE_HEADERS)


# ── Note médecin ──────────────────────────────────────────────────────────────

class NoteBody(BaseModel):
    note: str


@router.put("/rapports/{rapport_id}/note")
async def update_note(
    rapport_id: str,
    body: NoteBody,
    current: UserDocument = Depends(_only_doctor),
):
    rapport = await _own_rapport(rapport_id, current)
    rapport.note_medecin = body.note.strip()
    await rapport.save()
    return {"message": "Note enregistrée", "note_medecin": rapport.note_medecin}


# ── Modifier un rapport (note + texte IA) ─────────────────────────────────────

class RapportUpdate(BaseModel):
    note_medecin:  str | None            = None
    rapport_texte: str | None            = None
    patient_data:  dict[str, Any] | None = None
    prediction:    dict[str, Any] | None = None


@router.patch("/rapports/{rapport_id}")
async def update_rapport(
    rapport_id: str,
    body: RapportUpdate,
    current: UserDocument = Depends(_only_doctor),
):
    rapport = await _own_rapport(rapport_id, current)
    if body.note_medecin  is not None: rapport.note_medecin  = body.note_medecin.strip()
    if body.rapport_texte is not None: rapport.rapport_texte = body.rapport_texte
    if body.patient_data  is not None: rapport.patient_data  = body.patient_data
    if body.prediction    is not None: rapport.prediction    = body.prediction
    await rapport.save()
    return {"message": "Rapport mis à jour"}


# ── Supprimer tous les rapports du médecin ───────────────────────────────────

@router.delete("/rapports", status_code=status.HTTP_200_OK)
async def delete_all_rapports(current: UserDocument = Depends(_only_doctor)):
    """Supprime tous les rapports appartenant au médecin connecté."""
    query = {} if current.role == Role.ADMIN else {"doctor_id": current.id}
    rapports = await RapportDocument.find(query).to_list()

    deleted = 0
    for rapport in rapports:
        # Supprimer les fichiers lab sur disque
        client_dir = str(rapport.client_id) if rapport.client_id else "_no_client"
        rapport_dir = os.path.join(UPLOADS_DIR, client_dir, str(rapport.id))
        if os.path.isdir(rapport_dir):
            import shutil
            shutil.rmtree(rapport_dir, ignore_errors=True)
        await rapport.delete()
        deleted += 1

    return {"message": f"{deleted} rapport(s) supprimé(s)", "deleted": deleted}


# ── Documents laboratoire ─────────────────────────────────────────────────────

@router.post("/rapports/{rapport_id}/lab", status_code=status.HTTP_201_CREATED)
async def upload_lab_doc(
    rapport_id: str,
    file: UploadFile = File(...),
    current: UserDocument = Depends(_only_doctor),
):
    rapport = await _own_rapport(rapport_id, current)

    content = await file.read()
    file_id     = str(uuid.uuid4())
    client_dir  = str(rapport.client_id) if rapport.client_id else "_no_client"
    dest_dir    = os.path.join(UPLOADS_DIR, client_dir, rapport_id)
    os.makedirs(dest_dir, exist_ok=True)

    dest_path = os.path.join(dest_dir, file_id)
    with open(dest_path, "wb") as f:
        f.write(content)

    lab_doc = LabDocument(
        id=file_id,
        original_name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        uploaded_at=datetime.now(timezone.utc).isoformat(),
    )
    rapport.documents_lab.append(lab_doc)
    await rapport.save()

    return lab_doc.model_dump()


@router.get("/rapports/{rapport_id}/lab/{file_id}")
async def download_lab_doc(
    rapport_id: str,
    file_id: str,
    current: UserDocument = Depends(_only_doctor),
):
    rapport = await _own_rapport(rapport_id, current)

    lab_doc = next((d for d in rapport.documents_lab if d.id == file_id), None)
    if not lab_doc:
        raise HTTPException(status_code=404, detail="Document introuvable")

    client_dir = str(rapport.client_id) if rapport.client_id else "_no_client"
    file_path  = os.path.join(UPLOADS_DIR, client_dir, rapport_id, file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fichier introuvable sur le serveur")

    return FileResponse(
        path=file_path,
        media_type=lab_doc.content_type,
        filename=lab_doc.original_name,
    )


@router.delete("/rapports/{rapport_id}/lab/{file_id}")
async def delete_lab_doc(
    rapport_id: str,
    file_id: str,
    current: UserDocument = Depends(_only_doctor),
):
    rapport = await _own_rapport(rapport_id, current)

    lab_doc = next((d for d in rapport.documents_lab if d.id == file_id), None)
    if not lab_doc:
        raise HTTPException(status_code=404, detail="Document introuvable")

    client_dir = str(rapport.client_id) if rapport.client_id else "_no_client"
    file_path  = os.path.join(UPLOADS_DIR, client_dir, rapport_id, file_id)
    if os.path.exists(file_path):
        os.remove(file_path)

    rapport.documents_lab = [d for d in rapport.documents_lab if d.id != file_id]
    await rapport.save()
    return {"message": "Document supprimé"}


# ── Helpers privés ────────────────────────────────────────────────────────────

async def _own_client(client_id: str, doctor: UserDocument) -> ClientDocument:
    client = await client_svc.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    if doctor.role == Role.DOCTOR and client.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Ce client ne vous appartient pas")
    return client


async def _own_rapport(rapport_id: str, doctor: UserDocument) -> RapportDocument:
    try:
        rapport = await RapportDocument.get(PydanticObjectId(rapport_id))
    except Exception:
        rapport = None
    if not rapport:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    if doctor.role == Role.DOCTOR and rapport.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Ce rapport ne vous appartient pas")
    return rapport


def _sec_out(sec: UserDocument | None) -> dict | None:
    if not sec:
        return None
    return {
        "id":        str(sec.id),
        "full_name": sec.full_name,
        "email":     sec.email,
        "telephone": sec.telephone,
        "adresse":   sec.adresse,
        "is_active": sec.is_active,
    }


def _user_out(user: UserDocument) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        specialite=user.specialite,
        assigned_doctor_id=str(user.assigned_doctor_id) if user.assigned_doctor_id else None,
        telephone=user.telephone,
        adresse=user.adresse,
        is_active=user.is_active,
    )
