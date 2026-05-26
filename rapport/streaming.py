# =============================================================================
# rapport/streaming.py — Helper SSE partagé
# Utilisé par rapport/rapport.py et doctor/routes.py
# =============================================================================

import os
import json
from typing import Any, AsyncGenerator
from services.history_service import save_rapport

_MODELE_LLM = os.getenv("OPENROUTER_MODEL", "gemini-2.0-flash-001")


async def sse_stream_and_save(
    generator: AsyncGenerator[str, None],
    axe: int,
    patient_nom: str,
    patient_prenom: str,
    patient_data: dict[str, Any],
    prediction: dict[str, Any],
    medecin_nom: str | None = None,
    client_id: str | None = None,
    doctor_id: str | None = None,
):
    """
    Stream le rapport chunk-par-chunk via SSE, accumule le texte,
    puis sauvegarde le document complet en MongoDB.
    Envoie l'ID sauvegardé comme dernier événement avant [DONE].
    """
    rapport_complet = ""
    try:
        async for chunk in generator:
            rapport_complet += chunk
            yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

        # Sauvegarde MongoDB
        try:
            rapport_id = await save_rapport(
                axe=axe,
                patient_nom=patient_nom,
                patient_prenom=patient_prenom,
                patient_data=patient_data,
                prediction=prediction,
                rapport_texte=rapport_complet,
                medecin_nom=medecin_nom,
                client_id=client_id,
                doctor_id=doctor_id,
                modele_llm=_MODELE_LLM,
            )
            meta = json.dumps({"saved": True, "rapport_id": rapport_id}, ensure_ascii=False)
            yield f"data: {meta}\n\n"
        except Exception as e:
            print(f"⚠️ Sauvegarde MongoDB échouée : {e}")

        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"


async def sse_stream_and_update(
    generator: AsyncGenerator[str, None],
    rapport_doc,          # RapportDocument instance
):
    """
    Génère le texte IA chunk-par-chunk, met à jour rapport_texte du document
    existant en MongoDB quand la génération est terminée.
    """
    texte = ""
    try:
        async for chunk in generator:
            texte += chunk
            yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

        rapport_doc.rapport_texte = texte
        await rapport_doc.save()

        meta = json.dumps({"saved": True, "rapport_id": str(rapport_doc.id)}, ensure_ascii=False)
        yield f"data: {meta}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}
