# ShiftManager — Documentazione Architetturale

## 1. Visione Generale

**ShiftManager** e' un sistema di gestione turni medici progettato per il sistema sanitario italiano. Permette di gestire medici, strutture sanitarie, turni e assegnamenti con un motore di eleggibilita' e scoring che automatizza il matching medico-turno.

**Utenti target:** amministratori di cooperative mediche e strutture sanitarie (Pronto Soccorso, Guardia Medica, 118, RSA, ecc.).

**Funzionalita' principali:**
- Anagrafica medici con certificazioni, lingue e preferenze
- Gestione strutture sanitarie con sedi e requisiti
- Calendario turni con template e generazione batch
- Disponibilita' e indisponibilita' dei medici
- Assegnamento automatico con 16 controlli di eleggibilita'
- Scoring e ranking dei medici eleggibili (0-100 punti)

---

## 2. Architettura Tecnica

### Stack

| Livello | Tecnologia |
|---------|-----------|
| Backend | FastAPI 0.115+ (Python 3.12+) |
| ORM | SQLAlchemy 2.0+ (async) |
| Database | PostgreSQL 16 (asyncpg) |
| Migrazioni | Alembic |
| Frontend | Alpine.js 3.14 + Tailwind CSS (CDN) |
| Calendario | FullCalendar 6.1 |
| Auth | python-jose (JWT) + passlib (bcrypt) |
| Deploy | Docker + Railway |

### Architettura a Livelli

```
Frontend (Alpine.js SPA)
    |
    | HTTP/JSON
    v
API Layer (/app/api/)           -- Route handlers, validazione input
    |
Service Layer (/app/services/)  -- Logica di business, orchestrazione
    |
Rules Layer (/app/rules/)       -- Eleggibilita' e scoring
    |
Repository Layer (/app/repositories/)  -- Accesso dati, query
    |
Model Layer (/app/models/)      -- ORM SQLAlchemy
    |
    v
PostgreSQL
```

### Struttura del Progetto

```
ShiftManager/
├── app/
│   ├── main.py                 # FastAPI app, mount statico, health check
│   ├── api/                    # Route handlers
│   │   ├── router.py           # Aggregatore route (/api/v1/)
│   │   ├── doctors.py
│   │   ├── institutions.py
│   │   ├── shifts.py
│   │   ├── availability.py
│   │   ├── assignments.py
│   │   └── lookups.py
│   ├── models/                 # SQLAlchemy ORM
│   │   ├── doctor.py
│   │   ├── institution.py
│   │   ├── shift.py
│   │   ├── assignment.py
│   │   ├── availability.py
│   │   └── requirement.py
│   ├── schemas/                # Pydantic request/response
│   ├── services/               # Business logic
│   │   ├── doctor.py
│   │   ├── institution.py
│   │   ├── shift.py
│   │   ├── availability.py
│   │   └── assignment.py
│   ├── repositories/           # Data access
│   │   ├── base.py             # Generic CRUD
│   │   ├── doctor.py
│   │   ├── institution.py
│   │   ├── shift.py
│   │   ├── assignment.py
│   │   └── availability.py
│   ├── rules/                  # Motore regole
│   │   ├── eligibility.py      # 16 controlli eleggibilita'
│   │   ├── scoring.py          # Scoring 0-100
│   │   └── constraints.py      # Costanti regolamentari
│   ├── core/                   # Infrastruttura
│   │   ├── config.py           # Settings (Pydantic)
│   │   ├── database.py         # Engine async, session factory
│   │   └── security.py         # Hash password, JWT
│   ├── utils/
│   │   ├── enums.py            # Enum di dominio
│   │   ├── seed.py             # Dati seed (lookup tables)
│   │   └── generate_data.py    # Dati demo
│   ├── static/                 # Frontend SPA
│   │   ├── index.html          # HTML principale (~715 righe)
│   │   ├── css/app.css         # Stili custom
│   │   └── js/
│   │       ├── api.js          # Client API (fetch wrapper)
│   │       ├── app.js          # Alpine store, routing
│   │       └── pages/
│   │           ├── dashboard.js
│   │           ├── doctors.js
│   │           ├── institutions.js
│   │           └── calendar.js
│   └── tests/
├── alembic/                    # Migrazioni DB
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── pyproject.toml
└── start.sh                    # Entrypoint di avvio
```

