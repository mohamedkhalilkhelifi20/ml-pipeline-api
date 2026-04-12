from fastapi import APIRouter, HTTPException
from axe2.schemas.axe2 import Axe2Input, Axe2Output
from axe2.services.predict_axe2 import predict_axe2

router = APIRouter(prefix="/predict", tags=["Axe 2 — Stroke Severity"])


@router.post("/axe2", response_model=Axe2Output)
def predict(data: Axe2Input) -> Axe2Output:
    try:
        return predict_axe2(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
