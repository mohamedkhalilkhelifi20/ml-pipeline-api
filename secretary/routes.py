# =============================================================================
# secretary/routes.py — Espace secrétaire
#
# GET  /secretary/me          — profil + médecin assigné
# GET  /secretary/doctor      — info du médecin assigné
# POST /secretary/clients     — créer un client (auto-lié au médecin assigné)
# GET  /secretary/clients     — liste des clients créés
# GET  /secretary/clients/{id} — détail client
# =============================================================================

from fastapi import APIRouter, HTTPException, Depends, status
from beanie import PydanticObjectId
from models.user_model import UserDocument, Role
from models.client_model import ClientDocument
from auth.security import require_roles
from clients.schemas import ClientCreate
from clients import services as client_svc

router = APIRouter(prefix="/secretary", tags=["Secrétaire"])

_only_secretary = require_roles(Role.SECRETARY, Role.ADMIN)


def _ensure_assigned_doctor(secretary: UserDocument) -> PydanticObjectId:
    if not secretary.assigned_doctor_id:
        raise HTTPException(
            status_code=400,
            detail="Aucun médecin assigné à ce compte secrétaire",
        )
    return secretary.assigned_doctor_id


# ── Profil ────────────────────────────────────────────────────────────────────

@router.get("/me")
async def secretary_profile(current: UserDocument = Depends(_only_secretary)):
    doctor_info = None
    if current.assigned_doctor_id:
        doctor = await UserDocument.get(current.assigned_doctor_id)
        if doctor:
            doctor_info = {
                "id":         str(doctor.id),
                "full_name":  doctor.full_name,
                "email":      doctor.email,
                "specialite": doctor.specialite,
            }
    return {
        "id":           str(current.id),
        "full_name":    current.full_name,
        "email":        current.email,
        "role":         current.role.value,
        "assigned_doctor": doctor_info,
    }


# ── Médecin assigné ───────────────────────────────────────────────────────────

@router.get("/doctor")
async def my_doctor(current: UserDocument = Depends(_only_secretary)):
    doctor_id = _ensure_assigned_doctor(current)
    doctor = await UserDocument.get(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Médecin introuvable")

    # Clients gérés par ce médecin
    clients = await ClientDocument.find(
        ClientDocument.doctor_id == doctor_id
    ).to_list()

    return {
        "id":         str(doctor.id),
        "full_name":  doctor.full_name,
        "email":      doctor.email,
        "specialite": doctor.specialite,
        "nb_clients": len(clients),
    }


# ── Créer un client (auto-assigné au médecin de la secrétaire) ────────────────

@router.post("/clients", status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    current: UserDocument = Depends(_only_secretary),
):
    doctor_id = _ensure_assigned_doctor(current)

    # Vérifie cohérence si doctor_id fourni dans le body
    if body.doctor_id and str(doctor_id) != body.doctor_id:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez créer des clients que pour votre médecin assigné",
        )

    client = await client_svc.create_client(
        nom=body.nom,
        prenom=body.prenom,
        doctor_id=str(doctor_id),
        secretary_id=str(current.id),
        date_naissance=body.date_naissance,
        sexe=body.sexe,
        telephone=body.telephone,
        adresse=body.adresse,
        notes=body.notes,
    )
    return await client_svc.serialize_client(client)


# ── Liste clients créés par cette secrétaire ─────────────────────────────────

@router.get("/clients")
async def my_clients(current: UserDocument = Depends(_only_secretary)):
    clients = await client_svc.list_clients_by_secretary(str(current.id))
    return {
        "total":   len(clients),
        "clients": [await client_svc.serialize_client(c) for c in clients],
    }


# ── Détail client ─────────────────────────────────────────────────────────────

@router.get("/clients/{client_id}")
async def client_detail(
    client_id: str,
    current: UserDocument = Depends(_only_secretary),
):
    client = await client_svc.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    if client.secretary_id != current.id:
        raise HTTPException(status_code=403, detail="Ce client n'est pas sous votre gestion")

    return await client_svc.serialize_client(client)
