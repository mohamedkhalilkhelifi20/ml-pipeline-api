# =============================================================================
# database.py — Connexion MongoDB + initialisation Beanie
# =============================================================================

import os
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore
from beanie import init_beanie  # type: ignore
from models.rapport_model     import RapportDocument
from models.user_model        import UserDocument
from models.client_model      import ClientDocument
from models.rendezvous_model  import RendezVousDocument


async def init_db():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db  = os.getenv("MONGODB_DB", "strokeai")

    client = AsyncIOMotorClient(mongodb_url)

    await init_beanie(
        database=client[mongodb_db],
        document_models=[
            UserDocument,
            ClientDocument,
            RapportDocument,
            RendezVousDocument,
        ],
    )

    print(f"[OK] MongoDB connecte - base : {mongodb_db}")