---

## 3. Backend

### 3.1 API Endpoints

Tutti gli endpoint sono sotto il prefisso `/api/v1/`.

#### Medici (`/doctors`)

| Metodo | Path | Descrizione |
|--------|------|-------------|
| POST | `/` | Crea medico |
| GET | `/` | Lista medici (paginata: skip, limit) |
| GET | `/{doctor_id}` | Dettaglio medico |
| PATCH | `/{doctor_id}` | Aggiorna medico |
| DELETE | `/{doctor_id}` | Elimina medico |
| POST | `/{doctor_id}/certifications` | Aggiungi certificazione |
| DELETE | `/{doctor_id}/certifications/{cert_type_id}` | Rimuovi certificazione |
| POST | `/{doctor_id}/languages` | Aggiungi lingua |
| DELETE | `/{doctor_id}/languages/{language_id}` | Rimuovi lingua |

#### Strutture (`/institutions`)

| Metodo | Path | Descrizione |
|--------|------|-------------|
| POST | `/` | Crea struttura |
| GET | `/` | Lista strutture (paginata) |
| GET | `/{institution_id}` | Dettaglio struttura |
| PATCH | `/{institution_id}` | Aggiorna struttura |
| DELETE | `/{institution_id}` | Elimina struttura |
| POST | `/{institution_id}/sites` | Crea sede |
| GET | `/{institution_id}/sites` | Lista sedi |
| PATCH | `/sites/{site_id}` | Aggiorna sede |
| POST | `/{institution_id}/requirements` | Aggiungi requisito certificazione |
| GET | `/{institution_id}/requirements` | Lista requisiti |
| POST | `/{institution_id}/language-requirements` | Aggiungi requisito lingua |
| GET | `/{institution_id}/language-requirements` | Lista requisiti lingua |

#### Turni (`/shifts`)

| Metodo | Path | Descrizione |
|--------|------|-------------|
| POST | `/` | Crea turno |
| GET | `/` | Lista turni (paginata) |
| GET | `/{shift_id}` | Dettaglio turno |
| PATCH | `/{shift_id}` | Aggiorna turno |
| DELETE | `/{shift_id}` | Elimina turno |
| POST | `/{shift_id}/requirements` | Aggiungi requisito |
| POST | `/{shift_id}/language-requirements` | Aggiungi requisito lingua |
| GET | `/calendar/{site_id}` | Turni per sede e range date |
| POST | `/templates` | Crea template turno |
| GET | `/templates/{site_id}` | Lista template per sede |
| POST | `/generate` | Genera turni da template |

#### Disponibilita' (`/doctors/{doctor_id}`)

| Metodo | Path | Descrizione |
|--------|------|-------------|
| POST | `/availability` | Imposta disponibilita' |
| POST | `/availability/bulk` | Disponibilita' in blocco |
| GET | `/availability` | Ottieni disponibilita' (range date) |
| POST | `/unavailability` | Crea indisponibilita' |
| GET | `/unavailability` | Lista indisponibilita' |

#### Assegnamenti (`/assignments`)

| Metodo | Path | Descrizione |
|--------|------|-------------|
| POST | `/` | Assegna medico a turno |
| DELETE | `/{assignment_id}` | Rimuovi assegnamento |
| GET | `/check/{doctor_id}/{shift_id}` | Verifica eleggibilita' |
| GET | `/eligible/{shift_id}` | Medici eleggibili con score |
| GET | `/shift/{shift_id}` | Assegnamenti di un turno |
| GET | `/doctor/{doctor_id}` | Assegnamenti di un medico |

#### Lookup (`/lookups`)

| Metodo | Path | Descrizione |
|--------|------|-------------|
| GET | `/certification-types` | Tipi di certificazione |
| POST | `/certification-types` | Crea tipo certificazione |
| GET | `/languages` | Lingue |
| POST | `/languages` | Crea lingua |
| GET | `/code-levels` | Livelli codice |
| POST | `/code-levels` | Crea livello codice |

### 3.2 Regole di Eleggibilita'

