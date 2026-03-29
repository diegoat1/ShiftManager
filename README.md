# ShiftManager

ShiftManager is a FastAPI application for managing medical shift operations for Italian healthcare institutions. In its current state, it behaves as a single deployable web app:

- The backend exposes a JSON API under `/api/v1`.
- The frontend is a static single-page app served from `/`.
- The same service also exposes `/health` for deployment health checks.

## Current Product Scope

The product is organized around four main business areas:

1. Doctors
2. Institutions and sites
3. Shifts and calendar
4. Assignment eligibility and ranking

Today the application is already usable as a demo or operational prototype for:

- viewing doctors and their profile details
- viewing institutions and their sites
- viewing monthly shifts in a calendar by site
- checking which shifts are open, partially filled, or filled
- ranking eligible doctors for a shift
- assigning or removing doctors from a shift
- creating institutions and doctors from the UI calendar page

## How The App Works Today

### 1. Entry points

- `GET /` serves the frontend
- `GET /health` returns `{"status": "ok"}`
- `GET /api/v1/...` serves the API

The frontend uses hash-based routes, so these links are directly shareable:

- `/`
- `/#/medici`
- `/#/strutture`
- `/#/calendario`

### 2. Frontend experience

The UI is a lightweight SPA built with:

- Alpine.js
- Tailwind via CDN
- FullCalendar

Available sections:

- `Dashboard`: high-level counters and incomplete shifts
- `Medici`: paginated doctor list, search, and doctor detail panel
- `Strutture`: institutions with expandable site details
- `Calendario`: site filter, monthly calendar, shift modal, assignment actions, and quick-create forms

### 3. Backend architecture

The backend follows a clean split:

- `app/api`: HTTP routes
- `app/services`: business orchestration
- `app/repositories`: database access
- `app/models`: SQLAlchemy models
- `app/schemas`: request/response contracts
- `app/rules`: eligibility and scoring rules
- `alembic`: database migrations

### 4. Main entities

The domain model currently includes:

- doctors
- doctor certifications
- doctor languages
- doctor preferences
- institutions
- institution sites
- shift requirements
- shift language requirements
- doctor availability and unavailability
- shifts
- shift assignments
- lookup tables for certification types, languages, and code levels

## Business Logic Implemented

### Eligibility checks

Before a doctor can be assigned, the system checks:

- active doctor status
- declared availability in the requested time slot
- mandatory certifications
- certification expiry
- required languages
- distance vs doctor travel limit
- overlapping shifts
- minimum rest time between shifts
- maximum consecutive work days
- monthly night-shift limit
- code level compatibility
- ability to work independently
- emergency vehicle capability
- minimum years of experience
- doctor monthly shift cap
- doctor personal night-shift cap

### Ranking logic

Eligible doctors are then scored and ranked using:

- availability type
- shift preference fit
- site affinity
- workload balance
- distance
- extra qualifications

The calendar modal already shows:

- current assignments
- eligible doctors
- rank
- total score
- scoring breakdown
- warnings for non-blocking issues

## Data And Demo Behavior

On startup the service does more than boot the API:

1. waits for the database
2. runs Alembic migrations
3. seeds lookup data
4. generates demo data if the database is empty

The current demo generation behavior is important:

- reference data is seeded automatically
- demo data is generated only if there are no doctors yet
- demo shifts are generated for April 2026
- the generator creates 50 doctors, 6 institutions, multiple sites, availability records, and a monthly shift set

This means a fresh deployment can be shown immediately without manual data entry.

## Deployment Model

The repository is configured for:

- local development with Docker Compose
- production-style deployment on Railway

Expected environment variables:

- `DATABASE_URL`
- `SECRET_KEY`

The app expects PostgreSQL in normal operation. Railway-specific handling already converts `postgresql://` to `postgresql+asyncpg://` when needed.

## Current Strengths

- backend and frontend are already integrated in one service
- useful demo data is generated automatically
- assignment decisions are not random; they are explainable
- the product has a strong demo surface in the calendar modal
- the root URL is easy to share because there is no separate frontend deployment

## Current Limitations

These are relevant when presenting the product to someone else:

- there is no authentication or role system enforced in the current UI flow
- sharing the public URL means sharing full access to the exposed demo or environment
- the seeded demo month is fixed to April 2026
- the UI currently supports some create flows, but not full admin editing everywhere
- automated test files exist, but I could not execute them in this environment because `pytest` is not installed here

## Recommended Use Right Now

The project is in a good state for:

- a product demo
- internal validation with partners
- showing operational logic to a healthcare stakeholder
- collecting feedback on matching rules and workflow

It is not yet in a state where a public unrestricted production share is advisable without:

- authentication
- environment separation
- access control
- a review of seeded/demo behavior

## Local Run

### Docker

```bash
docker compose up --build
```

Then open:

- `http://localhost:8000/`

### Direct Python run

Install the project and run the app with a PostgreSQL database configured in `.env`, then start:

```bash
uvicorn app.main:app --reload
```

## Suggested Next Documentation

For operational sharing and outbound product presentation, see:

- `docs/share-workflow.md`
