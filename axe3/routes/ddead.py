from fastapi import APIRouter, HTTPException
from axe3.schemas.axe3 import Axe3DdeadInput, Axe3DdeadOutput
from axe3.services.predict_ddead import predict_ddead

router = APIRouter(prefix="/predict", tags=["Axe 3 — Mortality (DDEAD 14 jours)"])


@router.post("/axe3/ddead", response_model=Axe3DdeadOutput)
def predict(data: Axe3DdeadInput) -> Axe3DdeadOutput:
    try:
        return predict_ddead(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