Il motore (`app/rules/eligibility.py`) esegue 16 controlli sequenziali. Se un controllo fallisce, il medico e' **non eleggibile** (hard fail). Alcuni controlli generano solo **warning** informativi.

| # | Controllo | Tipo |
|---|-----------|------|
| 1 | Medico attivo (`is_active`) | Hard |
| 2 | Disponibilita' nel giorno/orario del turno | Hard |
| 3 | Certificazioni obbligatorie presenti | Hard |
| 4 | Certificazioni non scadute alla data del turno | Hard |
| 5 | Lingue richieste presenti | Hard |
| 6 | Competenza linguistica sufficiente | Warning |
| 7 | Distanza entro `max_distance_km` (o `willing_to_relocate`) | Hard/Warning |
| 8 | Nessuna sovrapposizione turni (finestra ±24h) | Hard |
| 9 | Riposo minimo 11 ore tra turni | Hard |
| 10 | Max 6 giorni consecutivi | Hard |
| 11 | Max 8 turni notturni al mese | Hard |
| 12 | Livello codice sufficiente (`severity_order`) | Hard |
| 13 | Capacita' lavoro autonomo se richiesto | Hard |
| 14 | Abilitazione mezzo emergenza se richiesto | Hard |
| 15 | Anni di esperienza sufficienti | Hard |
| 16 | Max turni mensili personali non superato | Hard |

**Costanti configurabili** (`app/core/config.py`):
- `MIN_REST_HOURS = 11`
- `MAX_CONSECUTIVE_DAYS = 6`
- `MAX_NIGHT_SHIFTS_PER_MONTH = 8`

### 3.3 Sistema di Scoring

Il motore (`app/rules/scoring.py`) assegna un punteggio 0-100 ai medici eleggibili per il ranking.

| Categoria | Max Punti | Criteri |
|-----------|-----------|---------|
| Disponibilita' | 25 | preferred=25, available=15, reluctant=5 |
| Preferenza turno | 15 | Match giorno/notte/weekend con preferenze medico |
| Affinita' sede | 20 | Stessa sede (20), stessa istituzione (12), tipo preferito (8) |
| Bilanciamento carico | 15 | Rapporto turni assegnati / max: ≤25%=15, ≤50%=12, ≤75%=8, <100%=4 |
| Distanza | 15 | ≤10km=15, ≤25km=12, ≤50km=8, >50km=3 |
| Qualifiche extra | 10 | Certificazioni extra (+1, max 4), lingue extra (+1, max 2), esperienza (+1, max 4) |
| **Totale** | **100** | |

### 3.4 Enum di Dominio

```
ShiftStatus:       draft | open | partially_filled | filled | in_progress | completed | cancelled
AssignmentStatus:  proposed | confirmed | rejected | cancelled | completed
AvailabilityType:  available | preferred | reluctant
UnavailabilityReason: vacation | sick_leave | personal | training | other
ShiftType:         day | night | evening | weekend_day | weekend_night
InstitutionType:   pronto_soccorso | punto_primo_intervento | guardia_medica |
                   emergenza_118 | casa_di_comunita | rsa
```

---

## 4. Frontend

### 4.1 Architettura

SPA (Single Page Application) senza build step. Tutto il frontend e' servito come file statici da FastAPI.

