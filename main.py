import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from axe1.routes import axe1
from axe2.routes import axe2
from axe3.routes import fdead, ddead

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

@app.get("/health")
def health():
    return {"status": "ok"}