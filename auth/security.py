# =============================================================================
# auth/security.py — JWT HS256 + bcrypt + dépendances FastAPI
# =============================================================================

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from beanie import PydanticObjectId
from models.user_model import UserDocument, Role

# ── Configuration ─────────────────────────────────────────────────────────────

_SECRET_KEY = os.getenv("SECRET_KEY", "")
if not _SECRET_KEY:
    import secrets
    _SECRET_KEY = secrets.token_hex(32)   # aléatoire au démarrage (dev only)
    print("[WARN] SECRET_KEY non definie - tokens invalides apres redemarrage. Definir SECRET_KEY en prod.")

ALGORITHM         = "HS256"
TOKEN_TTL_MINUTES = int(os.getenv("TOKEN_TTL_MINUTES", "1440"))  # 24h par défaut

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Mots de passe ─────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MINUTES)
    payload = {
        "sub":  user_id,
        "role": role,
        "exp":  expire,
        "iat":  datetime.now(timezone.utc),   # issued at
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    """Décode et valide un JWT. Lève HTTPException si invalide."""
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            raise ValueError("sub manquant")
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── Dépendances FastAPI ───────────────────────────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserDocument:
    payload = _decode_token(token)
    try:
        user = await UserDocument.get(PydanticObjectId(payload["sub"]))
    except Exception:
        user = None

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou désactivé",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*roles: Role):
    """Dependency factory — restreint l'accès à certains rôles."""
    async def _guard(user: UserDocument = Depends(get_current_user)) -> UserDocument:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé. Rôle requis : {', '.join(r.value for r in roles)}",
            )
        return user
    return _guard


# ── Raccourcis ────────────────────────────────────────────────────────────────
require_doctor    = require_roles(Role.DOCTOR, Role.ADMIN)
require_secretary = require_roles(Role.SECRETARY, Role.ADMIN)
require_admin     = require_roles(Role.ADMIN)
