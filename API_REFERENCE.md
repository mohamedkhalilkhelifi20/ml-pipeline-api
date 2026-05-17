# StrokeAI API — Référence Endpoints v2

## Relations MongoDB

```
UserDocument (role: admin | doctor | secretary)
     │
     ├── secretary.assigned_doctor_id ──► UserDocument (doctor)
     │
ClientDocument
     ├── doctor_id    ──► UserDocument (doctor)
     └── secretary_id ──► UserDocument (secretary)

RapportDocument
     ├── client_id  ──► ClientDocument
     └── doctor_id  ──► UserDocument (doctor)
```

## Auth

| Méthode | Endpoint         | Accès | Description |
|---------|-----------------|-------|-------------|
| POST    | /auth/register  | open  | Créer un compte |
| POST    | /auth/login     | open  | Obtenir JWT (form: username + password) |
| GET     | /auth/me        | tous  | Profil connecté |

### Register body
```json
{
  "email": "dr.ali@clinic.tn",
  "password": "secret123",
  "full_name": "Dr. Ali Ben Salah",
  "role": "doctor",
  "specialite": "Neurologie",
  "assigned_doctor_id": null
}
```
Pour role=`secretary`, fournir `assigned_doctor_id` (ID du médecin).

---

## Espace Secrétaire `/secretary`

| Méthode | Endpoint                    | Description |
|---------|-----------------------------|-------------|
| GET     | /secretary/me               | Profil + médecin assigné |
| GET     | /secretary/doctor           | Info du médecin assigné + nb clients |
| POST    | /secretary/clients          | Créer un client (auto-lié au médecin assigné) |
| GET     | /secretary/clients          | Liste des clients créés |
| GET     | /secretary/clients/{id}     | Détail client |

### Créer un client
```json
{
  "nom": "Khelifi",
  "prenom": "Mohamed",
  "date_naissance": "1985-03-15",
  "sexe": "M",
  "telephone": "+216 XX XXX XXX",
  "adresse": "Tunis",
  "notes": "Patient hypertendu"
}
```

---

## Espace Médecin `/doctor`

| Méthode | Endpoint                              | Description |
|---------|---------------------------------------|-------------|
| GET     | /doctor/me                            | Profil + secrétaire + nb clients |
| GET     | /doctor/secretary                     | Info de la secrétaire assignée |
| GET     | /doctor/clients                       | Tous ses clients |
| GET     | /doctor/clients/{id}                  | Détail client |
| GET     | /doctor/clients/{id}/rapports         | Rapports ML du client |
| POST    | /doctor/clients/{id}/rapport/{axe}    | Générer rapport IA (SSE) |

### Générer rapport (SSE)
`POST /doctor/clients/{client_id}/rapport/1`  (axe = 1, 2, ou 3)
```json
{
  "patient": { "age": 2, "gender": 1, "hypertension": 1, ... },
  "prediction": { "probabilite": 0.72, "verdict": "AVC probable", ... }
}
```
Réponse : stream SSE → chunks texte → `{"saved": true, "rapport_id": "..."}` → `[DONE]`

---

## Historique `/history`

| Méthode | Endpoint                          | Accès    | Description |
|---------|-----------------------------------|----------|-------------|
| GET     | /history/                         | staff    | Médecin: ses rapports / Admin: tous |
| GET     | /history/mine                     | doctor   | Ses propres rapports uniquement |
| GET     | /history/{rapport_id}             | staff    | Détail rapport |
| GET     | /history/patient/{nom}/{prenom}   | staff    | Rapports d'un patient |
| DELETE  | /history/{rapport_id}             | doctor+  | Supprimer |

---

## Admin `/users`

| Méthode | Endpoint             | Description |
|---------|---------------------|-------------|
| GET     | /users/doctors       | Liste médecins (utile à la secrétaire) |
| GET     | /users/              | Tous les utilisateurs (admin only) |
| PUT     | /users/{id}/toggle   | Activer/désactiver compte |
