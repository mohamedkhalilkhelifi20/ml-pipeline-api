from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
 
load_dotenv()
 
from axe1.routes import axe1
from axe2.routes import axe2
from axe3.routes import fdead, ddead
from rapport.rapport import router as rapport_router
from database import init_db
from rapport.history import router as history_router
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Exécuté au démarrage et à l'arrêt de FastAPI."""
    await init_db()   # ← connexion MongoDB au démarrage
    yield
    # cleanup si besoin

app = FastAPI(
    title="Stroke Prediction API",
    description="Prédiction multi-axe des AVC — NHANES + IST",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(axe1.router)
app.include_router(axe2.router)
app.include_router(fdead.router)
app.include_router(ddead.router)
app.include_router(rapport_router)
app.include_router(history_router)
 
@app.get("/health")
def health():
    return {"status": "ok"}