from pydantic import BaseModel, Field


# OopCompanion:suppressRename


class Axe1Input(BaseModel):
    # ── Démographie ──────────────────────────────────────────────
    age: int = Field(..., ge=1, le=3,
                     description="1=20-39ans, 2=40-59ans, 3=60+")
    Race: int = Field(..., ge=1, le=5,
                      description="1=Mexican American, 2=Other Hispanic, 3=Non-H White, 4=Non-H Black, 5=Other")
    Body_Mass_Index: float = Field(..., ge=1, le=4, alias="Body Mass Index",
                                   description="1=Underweight, 2=Normal, 3=Overweight, 4=Obese")
    Waist_Circumference: float = Field(..., gt=0, alias="Waist Circumference",
                                       description="Tour de taille en cm")

    # ── Mode de vie ───────────────────────────────────────────────
    smoke: int = Field(..., ge=0, le=1,
                       description="0=Non-fumeur, 1=Fumeur")
    alcohol: int = Field(..., ge=0, le=1,
                         description="0=Non, 1=Oui")
    sleep_disorder: int = Field(..., ge=1, le=2, alias="sleep disorder",
                                description="1=Oui, 2=Non")
    sleep_time: float = Field(..., ge=1, le=14, alias="sleep time",
                              description="Heures de sommeil par nuit")
    Minutes_sedentary_activity: float = Field(..., ge=0, le=1200, alias="Minutes sedentary activity",
                                              description="Minutes d'activité sédentaire par jour")
    depression: int = Field(..., ge=1, le=3,
                            description="1=Jamais, 2=Plusieurs jours, 3=Plus de la moitié du temps")
    Health_Insurance: int = Field(..., ge=1, le=2, alias="Health Insurance",
                                  description="1=Oui, 2=Non")

    # ── Antécédents médicaux ──────────────────────────────────────
    hypertension: int = Field(..., ge=0, le=1,
                              description="0=Non, 1=Oui")
    diabetes: int = Field(..., ge=0, le=1,
                          description="0=Non, 1=Oui")
    high_cholesterol: int = Field(..., ge=0, le=1, alias="high cholesterol",
                                  description="0=Non, 1=Oui")
    Coronary_Heart_Disease: int = Field(..., ge=0, le=1, alias="Coronary Heart Disease",
                                        description="0=Non, 1=Oui")
    General_health_condition: int = Field(..., ge=1, le=5, alias="General health condition",
                                          description="1=Excellent, 2=Très bon, 3=Bon, 4=Passable, 5=Mauvais")

    # ── Pression artérielle ───────────────────────────────────────
    Systolic_blood_pressure: float = Field(..., gt=0, alias="Systolic blood pressure",
                                           description="Pression systolique en mmHg")
    Diastolic_blood_pressure: float = Field(..., gt=0, alias="Diastolic blood pressure",
                                            description="Pression diastolique en mmHg")

    # ── Bilan lipidique & glycémie ────────────────────────────────
    Low_density_lipoprotein: float = Field(..., ge=0, alias="Low-density lipoprotein",
                                           description="LDL en mg/dL")
    Fasting_Glucose: float = Field(..., ge=0, alias="Fasting Glucose",
                                   description="Glycémie à jeun en mg/dL")
    Potassium: float = Field(..., ge=0,
                             description="Potassium en mg")
    Sodium: float = Field(..., ge=0,
                          description="Sodium en mg")

    # ── Nutrition ─────────────────────────────────────────────────
    energy: float = Field(..., ge=0,
                          description="Énergie en kcal")
    protein: float = Field(..., ge=0,
                           description="Protéines en g")
    Carbohydrate: float = Field(..., ge=0,
                                description="Glucides en g")
    Total_fat: float = Field(..., ge=0, alias="Total fat",
                             description="Lipides totaux en g")
    Dietary_fiber: float = Field(..., ge=0, alias="Dietary fiber",
                                 description="Fibres alimentaires en g")
    Total_saturated_fatty_acids: float = Field(..., ge=0, alias="Total saturated fatty acids",
                                               description="Acides gras saturés en g")
    Total_monounsaturated_fatty_acids: float = Field(..., ge=0, alias="Total monounsaturated fatty acids",
                                                     description="Acides gras monoinsaturés en g")
    Total_polyunsaturated_fatty_acids: float = Field(..., ge=0, alias="Total polyunsaturated fatty acids",
                                                     description="Acides gras polyinsaturés en g")

    model_config = {"populate_by_name": True}


class Axe1Output(BaseModel):
    probability: float = Field(..., description="Probabilité de stroke (0-1)")
    prediction: int = Field(..., description="0=Faible risque, 1=Risque élevé")
    threshold: float = Field(..., description="Seuil de décision utilisé")
    verdict: str = Field(..., description="Faible risque / Risque élevé")
    engineered_features: dict = Field(..., description="Features calculées automatiquement")
