from fastapi import APIRouter, HTTPException
from axe1.schemas.axe1 import Axe1Input, Axe1Output
from axe1.services.predict import predict_stroke

router = APIRouter(prefix="/predict", tags=["Axe 1 — Stroke Risk"])


@router.post("/axe1", response_model=Axe1Output)
def predict(data: Axe1Input) -> Axe1Output:
    try:
        return predict_stroke(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
