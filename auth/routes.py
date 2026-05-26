# =============================================================================
# auth/routes.py
#
# POST /auth/register        — inscription médecin uniquement
# POST /auth/login           — connexion (médecin + secrétaire + admin)
# GET  /auth/me              — profil connecté
# PUT  /auth/change-password — changer son mot de passe
# =============================================================================

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from models.user_model import UserDocument, Role
from auth.schemas import DoctorRegisterRequest, TokenResponse, UserOut, ChangePasswordRequest, ProfileUpdateRequest
from auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


# ── Inscription médecin ───────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: DoctorRegisterRequest):
    """Crée un compte médecin. Les secrétaires sont créées par le médecin."""
    existing = await UserDocument.find_one(UserDocument.email == body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email déjà utilisé")

    user = UserDocument(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name.strip(),
        role=Role.DOCTOR,
        specialite=body.specialite.strip(),
    )
    await user.insert()
    return _serialize(user)


# ── Connexion (tous rôles) ────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = await UserDocument.find_one(
        UserDocument.email == form.username.lower().strip()
    )
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé — contactez votre médecin ou l'administrateur",
        )
    token = create_access_token(str(user.id), user.role.value)
    return TokenResponse(
        access_token=token,
        role=user.role.value,
        full_name=user.full_name,
        user_id=str(user.id),
    )


# ── Profil ────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def me(user: UserDocument = Depends(get_current_user)):
    return _serialize(user)


# ── Changer mot de passe ──────────────────────────────────────────────────────

@router.put("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: UserDocument = Depends(get_current_user),
):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    user.hashed_password = hash_password(body.new_password)
    await user.save()
    return {"message": "Mot de passe mis à jour"}


# ── Mettre à jour le profil ───────────────────────────────────────────────────

@router.put("/profile", response_model=UserOut)
async def update_profile(
    body: ProfileUpdateRequest,
    user: UserDocument = Depends(get_current_user),
):
    if body.full_name  is not None: user.full_name  = body.full_name.strip()
    if body.telephone  is not None: user.telephone  = body.telephone.strip() or None
    if body.adresse    is not None: user.adresse    = body.adresse.strip()   or None
    if body.specialite is not None and user.role.value == "doctor":
        user.specialite = body.specialite.strip() or None
    if body.email is not None:
        new_email = body.email.lower().strip()
        if new_email != user.email:
            conflict = await UserDocument.find_one(UserDocument.email == new_email)
            if conflict:
                raise HTTPException(status_code=400, detail="Cet email est déjà utilisé par un autre compte.")
            user.email = new_email
    await user.save()
    return _serialize(user)


# ── Sérializer ────────────────────────────────────────────────────────────────

def _serialize(user: UserDocument) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        specialite=user.specialite,
        assigned_doctor_id=(
            str(user.assigned_doctor_id) if user.assigned_doctor_id else None
        ),
        telephone=user.telephone,
        adresse=user.adresse,
        is_active=user.is_active,
    )
