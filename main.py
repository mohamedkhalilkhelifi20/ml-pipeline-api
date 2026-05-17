# =============================================================================
# main.py — StrokeAI Backend v2
# =============================================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from axe1.routes import axe1
from axe2.routes import axe2
from axe3.routes import fdead, ddead
from rapport.rapport import router as rapport_router
from rapport.history import router as history_router
from auth.routes import router as auth_router
from users.routes import router as users_router
from clients.routes import router as clients_router
from secretary.routes import router as secretary_router
from doctor.routes import router as doctor_router
from database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="StrokeAI API",
    description="Prédiction multi-axe AVC — Médecin / Secrétaire / Client",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ML ────────────────────────────────────────────────────────────────────────
app.include_router(axe1.router)
app.include_router(axe2.router)
app.include_router(fdead.router)
app.include_router(ddead.router)

# ── Rapport / Historique ──────────────────────────────────────────────────────
app.include_router(rapport_router)
app.include_router(history_router)

# ── Auth + Gestion utilisateurs ───────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(users_router)

# ── Espaces métier ────────────────────────────────────────────────────────────
app.include_router(clients_router)
app.include_router(secretary_router)
app.include_router(doctor_router)


@app.get("/health", tags=["Santé"])
def health():
    return {"status": "ok", "version": "2.0.0"}
