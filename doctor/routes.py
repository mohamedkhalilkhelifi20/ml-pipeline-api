# =============================================================================
# doctor/routes.py — Espace médecin
#
# Profil & secrétaire :
#   GET    /doctor/me                          — profil + secrétaire + nb clients
#   POST   /doctor/secretary                   — créer le compte secrétaire
#   DELETE /doctor/secretary                   — désactiver la secrétaire
#   PUT    /doctor/secretary                   — mettre à jour la secrétaire
#
# Clients :
#   GET    /doctor/clients                     — liste patients
#   GET    /doctor/clients/{id}                — détail patient
#   GET    /doctor/clients/{id}/rapports       — rapports ML du patient
#   POST   /doctor/clients/{id}/rapport/{axe} — générer rapport SSE
# =============================================================================

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Literal
from beanie import PydanticObjectId
from models.user_model import UserDocument, Role
from models.client_model import ClientDocument
from auth.security import require_roles
from auth.schemas import SecretaryCreateRequest, UserOut
from auth.security import hash_password
from clients import services as client_svc
from services.rapport_service import (
    generer_rapport_axe1,
    generer_rapport_axe2,
    generer_rapport_axe3,
)
from rapport.streaming import sse_stream_and_save, SSE_HEADERS

router = APIRouter(prefix="/doctor", tags=["Médecin"])

_only_doctor = require_roles(Role.DOCTOR, Role.ADMIN)

AxeNum = Literal[1, 2, 3]
_generators = {
    1: generer_rapport_axe1,
    2: generer_rapport_axe2,
    3: generer_rapport_axe3,
}


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
        "id":           str(current.id),
        "full_name":    current.full_name,
        "email":        current.email,
        "specialite":   current.specialite,
        "nb_clients":   clients_count,
        "secretary":    _sec_out(secretary),
    }


# ── Créer le compte secrétaire ────────────────────────────────────────────────

@router.post("/secretary", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_secretary(
    body: SecretaryCreateRequest,
    current: UserDocument = Depends(_only_doctor),
):
    """Le médecin crée le compte de sa secrétaire avec un mot de passe haché."""
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
    full_name:  str | None = None
    telephone:  str | None = None
    adresse:    str | None = None
    new_password: str | None = None


@router.put("/secretary", response_model=UserOut)
async def update_secretary(
    body: SecretaryUpdateRequest,
    current: UserDocument = Depends(_only_doctor),
):
    secretary = await _get_secretary(current.id)
    if not secretary:
        raise HTTPException(status_code=404, detail="Aucune secrétaire assignée")

    if body.full_name:  secretary.full_name = body.full_name.strip()
    if body.telephone:  secretary.telephone = body.telephone
    if body.adresse:    secretary.adresse   = body.adresse
    if body.new_password:
        if len(body.new_password) < 8:
            raise HTTPException(status_code=422, detail="Mot de passe trop court (min 8 car.)")
        secretary.hashed_password = hash_password(body.new_password)

    await secretary.save()
    return _user_out(secretary)


# ── Désactiver la secrétaire ──────────────────────────────────────────────────

@router.delete("/secretary", status_code=status.HTTP_200_OK)
async def deactivate_secretary(current: UserDocument = Depends(_only_doctor)):
    secretary = await _get_secretary(current.id)
    if not secretary:
        raise HTTPException(status_code=404, detail="Aucune secrétaire assignée")
    secretary.is_active = False
    await secretary.save()
    return {"message": "Compte secrétaire désactivé"}


# ── Réactiver la secrétaire ───────────────────────────────────────────────────

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


# ── Générer rapport SSE pour un client ───────────────────────────────────────

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
    gen = _generators[axe](body.patient, body.prediction)
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


# ── Helpers privés ────────────────────────────────────────────────────────────

async def _own_client(client_id: str, doctor: UserDocument) -> ClientDocument:
    client = await client_svc.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    if doctor.role == Role.DOCTOR and client.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Ce client ne vous appartient pas")
    return client


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
