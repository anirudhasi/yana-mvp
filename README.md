# Yana MVP — Rider Onboarding + Vehicle Allocation

Zero-dependency local setup. SQLite database. No Docker, no Redis, no PostgreSQL needed.

---

## What's in this MVP

| Module | What it does |
|---|---|
| Auth | Phone + OTP login, JWT tokens |
| Rider Onboarding | Apply → Upload docs → KYC review → Activate |
| Vehicle Allocation | Add vehicles/hubs, allocate to active riders, return |
| Admin Dashboard | Stats, full CRUD, audit trail |
| Django Admin | `/admin/` — full database management |
| API Docs | `/api/docs/` — interactive Swagger UI |

---

## Prerequisites

Only Python 3.10, 3.11, 3.12, or 3.13 is needed.
**Python 3.14 may have issues with some packages — use 3.12 if possible.**

Check your version:
```powershell
python --version
```

If you need Python 3.12:
→ Download from https://www.python.org/downloads/release/python-3120/
→ During install: tick **"Add Python to PATH"**
→ Restart PowerShell after installing

---

## Setup — 5 commands, then done

Open PowerShell and run these **one at a time**:

```powershell
# 1. Go into the backend folder
cd path\to\yana-mvp\backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate it  (you will see (venv) appear in prompt)
.\venv\Scripts\activate

# 4. Install packages  (only 8 packages, ~30 seconds)
pip install -r requirements.txt

# 5. Create database tables
python manage.py migrate
```

You should see Django create all tables with no errors.

---

## Load demo data (recommended)

```powershell
python manage.py shell < seed_data.py
```

This creates:
- 3 hubs (Koramangala, HSR Layout, Whitefield)
- 6 vehicles
- 3 demo riders at different stages
- 1 active allocation

**Demo login credentials:**
| Phone | Password | Role | Status |
|---|---|---|---|
| +919999999999 | admin123 | Admin | — |
| +919876543210 | rider123 | Rider | Applied |
| +918765432109 | rider123 | Rider | KYC Verified |
| +917654321098 | rider123 | Rider | Active + vehicle allocated |

---

## Start the server

```powershell
python manage.py runserver
```

Then open these URLs in your browser:

| URL | What it is |
|---|---|
| Open `frontend/index.html` directly in browser | React Admin UI |
| http://127.0.0.1:8000/admin/ | Django Admin (full DB management) |
| http://127.0.0.1:8000/api/docs/ | Swagger API documentation |

---

## How to open the frontend

The frontend is a single HTML file — no build step, no npm.

**Windows:** Right-click `frontend/index.html` → Open with → Chrome/Edge/Firefox

Or drag and drop the file into your browser.

The frontend talks to Django at `http://127.0.0.1:8000` automatically.

---

## Complete API reference

### Auth
```
POST /api/auth/otp/request/    Body: { phone_number }
                                Returns: { otp }  ← shown in dev mode

POST /api/auth/otp/verify/     Body: { phone_number, otp }
                                Returns: { access, refresh, user }

POST /api/auth/token/refresh/  Body: { refresh }
GET  /api/auth/me/             Returns current user
PATCH /api/auth/me/update/     Body: { full_name, email }
```

### Rider Onboarding
```
GET  /api/onboarding/riders/                    List all riders (ops/admin)
GET  /api/onboarding/riders/?onboarding_status=applied   Filter by status

GET  /api/onboarding/riders/my_profile/         Rider fetches own profile
POST /api/onboarding/riders/my_profile/         Rider creates/updates profile

GET  /api/onboarding/riders/{id}/               Rider detail
POST /api/onboarding/riders/{id}/upload_document/  Upload KYC doc
                                                Form-data: doc_type, file
POST /api/onboarding/riders/{id}/verify/        Approve/reject KYC
                                                Body: { action: "approve"|"reject", rejection_reason }
POST /api/onboarding/riders/{id}/activate/      Activate rider (after KYC verified)
GET  /api/onboarding/riders/{id}/events/        Audit trail
GET  /api/onboarding/riders/stats/              Status counts
```

### Fleet
```
GET  /api/fleet/hubs/                 List hubs
POST /api/fleet/hubs/                 Create hub

GET  /api/fleet/vehicles/             List all vehicles
GET  /api/fleet/vehicles/available/   Available vehicles only (?hub=<id>)
GET  /api/fleet/vehicles/stats/       Fleet status summary
POST /api/fleet/vehicles/             Add vehicle

POST /api/fleet/allocations/allocate/           Allocate vehicle to rider
                                                Body: { vehicle_id, rider_id, plan_type,
                                                        start_date, daily_rent }
GET  /api/fleet/allocations/                    List allocations (?status=active)
POST /api/fleet/allocations/{id}/return_vehicle/ Return vehicle
```

---

## Onboarding status flow

```
Applied  →  Docs Submitted  →  KYC Pending  →  KYC Verified  →  Active
                                   ↓
                               Rejected
```

- Rider uploads documents → status auto-advances to `docs_submitted`
- Ops team reviews → `verify/` endpoint → `kyc_verified` or `rejected`
- Ops team activates → `activate/` endpoint → `active`
- Only `active` riders can be allocated a vehicle

---

## Troubleshooting

**"No module named X"**
```powershell
# Make sure venv is active — you should see (venv) in prompt
.\venv\Scripts\activate
pip install -r requirements.txt
```

**"Table does not exist"**
```powershell
python manage.py migrate
```

**"Port 8000 already in use"**
```powershell
python manage.py runserver 8001
# Then change API url in frontend/index.html line 7: const API = "http://127.0.0.1:8001/api";
```

**Python 3.14 package errors**
Install Python 3.12 from python.org/downloads, then:
```powershell
# Remove old venv
Remove-Item -Recurse -Force venv

# Create new one with Python 3.12 explicitly
C:\Python312\python.exe -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
```

**Frontend shows "Failed to fetch"**
- Make sure Django server is running: `python manage.py runserver`
- Make sure you see `(venv)` in your PowerShell prompt

---

## Next modules (Phase 2)

When this MVP is working, the next sprint builds:
- Payments & Wallet module
- Job Marketplace (demand slots)
- Sales CRM
- Flutter Rider App connected to this backend
- Docker deployment with PostgreSQL
