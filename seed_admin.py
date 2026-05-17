"""
seed_admin.py — Crée le compte administrateur manuellement.

Usage :
    python seed_admin.py

Le mot de passe est haché avec bcrypt avant insertion en base.
Ne jamais stocker le mot de passe en clair dans la DB ni dans ce script.
"""

import asyncio
import os
from getpass import getpass
from dotenv import load_dotenv

load_dotenv()


async def main():
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    from models.user_model import UserDocument, Role
    from models.client_model import ClientDocument
    from models.rapport_model import RapportDocument
    from auth.security import hash_password

    # ── Connexion MongoDB ──────────────────────────────────────────────────────
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db  = os.getenv("MONGODB_DB", "strokeai")
    client      = AsyncIOMotorClient(mongodb_url)

    await init_beanie(
        database=client[mongodb_db],
        document_models=[UserDocument, ClientDocument, RapportDocument],
    )

    # ── Saisie interactive ────────────────────────────────────────────────────
    print("\n=== Création du compte Administrateur ===\n")
    email     = input("Email admin : ").strip().lower()
    full_name = input("Nom complet : ").strip()
    password  = getpass("Mot de passe (min 8 car.) : ")
    confirm   = getpass("Confirmer le mot de passe : ")

    if password != confirm:
        print("❌ Les mots de passe ne correspondent pas.")
        return

    if len(password) < 8:
        print("❌ Mot de passe trop court (minimum 8 caractères).")
        return

    # ── Vérification unicité ─────────────────────────────────────────────────
    existing = await UserDocument.find_one(UserDocument.email == email)
    if existing:
        print(f"❌ Un compte existe déjà avec l'email : {email}")
        return

    # ── Insertion avec mot de passe haché ────────────────────────────────────
    admin = UserDocument(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=Role.ADMIN,
    )
    await admin.insert()

    print(f"\n[OK] Compte admin cree avec succes !")
    print(f"   ID    : {admin.id}")
    print(f"   Email : {admin.email}")
    print(f"   Role  : {admin.role.value}")
    print(f"\n[!] Le mot de passe est hache - impossible de le recuperer. Conservez-le.\n")


if __name__ == "__main__":
    asyncio.run(main())
