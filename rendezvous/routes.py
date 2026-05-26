# =============================================================================
# rendezvous/routes.py — Gestion des rendez-vous
#
# POST   /rendezvous/           — créer un RDV (secrétaire)
# GET    /rendezvous/           — liste RDV du médecin (secrétaire / médecin)
# GET    /rendezvous/creneaux   — créneaux d'un jour (secrétaire / médecin)
# DELETE /rendezvous/{id}       — annuler un RDV (secrétaire)
# =============================================================================

from datetime import datetime, date as date_type
from fastapi import APIRouter, HTTPException, Depends, Query
from beanie import PydanticObjectId
from models.rendezvous_model import RendezVousDocument
from models.client_model     import ClientDocument
from models.user_model       import UserDocument, Role
from auth.security           import require_roles
from rendezvous.schemas      import RendezVousCreate, RendezVousUpdate

router = APIRouter(prefix="/rendezvous", tags=["Rendez-vous"])

# ── Config horaire ─────────────────────────────────────────────────────────────
WORK_START   = 8          # 08:00
WORK_END     = 18         # 18:00 (dernier créneau : 17:30)
SLOT_MIN     = 30         # durée d'un créneau en minutes
WORK_DAYS    = {0,1,2,3,4,5}   # lundi(0)–samedi(5), dimanche(6) exclu

_only_secretary = require_roles(Role.SECRETARY, Role.ADMIN)
_staff          = require_roles(Role.SECRETARY, Role.DOCTOR, Role.ADMIN)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_slot(dt: datetime):
    if dt.weekday() not in WORK_DAYS:
        raise HTTPException(400, "Le médecin ne travaille pas le dimanche.")
    if not (WORK_START <= dt.hour < WORK_END):
        raise HTTPException(400, f"Heure hors plage ({WORK_START}h–{WORK_END}h).")
    if dt.minute not in (0, 30):
        raise HTTPException(400, "Créneau invalide : minutes doivent être 0 ou 30.")


def _get_doctor_id(current: UserDocument) -> PydanticObjectId:
    if current.role == Role.DOCTOR:
        return current.id
    if current.role == Role.SECRETARY:
        if not current.assigned_doctor_id:
            raise HTTPException(400, "Aucun médecin assigné à ce compte secrétaire.")
        return current.assigned_doctor_id
    raise HTTPException(403, "Accès non autorisé.")


async def _serialize(rdv: RendezVousDocument) -> dict:
    client = await ClientDocument.get(rdv.client_id)
    doctor = await UserDocument.get(rdv.doctor_id)
    return {
        "id":           str(rdv.id),
        "client_id":    str(rdv.client_id),
        "client_nom":   client.full_name if client else "—",
        "doctor_id":    str(rdv.doctor_id),
        "doctor_nom":   doctor.full_name if doctor else "—",
        "secretary_id": str(rdv.secretary_id),
        "date_heure":   rdv.date_heure.isoformat(),
        "duree":        rdv.duree,
        "motif":        rdv.motif,
        "statut":       rdv.statut,
        "created_at":   rdv.created_at.isoformat(),
    }


# ── Créer un rendez-vous ──────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_rendezvous(
    body: RendezVousCreate,
    current: UserDocument = Depends(_only_secretary),
):
    # Normalise : retire le timezone pour comparer en UTC naïf
    dt = body.date_heure.replace(tzinfo=None)

    _validate_slot(dt)

    doctor_id = _get_doctor_id(current)

    # Vérifie que le client existe et appartient au bon médecin
    try:
        client = await ClientDocument.get(PydanticObjectId(body.client_id))
    except Exception:
        raise HTTPException(404, "Patient introuvable.")
    if not client:
        raise HTTPException(404, "Patient introuvable.")
    if client.doctor_id != doctor_id:
        raise HTTPException(403, "Ce patient n'est pas sous la responsabilité de votre médecin.")

    # Conflit créneau : même médecin, même heure exacte, statut confirmé
    conflict_slot = await RendezVousDocument.find_one(
        RendezVousDocument.doctor_id  == doctor_id,
        RendezVousDocument.statut     == "confirme",
        RendezVousDocument.date_heure == dt,
    )
    if conflict_slot:
        raise HTTPException(409, "Ce créneau est déjà réservé pour un autre patient.")

    # Conflit patient : même patient déjà confirmé ce jour-là
    day_start = datetime(dt.year, dt.month, dt.day, 0, 0)
    day_end   = datetime(dt.year, dt.month, dt.day, 23, 59)
    conflict_patient = await RendezVousDocument.find_one(
        RendezVousDocument.client_id  == PydanticObjectId(body.client_id),
        RendezVousDocument.statut     == "confirme",
        RendezVousDocument.date_heure >= day_start,
        RendezVousDocument.date_heure <= day_end,
    )
    if conflict_patient:
        raise HTTPException(
            409,
            f"Ce patient a déjà un rendez-vous confirmé ce jour-là "
            f"à {conflict_patient.date_heure.strftime('%H:%M')}. "
            f"Annulez-le d'abord avant d'en créer un nouveau.",
        )

    rdv = RendezVousDocument(
        client_id=PydanticObjectId(body.client_id),
        doctor_id=doctor_id,
        secretary_id=current.id,
        date_heure=dt,
        motif=body.motif,
    )
    await rdv.insert()
    return await _serialize(rdv)


# ── Lister les rendez-vous ────────────────────────────────────────────────────

@router.get("/")
async def list_rendezvous(current: UserDocument = Depends(_staff)):
    doctor_id = _get_doctor_id(current)

    rdvs = await RendezVousDocument.find(
        RendezVousDocument.doctor_id == doctor_id,
        RendezVousDocument.statut    != "annule",
    ).sort("+date_heure").to_list()

    return [await _serialize(r) for r in rdvs]


