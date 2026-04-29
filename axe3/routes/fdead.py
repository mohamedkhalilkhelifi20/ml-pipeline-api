from fastapi import APIRouter, HTTPException
from axe3.schemas.axe3 import Axe3FdeadInput, Axe3FdeadOutput
from axe3.services.predict_fdead import predict_fdead

router = APIRouter(prefix="/predict", tags=["Axe 3 — Mortality (FDEAD 6 mois)"])


@router.post("/axe3/fdead", response_model=Axe3FdeadOutput)
def predict(data: Axe3FdeadInput) -> Axe3FdeadOutput:
    try:
        return predict_fdead(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