- **Framework UI:** Alpine.js 3.14 (reattivita' inline via direttive `x-data`, `x-for`, `x-show`, ecc.)
- **CSS:** Tailwind CSS via CDN
- **Calendario:** FullCalendar 6.1 (locale italiano)
- **Routing:** Client-side tramite hash fragment (`window.location.hash`)

### 4.2 Pagine

| Route | Pagina | Componente Alpine | Funzione |
|-------|--------|-------------------|----------|
| `#/` | Dashboard | `dashboardPage` | KPI (medici, strutture, turni mensili, non assegnati), tabella turni incompleti |
| `#/medici` | Medici | `doctorsPage` | Lista paginata, ricerca client-side, pannello dettaglio |
| `#/strutture` | Strutture | `institutionsPage` | Vista a fisarmonica con sedi e dettagli |
| `#/calendario` | Calendario | `calendarPage` | Calendario FullCalendar, modale dettaglio turno, assegnamenti |

### 4.3 Componente Calendario (il piu' complesso)

Il calendario (`calendar.js`, 276 righe) e' il centro operativo:

1. **Selettore sede** — dropdown per filtrare turni per sede
2. **Vista calendario** — FullCalendar con viste mese e settimana
3. **Modale dettaglio turno** — click su un evento apre:
   - Dettagli turno (data, orario, tipo, paga, stato)
   - Assegnamenti correnti (con bottone rimuovi)
   - Medici eleggibili ordinati per score con:
     - Badge ranking (#1-#3 evidenziati)
     - Barra punteggio (0-100%) con gradiente colore
     - Breakdown punteggio in tooltip
     - Tag competenze (certificazioni, lingue, lavoro autonomo, ecc.)
     - Warning di eleggibilita'
     - Bottone "Assegna"
4. **Modale aggiungi struttura** — form rapido per creare struttura + sede
5. **Modale aggiungi medico** — form rapido per creare medico

**Colori stato turno:**
- `open` → blu, `partially_filled` → giallo, `filled` → verde
- `draft` → grigio, `in_progress` → viola, `completed` → teal, `cancelled` → rosso

### 4.4 Client API

`api.js` (30 righe) — wrapper minimale su `fetch`:

```javascript
const API = {
    BASE: '/api/v1',
    async request(method, path, body, params) { ... },
    get(path, params)  { return this.request('GET', path, null, params) },
    post(path, body)   { return this.request('POST', path, body) },
    patch(path, body)  { return this.request('PATCH', path, body) },
    del(path)          { return this.request('DELETE', path) },
}
```

- Query params costruiti con `URLSearchParams`
- Risposte 204 (No Content) ritornano `null`
- Errori parsano `err.detail` dal JSON di risposta

---

## 5. Base di Dati

### 5.1 Modello ER

```
doctors ──────┬── doctor_certifications ──── certification_types
              ├── doctor_languages ────────── languages
              ├── doctor_preferences
              ├── doctor_availabilities
              ├── doctor_unavailabilities
              └── shift_assignments ─────┐
                                         │
institutions ─┬── institution_sites ─────┼── shifts ──┬── shift_requirements ──── certification_types
              ├── institution_requirements│            ├── shift_language_requirements ── languages
              └── institution_language_requirements    └── shift_templates
                                         │
                               code_levels (lookup)
```

### 5.2 Tabelle Principali

#### `doctors`
- `id` UUID PK
- `fiscal_code` VARCHAR(16) UNIQUE — codice fiscale
- `first_name`, `last_name` VARCHAR(100)
- `email` VARCHAR(255) UNIQUE
- `phone` VARCHAR(20) nullable
- `password_hash` VARCHAR(255)
- `lat`, `lon` FLOAT nullable — coordinate per calcolo distanza
- `max_distance_km` FLOAT default 50.0
- `is_active` BOOL default TRUE
- `willing_to_relocate`, `willing_overnight_stay` BOOL
- `max_shifts_per_month` INT default 20
- `max_night_shifts_per_month` INT nullable
- `max_code_level_id` FK → code_levels
- `can_work_alone`, `can_emergency_vehicle` BOOL
- `years_experience` INT default 0
- `created_at`, `updated_at` TIMESTAMP

#### `institutions`
- `id` UUID PK
- `name` VARCHAR(200)
- `tax_code` VARCHAR(16) UNIQUE — partita IVA / codice fiscale
- `address`, `city` VARCHAR, `province` VARCHAR(2)
- `institution_type` VARCHAR(50) — enum InstitutionType
- `is_active` BOOL default TRUE

#### `institution_sites`
- `id` UUID PK
- `institution_id` FK → institutions CASCADE
- `name`, `address`, `city`, `province`
- `lat`, `lon` FLOAT — coordinate sede
- `lodging_available`, `meal_support`, `parking_available` BOOL
- `min_code_level_id` FK → code_levels
- `requires_independent_work`, `requires_emergency_vehicle` BOOL
- `min_years_experience` INT default 0

#### `shifts`
- `id` UUID PK
- `template_id` FK → shift_templates SET NULL
- `site_id` FK → institution_sites CASCADE
- `date` DATE, `start_datetime` DATETIME, `end_datetime` DATETIME
- `required_doctors` INT default 1
- `status` ENUM ShiftStatus
- `base_pay` FLOAT, `urgent_multiplier` FLOAT default 1.0
- `is_night` BOOL
- `shift_type` VARCHAR(20)
- `priority` INT default 3
- `min_code_level_id` FK, `requires_independent_work`, `requires_emergency_vehicle` BOOL
- `min_years_experience` INT

#### `shift_assignments`
- `id` UUID PK
- `shift_id` FK → shifts CASCADE (UNIQUE con doctor_id)
- `doctor_id` FK → doctors CASCADE
- `status` ENUM AssignmentStatus
- `pay_amount` FLOAT
- `assigned_at`, `responded_at` DATETIME

#### `doctor_availabilities`
- `doctor_id` FK, `date` DATE, `start_time` TIME, `end_time` TIME
- `availability_type` ENUM: available | preferred | reluctant
- UNIQUE (doctor_id, date, start_time, end_time)

#### `doctor_unavailabilities`
- `doctor_id` FK, `start_date` DATE, `end_date` DATE
- `reason` ENUM: vacation | sick_leave | personal | training | other
- `is_approved` BOOL default FALSE

### 5.3 Tabelle Lookup

- `certification_types` — id, name, description, validity_months
- `languages` — id, code (es. "it", "en"), name
- `code_levels` — id, code (es. "rosso", "giallo"), description, severity_order

### 5.4 Migrazioni

Gestite con Alembic (`/alembic/`):
- `001_initial_schema.py` — Schema iniziale completo
- `002_add_enum_types.py` — Tipi enum per campi status

Eseguite automaticamente all'avvio (`start.sh`): `alembic upgrade head`

---

## 6. Deployment

### 6.1 Docker

**Dockerfile** (multi-layer):
```dockerfile
FROM python:3.12-slim
# Installa gcc + libpq-dev per asyncpg
# Copia pyproject.toml e installa dipendenze
# Copia codice sorgente
# EXPOSE 8000
# CMD ["./start.sh"]
```

**docker-compose.yml** (sviluppo locale):
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: shiftmanager
      POSTGRES_PASSWORD: shiftmanager
      POSTGRES_DB: shiftmanager
    ports: ["5432:5432"]
    healthcheck: pg_isready

  api:
    build: .
    ports: ["8000:8000"]
    depends_on:
      db: { condition: service_healthy }
    volumes: [".:/app"]  # Live reload
```

### 6.2 Sequenza di Avvio (`start.sh`)

1. Verifica connessione database (retry fino a 30 tentativi, 2s intervallo)
2. Esegue migrazioni Alembic (`alembic upgrade head`)
3. Esegue seed dati lookup (`python -m app.utils.seed`)
4. Genera dati demo (`python -m app.utils.generate_data`)
5. Avvia uvicorn sulla porta `$PORT` (default 8000)

### 6.3 Railway

Configurazione in `railway.toml`:
- Builder: Dockerfile
- Health check: `GET /health`
- Restart policy: on_failure (max 3 retry)

Railway fornisce automaticamente la variabile `DATABASE_URL` (PostgreSQL). Il codice converte `postgresql://` in `postgresql+asyncpg://` per compatibilita' con SQLAlchemy async.

---

## 7. Configurazione

### Variabili d'Ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://shiftmanager:shiftmanager@localhost:5432/shiftmanager` | URL database PostgreSQL |
| `SECRET_KEY` | `change-me-in-production` | Chiave per JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | Durata token |
| `MIN_REST_HOURS` | `11` | Ore minime di riposo tra turni |
| `MAX_CONSECUTIVE_DAYS` | `6` | Giorni consecutivi massimi |
| `MAX_NIGHT_SHIFTS_PER_MONTH` | `8` | Turni notturni massimi al mese |
| `PORT` | `8000` | Porta del server (usata da start.sh) |

Le variabili sono lette da file `.env` (se presente) tramite `pydantic-settings`.

### Dipendenze Principali (`pyproject.toml`)

**Runtime:** fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-jose, passlib[bcrypt]

**Dev:** pytest, pytest-asyncio, httpx, aiosqlite

**Python:** >=3.12