# ── Créneaux disponibles pour un jour donné ───────────────────────────────────

@router.get("/creneaux")
async def creneaux_du_jour(
    date: str = Query(..., description="Date au format YYYY-MM-DD"),
    current: UserDocument = Depends(_staff),
):
    try:
        target = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(400, "Format de date invalide (attendu : YYYY-MM-DD).")

    if target.weekday() not in WORK_DAYS:
        return {"date": date, "jour_ouvre": False, "creneaux": []}

    doctor_id = _get_doctor_id(current)

    day_start = datetime(target.year, target.month, target.day, 0, 0)
    day_end   = datetime(target.year, target.month, target.day, 23, 59)

    booked = await RendezVousDocument.find(
        RendezVousDocument.doctor_id  == doctor_id,
        RendezVousDocument.statut     == "confirme",
        RendezVousDocument.date_heure >= day_start,
        RendezVousDocument.date_heure <= day_end,
    ).to_list()

    booked_map: dict = {}
    for r in booked:
        key = r.date_heure.strftime("%H:%M")
        booked_map[key] = {"rdv_id": str(r.id), "client_id": str(r.client_id)}

    slots = []
    for hour in range(WORK_START, WORK_END):
        for minute in (0, 30):
            heure = f"{hour:02d}:{minute:02d}"
            iso   = datetime(target.year, target.month, target.day, hour, minute).isoformat()
            entry: dict = {"heure": heure, "iso": iso}
            if heure in booked_map:
                entry["statut"]    = "pris"
                entry["rdv_id"]    = booked_map[heure]["rdv_id"]
                entry["client_id"] = booked_map[heure]["client_id"]
            else:
                entry["statut"] = "libre"
            slots.append(entry)

    return {"date": date, "jour_ouvre": True, "creneaux": slots}


# ── Modifier un rendez-vous ───────────────────────────────────────────────────

@router.put("/{rdv_id}")
async def update_rendezvous(
    rdv_id: str,
    body: RendezVousUpdate,
    current: UserDocument = Depends(_only_secretary),
):
    try:
        rdv = await RendezVousDocument.get(PydanticObjectId(rdv_id))
    except Exception:
        raise HTTPException(404, "Rendez-vous introuvable.")
    if not rdv:
        raise HTTPException(404, "Rendez-vous introuvable.")
    if rdv.statut != "confirme":
        raise HTTPException(400, "Seul un rendez-vous confirmé peut être modifié.")

    doctor_id = _get_doctor_id(current)

    # Changement de patient
    new_client_id = PydanticObjectId(body.client_id) if body.client_id else rdv.client_id
    if body.client_id is not None:
        try:
            new_client = await ClientDocument.get(new_client_id)
        except Exception:
            raise HTTPException(404, "Patient introuvable.")
        if not new_client:
            raise HTTPException(404, "Patient introuvable.")
        if new_client.doctor_id != doctor_id:
            raise HTTPException(403, "Ce patient n'est pas sous la responsabilité de votre médecin.")

    # Changement de date/heure
    new_dt = rdv.date_heure
    if body.date_heure is not None:
        new_dt = body.date_heure.replace(tzinfo=None)
        _validate_slot(new_dt)

    # Conflit créneau : même médecin, même heure, statut confirmé (sauf ce RDV lui-même)
    if body.date_heure is not None:
        conflict_slot = await RendezVousDocument.find_one(
            RendezVousDocument.doctor_id  == doctor_id,
            RendezVousDocument.statut     == "confirme",
            RendezVousDocument.date_heure == new_dt,
            RendezVousDocument.id         != rdv.id,
        )
        if conflict_slot:
            raise HTTPException(409, "Ce créneau est déjà réservé par un autre rendez-vous.")

    # Conflit patient : même patient déjà confirmé ce jour (sauf ce RDV lui-même)
    if body.client_id is not None or body.date_heure is not None:
        day_start = datetime(new_dt.year, new_dt.month, new_dt.day, 0, 0)
        day_end   = datetime(new_dt.year, new_dt.month, new_dt.day, 23, 59)
        conflict_patient = await RendezVousDocument.find_one(
            RendezVousDocument.client_id  == new_client_id,
            RendezVousDocument.statut     == "confirme",
            RendezVousDocument.date_heure >= day_start,
            RendezVousDocument.date_heure <= day_end,
            RendezVousDocument.id         != rdv.id,
        )
        if conflict_patient:
            raise HTTPException(
                409,
                f"Ce patient a déjà un rendez-vous confirmé ce jour-là "
                f"à {conflict_patient.date_heure.strftime('%H:%M')}. "
                f"Annulez-le d'abord avant de modifier.",
            )

    # Appliquer les changements
    if body.client_id is not None:
        rdv.client_id = new_client_id
    if body.date_heure is not None:
        rdv.date_heure = new_dt

    # Changement de motif (None = pas de changement, chaîne vide = effacement)
    if body.motif is not None:
        rdv.motif = body.motif or None

    await rdv.save()
    return await _serialize(rdv)


# ── Annuler un rendez-vous ────────────────────────────────────────────────────

@router.delete("/{rdv_id}", status_code=204)
async def cancel_rendezvous(
    rdv_id: str,
    current: UserDocument = Depends(_only_secretary),
):
    try:
        rdv = await RendezVousDocument.get(PydanticObjectId(rdv_id))
    except Exception:
        raise HTTPException(404, "Rendez-vous introuvable.")
    if not rdv:
        raise HTTPException(404, "Rendez-vous introuvable.")

    if str(rdv.secretary_id) != str(current.id) and current.role.value != "admin":
        raise HTTPException(403, "Vous ne pouvez annuler que vos propres rendez-vous.")

    rdv.statut = "annule"
    await rdv.save()
