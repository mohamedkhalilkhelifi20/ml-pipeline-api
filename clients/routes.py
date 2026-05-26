# =============================================================================
# clients/routes.py — Endpoints clients/patients
#
# Secrétaire :
#   POST /clients              — créer un client et l'assigner à un médecin
#   GET  /clients              — liste de ses propres clients créés
#
# Médecin :
#   GET  /clients/mine         — liste de ses clients assignés
#   GET  /clients/{id}         — détail d'un client (si appartient au médecin)
#   GET  /clients/{id}/rapports — tous les rapports ML du client
# =============================================================================

from fastapi import APIRouter, HTTPException, Depends, status
from models.user_model import UserDocument, Role
from auth.security import require_roles
from clients.schemas import ClientCreate, ClientUpdate, ClientOut
from clients import services

router = APIRouter(prefix="/clients", tags=["Clients"])

_secretary_or_admin = require_roles(Role.SECRETARY, Role.ADMIN)
_doctor_or_admin    = require_roles(Role.DOCTOR, Role.ADMIN)
_any_staff          = require_roles(Role.SECRETARY, Role.DOCTOR, Role.ADMIN)


# ── Secrétaire : créer un client ──────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    current: UserDocument = Depends(_secretary_or_admin),
):
    # Résoudre le doctor_id : fourni explicitement (admin) ou depuis assigned_doctor_id (secrétaire)
    doctor_id = body.doctor_id
    if not doctor_id:
        if current.role == Role.SECRETARY and current.assigned_doctor_id:
            doctor_id = str(current.assigned_doctor_id)
        else:
            raise HTTPException(
                status_code=422,
                detail="doctor_id requis pour ce rôle",
            )

    client = await services.create_client(
        nom=body.nom,
        prenom=body.prenom,
        doctor_id=doctor_id,
        secretary_id=str(current.id),
        date_naissance=body.date_naissance,
        sexe=body.sexe,
        telephone=body.telephone,
        adresse=body.adresse,
    )
    return await services.serialize_client(client)


# ── Secrétaire : ses clients créés ────────────────────────────────────────────

@router.get("/my-created")
async def my_created_clients(current: UserDocument = Depends(_secretary_or_admin)):
    clients = await services.list_clients_by_secretary(str(current.id))
    return {
        "total":   len(clients),
        "clients": [await services.serialize_client(c) for c in clients],
    }


# ── Médecin : ses clients assignés ───────────────────────────────────────────

@router.get("/mine")
async def my_clients(current: UserDocument = Depends(_doctor_or_admin)):
    doctor_id = str(current.id)
    clients = await services.list_clients_by_doctor(doctor_id)
    return {
        "total":   len(clients),
        "clients": [await services.serialize_client(c) for c in clients],
    }


# ── Détail client — accessible par son médecin, la secrétaire ou l'admin ─────

@router.get("/{client_id}")
async def get_client(
    client_id: str,
    current: UserDocument = Depends(_any_staff),
):
    client = await services.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    # Un médecin ne peut voir que ses propres clients
    if current.role == Role.DOCTOR and client.doctor_id != current.id:
        raise HTTPException(status_code=403, detail="Ce client n'est pas sous votre responsabilité")

    return await services.serialize_client(client)


# ── Modifier un client ────────────────────────────────────────────────────────

@router.put("/{client_id}")
async def update_client(
    client_id: str,
    body: ClientUpdate,
    current: UserDocument = Depends(_any_staff),
):
    client = await services.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    if current.role == Role.DOCTOR and client.doctor_id != current.id:
        raise HTTPException(status_code=403, detail="Ce client n'est pas sous votre responsabilité")
    if current.role == Role.SECRETARY and client.secretary_id != current.id:
        raise HTTPException(status_code=403, detail="Ce client n'est pas sous votre gestion")

    if body.nom             is not None: client.nom            = body.nom.strip()
    if body.prenom          is not None: client.prenom         = body.prenom.strip()
    if body.date_naissance  is not None: client.date_naissance = body.date_naissance or None
    if body.sexe            is not None: client.sexe           = body.sexe or None
    if body.telephone       is not None: client.telephone      = body.telephone.strip() or None
    if body.adresse         is not None: client.adresse        = body.adresse.strip() or None

    # Recalcule le champ full_name si nom ou prénom a changé
    client.full_name = f"{client.prenom} {client.nom}"

    await client.save()
    return await services.serialize_client(client)


# ── Rapports ML d'un client ───────────────────────────────────────────────────

@router.get("/{client_id}/rapports")
async def client_rapports(
    client_id: str,
    current: UserDocument = Depends(_any_staff),
):
    client = await services.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    if current.role == Role.DOCTOR and client.doctor_id != current.id:
        raise HTTPException(status_code=403, detail="Ce client n'est pas sous votre responsabilité")

    rapports = await services.get_client_rapports(client_id)
    return {"total": len(rapports), "rapports": rapports}
