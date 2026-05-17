# =============================================================================
# users/routes.py — Endpoints utilisateurs / annuaire
#
# Secrétaire :
#   GET /users/doctors       — liste des médecins disponibles
#
# Admin :
#   GET  /users              — liste tous les utilisateurs
#   PUT  /users/{id}/toggle  — activer / désactiver un compte
# =============================================================================

from fastapi import APIRouter, HTTPException, Depends
from models.user_model import UserDocument, Role
from auth.security import require_roles
from users.schemas import DoctorOut

router = APIRouter(prefix="/users", tags=["Utilisateurs"])

_secretary_or_admin = require_roles(Role.SECRETARY, Role.ADMIN)
_admin_only         = require_roles(Role.ADMIN)


# ── Liste des médecins — utile à la secrétaire pour assigner un client ────────

@router.get("/doctors", response_model=list[DoctorOut])
async def list_doctors(current: UserDocument = Depends(_secretary_or_admin)):
    doctors = await UserDocument.find(
        UserDocument.role == Role.DOCTOR,
        UserDocument.is_active == True,
    ).to_list()

    return [
        DoctorOut(
            id=str(d.id),
            full_name=d.full_name,
            email=d.email,
            specialite=d.specialite,
        )
        for d in doctors
    ]


# ── Admin : liste tous les utilisateurs ──────────────────────────────────────

@router.get("/")
async def list_users(current: UserDocument = Depends(_admin_only)):
    users = await UserDocument.find_all().to_list()
    return [
        {
            "id":        str(u.id),
            "email":     u.email,
            "full_name": u.full_name,
            "role":      u.role.value,
            "is_active": u.is_active,
        }
        for u in users
    ]


# ── Admin : activer / désactiver un compte ────────────────────────────────────

@router.put("/{user_id}/toggle")
async def toggle_user(user_id: str, current: UserDocument = Depends(_admin_only)):
    from beanie import PydanticObjectId

    user = await UserDocument.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if str(user.id) == str(current.id):
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous désactiver vous-même")

    user.is_active = not user.is_active
    await user.save()
    return {"id": str(user.id), "is_active": user.is_active}
