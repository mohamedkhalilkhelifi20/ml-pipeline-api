# =============================================================================
# database.py — Connexion MongoDB + initialisation Beanie
# À placer à la racine de backend/
# =============================================================================

import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.rapport_model import RapportDocument


async def init_db():
    """
    Initialise la connexion MongoDB.
    Appelée au démarrage de FastAPI via lifespan.
    """
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db  = os.getenv("MONGODB_DB", "strokeai")

    client = AsyncIOMotorClient(mongodb_url)

    await init_beanie(
        database=client[mongodb_db],
        document_models=[RapportDocument],
    )

    print(f"✅ MongoDB connecté — base : {mongodb_db}")
