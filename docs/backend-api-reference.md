# ShiftManager - Backend API Reference

> Base URL: `http://localhost:8000`
> Todas las rutas (excepto Auth) usan el prefijo `/api/v1`
> Autenticacion: Bearer JWT token en header `Authorization: Bearer <token>`

---

## Tabla de Contenidos

1. [Autenticacion](#1-autenticacion)
2. [Medicos (Admin)](#2-medicos-gestion-admin)
3. [Perfil del Medico (Self)](#3-perfil-del-medico-self)
4. [Instituciones](#4-instituciones)
5. [Turnos y Calendario](#5-turnos-y-calendario)
6. [Disponibilidad](#6-disponibilidad)
7. [Asignaciones](#7-asignaciones)
8. [Ofertas de Turno](#8-ofertas-de-turno)
9. [Documentos](#9-documentos)
10. [Notificaciones](#10-notificaciones)
11. [Analytics y KPIs](#11-analytics-y-kpis)
12. [Audit Log](#12-audit-log)
13. [Datos de Referencia (Lookups)](#13-datos-de-referencia-lookups)
14. [Enums](#14-enums)
15. [Roles y Permisos](#15-roles-y-permisos)

---

## 1. Autenticacion

### `POST /auth/login`

Inicia sesion y obtiene un token JWT.

**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

---

### `POST /auth/register`

Registra un nuevo usuario. Si el rol es `medico`, crea tambien el perfil de doctor.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "string",
  "role": "medico",
  "fiscal_code": "string | null",
  "first_name": "string | null",
  "last_name": "string | null",
  "phone": "string | null"
}
```

**Response 201:** `LoginResponse` (mismo formato que login)

---

### `GET /auth/me`

Devuelve el usuario autenticado actual. **Requiere auth.**

**Response 200:**
```json
{
  "id": "uuid",
  "email": "string",
  "role": "medico | admin | superadmin | coordinatore | operatore",
  "is_active": true,
  "last_login_at": "datetime | null",
  "created_at": "datetime"
}
```

---

## 2. Medicos (Gestion Admin)

> Todos los endpoints requieren rol admin (superadmin, admin, coordinatore).

### `POST /api/v1/doctors/`

Crea un nuevo medico.

**Request Body:**
```json
{
  "fiscal_code": "string (obligatorio)",
  "first_name": "string (obligatorio)",
  "last_name": "string (obligatorio)",
  "email": "string (obligatorio)",
  "password": "string (obligatorio)",
  "phone": "string | null",
  "lat": "float | null",
  "lon": "float | null",
  "max_distance_km": 50.0,
  "willing_to_relocate": false,
  "willing_overnight_stay": false,
  "max_shifts_per_month": 20,
  "max_night_shifts_per_month": "int | null",
  "max_code_level_id": "int | null",
  "can_work_alone": false,
  "can_emergency_vehicle": false,
  "years_experience": 0
}
```

**Response 201:** `DoctorRead` (ver formato abajo)

---

### `GET /api/v1/doctors/`

Lista todos los medicos (version breve).

**Query Params:**
| Param | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `skip` | int | 0 | Offset de paginacion |
| `limit` | int | 50 | Cantidad por pagina |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "fiscal_code": "RSSMRA85M01H501Z",
      "first_name": "Mario",
      "last_name": "Rossi",
      "email": "mario@example.com",
      "is_active": true
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 50
}
```

---

### `GET /api/v1/doctors/{doctor_id}`

Detalle completo de un medico.

**Response 200 - `DoctorRead`:**
```json
{
  "id": "uuid",
  "fiscal_code": "RSSMRA85M01H501Z",
  "first_name": "Mario",
  "last_name": "Rossi",
  "email": "mario@example.com",
  "phone": "string | null",
  "lat": 41.9028,
  "lon": 12.4964,
  "max_distance_km": 50.0,
  "is_active": true,
  "willing_to_relocate": false,
  "willing_overnight_stay": false,
  "max_shifts_per_month": 20,
  "max_night_shifts_per_month": "int | null",
  "max_code_level_id": "int | null",
  "can_work_alone": false,
  "can_emergency_vehicle": false,
  "years_experience": 5,
  "birth_date": "1985-01-01 | null",
  "residence_address": "string | null",
  "domicile_city": "string | null",
  "homologation_status": "pending | approved | suspended | revoked",
  "ordine_province": "RM | null",
  "ordine_number": "string | null",
  "has_own_vehicle": false,
  "profile_completion_percent": 75,
  "created_at": "2024-01-15T10:30:00",
  "certifications": [
    {
      "id": 1,
      "certification_type_id": 2,
      "certification_type": {
        "id": 2,
        "name": "ACLS",
        "description": "Advanced Cardiovascular Life Support",
        "validity_months": 24
      },
      "obtained_date": "2023-06-15",
      "expiry_date": "2025-06-15",
      "is_active": true
    }
  ],
  "languages": [
    {
      "id": 1,
      "language_id": 1,
      "language": {
        "id": 1,
        "code": "it",
        "name": "Italiano"
      },
      "proficiency_level": 5
    }
  ],
  "preferences": {
    "id": 1,
    "doctor_id": "uuid",
    "prefers_day": true,
    "prefers_night": false,
    "prefers_weekends": false,
    "avoids_weekends": false,
    "preferred_institution_types": "pronto_soccorso,guardia_medica | null",
    "preferred_code_levels": "string | null",
    "min_pay_per_shift": 150.0,
    "max_preferred_distance_km": 30.0
  }
}
```

---

### `PATCH /api/v1/doctors/{doctor_id}`

Actualiza datos del medico. Solo enviar campos a modificar.

**Request Body - `DoctorUpdate`:**
```json
{
  "first_name": "string | null",
  "last_name": "string | null",
  "email": "string | null",
  "phone": "string | null",
  "lat": "float | null",
  "lon": "float | null",
  "max_distance_km": "float | null",
  "is_active": "bool | null",
  "willing_to_relocate": "bool | null",
  "willing_overnight_stay": "bool | null",
  "max_shifts_per_month": "int | null",
  "max_night_shifts_per_month": "int | null",
  "max_code_level_id": "int | null",
  "can_work_alone": "bool | null",
  "can_emergency_vehicle": "bool | null",
  "years_experience": "int | null",
  "birth_date": "date | null",
  "residence_address": "string | null",
  "domicile_city": "string | null",
  "ordine_province": "string | null",
  "ordine_number": "string | null",
  "has_own_vehicle": "bool | null"
}
```

**Response 200:** `DoctorRead`

---

### `DELETE /api/v1/doctors/{doctor_id}`

Elimina un medico. **Response 204** (sin cuerpo).

---

### `POST /api/v1/doctors/{doctor_id}/certifications`

Agrega una certificacion al medico.

**Request Body:**
```json
{
  "certification_type_id": 1,
  "obtained_date": "2023-06-15",
  "expiry_date": "2025-06-15 | null"
}
```

**Response 201:**
```json
{
  "id": 1,
  "certification_type_id": 1,
  "certification_type": { "id": 1, "name": "BLS", "description": "...", "validity_months": 24 },
  "obtained_date": "2023-06-15",
  "expiry_date": "2025-06-15",
  "is_active": true
}
```

### `DELETE /api/v1/doctors/{doctor_id}/certifications/{cert_type_id}`

Elimina certificacion. **Response 204.**

---

### `POST /api/v1/doctors/{doctor_id}/languages`

Agrega un idioma al medico.

**Request Body:**
```json
{
  "language_id": 1,
  "proficiency_level": 3
}
```

**Response 201:**
```json
{
  "id": 1,
  "language_id": 1,
  "language": { "id": 1, "code": "en", "name": "English" },
  "proficiency_level": 3
}
```

### `DELETE /api/v1/doctors/{doctor_id}/languages/{language_id}`

Elimina idioma. **Response 204.**

---

## 3. Perfil del Medico (Self)

> Endpoints para que el medico gestione su propio perfil. Requiere rol `medico`.

### `GET /api/v1/me/profile`

**Response 200:** `DoctorRead` (mismo formato que el detalle admin)

---

### `PATCH /api/v1/me/profile`

Actualiza su propio perfil (campos limitados, no puede cambiar email ni is_active).

**Request Body - `DoctorProfileUpdate`:**
```json
{
  "first_name": "string | null",
  "last_name": "string | null",
  "phone": "string | null",
  "lat": "float | null",
  "lon": "float | null",
  "max_distance_km": "float | null",
  "willing_to_relocate": "bool | null",
  "willing_overnight_stay": "bool | null",
  "max_shifts_per_month": "int | null",
  "max_night_shifts_per_month": "int | null",
  "birth_date": "date | null",
  "residence_address": "string | null",
  "domicile_city": "string | null",
  "ordine_province": "string | null",
  "ordine_number": "string | null",
  "has_own_vehicle": "bool | null"
}
```

**Response 200:** `DoctorRead`

---

## 4. Instituciones

### `POST /api/v1/institutions/` (Admin)

**Request Body:**
```json
{
  "name": "Ospedale San Camillo",
  "tax_code": "12345678901",
  "address": "Via Roma 1",
  "city": "Roma",
  "province": "RM",
  "institution_type": "pronto_soccorso | punto_primo_intervento | guardia_medica | emergenza_118 | casa_di_comunita | rsa"
}
```

**Response 201:** `InstitutionRead`

---

### `GET /api/v1/institutions/`

Lista instituciones con sus sedes.

**Query Params:** `skip` (default 0), `limit` (default 50)

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Ospedale San Camillo",
      "tax_code": "12345678901",
      "address": "Via Roma 1",
      "city": "Roma",
      "province": "RM",
      "institution_type": "pronto_soccorso",
      "is_active": true,
      "created_at": "2024-01-10T08:00:00",
      "sites": [
        {
          "id": "uuid",
          "institution_id": "uuid",
          "name": "Sede Centrale",
          "address": "Via Roma 1",
          "city": "Roma",
          "province": "RM",
          "lat": 41.8902,
          "lon": 12.4922,
          "is_active": true,
          "lodging_available": false,
          "meal_support": true,
          "parking_available": true,
          "min_code_level_id": 2,
          "requires_independent_work": false,
          "requires_emergency_vehicle": false,
          "min_years_experience": 2,
          "created_at": "2024-01-10T08:00:00"
        }
      ]
    }
  ],
  "total": 15,
  "skip": 0,
  "limit": 50
}
```

---

### `GET /api/v1/institutions/{institution_id}`

**Response 200:** `InstitutionRead` (mismo formato, incluye sites)

### `PATCH /api/v1/institutions/{institution_id}` (Admin)

**Request Body - `InstitutionUpdate`:**
```json
{
  "name": "string | null",
  "address": "string | null",
  "city": "string | null",
  "province": "string | null",
  "institution_type": "string | null",
  "is_active": "bool | null"
}
```

### `DELETE /api/v1/institutions/{institution_id}` (Admin)

**Response 204.**

---

### Sedes (Sites)

#### `POST /api/v1/institutions/{institution_id}/sites` (Admin)

**Request Body - `SiteCreate`:**
```json
{
  "name": "Sede Nord",
  "address": "Via Milano 10",
  "city": "Roma",
  "province": "RM",
  "lat": 41.92,
  "lon": 12.50,
  "lodging_available": false,
  "meal_support": false,
  "parking_available": true,
  "min_code_level_id": "int | null",
  "requires_independent_work": false,
  "requires_emergency_vehicle": false,
  "min_years_experience": 0
}
```

**Response 201:** `SiteRead`

#### `GET /api/v1/institutions/{institution_id}/sites`

**Response 200:** `list[SiteRead]`

#### `PATCH /api/v1/institutions/sites/{site_id}`

**Request Body:** `SiteUpdate` (todos los campos opcionales)

---

### Requisitos de Institucion

#### `POST /api/v1/institutions/{institution_id}/requirements`

```json
{ "certification_type_id": 1, "is_mandatory": true }
```

**Response 201:**
```json
{ "id": 1, "institution_id": "uuid", "certification_type_id": 1, "is_mandatory": true }
```

#### `GET /api/v1/institutions/{institution_id}/requirements`

**Response 200:** `list[RequirementRead]`

#### `POST /api/v1/institutions/{institution_id}/language-requirements`

```json
{ "language_id": 1, "min_proficiency": 3 }
```

**Response 201:**
```json
{ "id": 1, "institution_id": "uuid", "language_id": 1, "min_proficiency": 3 }
```

#### `GET /api/v1/institutions/{institution_id}/language-requirements`

**Response 200:** `list[LanguageRequirementRead]`

---

## 5. Turnos y Calendario

### `POST /api/v1/shifts/` (Admin)

**Request Body - `ShiftCreate`:**
```json
{
  "site_id": "uuid",
  "template_id": "uuid | null",
  "date": "2024-03-15",
  "start_datetime": "2024-03-15T08:00:00",
  "end_datetime": "2024-03-15T20:00:00",
  "required_doctors": 1,
  "base_pay": 250.0,
  "urgent_multiplier": 1.0,
  "is_night": false,
  "shift_type": "day | night | evening | weekend_day | weekend_night | null",
  "priority": 3,
  "min_code_level_id": "int | null",
  "requires_independent_work": false,
  "requires_emergency_vehicle": false,
  "min_years_experience": 0
}
```

**Response 201:** `ShiftRead`

---

### `GET /api/v1/shifts/`

**Query Params:** `skip` (default 0), `limit` (default 50)

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "site_id": "uuid",
      "template_id": "uuid | null",
      "date": "2024-03-15",
      "start_datetime": "2024-03-15T08:00:00",
      "end_datetime": "2024-03-15T20:00:00",
      "required_doctors": 1,
      "status": "open",
      "base_pay": 250.0,
      "urgent_multiplier": 1.0,
      "is_night": false,
      "shift_type": "day",
      "priority": 3,
      "min_code_level_id": 2,
      "requires_independent_work": false,
      "requires_emergency_vehicle": false,
      "min_years_experience": 0,
      "created_at": "2024-03-01T10:00:00"
    }
  ],
  "total": 120,
  "skip": 0,
  "limit": 50
}
```

---

### `GET /api/v1/shifts/{shift_id}`

**Response 200:** `ShiftRead`

### `PATCH /api/v1/shifts/{shift_id}` (Admin)

**Request Body - `ShiftUpdate`:**
```json
{
  "required_doctors": "int | null",
  "status": "draft | open | partially_filled | filled | ... | null",
  "base_pay": "float | null",
  "urgent_multiplier": "float | null",
  "shift_type": "string | null",
  "priority": "int | null",
  "min_code_level_id": "int | null",
  "requires_independent_work": "bool | null",
  "requires_emergency_vehicle": "bool | null",
  "min_years_experience": "int | null"
}
```

### `DELETE /api/v1/shifts/{shift_id}` (Admin)

**Response 204.**

---

### Calendario por Sede

#### `GET /api/v1/shifts/calendar/{site_id}`

Obtiene turnos de una sede en un rango de fechas.

**Query Params (obligatorios):**
| Param | Tipo | Descripcion |
|-------|------|-------------|
| `start` | date | Fecha inicio (YYYY-MM-DD) |
| `end` | date | Fecha fin (YYYY-MM-DD) |

**Response 200:** `list[ShiftRead]`

---

### Requisitos de Turno

#### `POST /api/v1/shifts/{shift_id}/requirements`

```json
{ "certification_type_id": 1, "is_mandatory": true }
```

#### `POST /api/v1/shifts/{shift_id}/language-requirements`

```json
{ "language_id": 1, "min_proficiency": 3 }
```

---

### Templates (Plantillas de Turno)

#### `POST /api/v1/shifts/templates`

**Request Body:**
```json
{
  "site_id": "uuid",
  "name": "Turno Mattina",
  "start_time": "08:00:00",
  "end_time": "20:00:00",
  "required_doctors": 1,
  "base_pay": 250.0,
  "is_night": false
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "site_id": "uuid",
  "name": "Turno Mattina",
  "start_time": "08:00:00",
  "end_time": "20:00:00",
  "required_doctors": 1,
  "base_pay": 250.0,
  "is_night": false
}
```

#### `GET /api/v1/shifts/templates/{site_id}`

**Response 200:** `list[TemplateRead]`

---

### Generacion Masiva de Turnos

#### `POST /api/v1/shifts/generate` (Admin)

Genera turnos automaticamente desde templates en un rango de fechas.

**Request Body:**
```json
{
  "site_id": "uuid",
  "template_ids": ["uuid", "uuid"],
  "start_date": "2024-03-01",
  "end_date": "2024-03-31"
}
```

**Response 200:** `list[ShiftRead]` (turnos generados)

---

## 6. Disponibilidad

### `POST /api/v1/doctors/{doctor_id}/availability`

Marca disponibilidad para un slot especifico.

**Request Body:**
```json
{
  "date": "2024-03-15",
  "start_time": "08:00:00",
  "end_time": "20:00:00",
  "availability_type": "available | preferred | reluctant"
}
```

**Response 201:**
```json
{
  "id": 1,
  "doctor_id": "uuid",
  "date": "2024-03-15",
  "start_time": "08:00:00",
  "end_time": "20:00:00",
  "availability_type": "available"
}
```

---

### `POST /api/v1/doctors/{doctor_id}/availability/bulk`

Crea multiples slots de disponibilidad.

**Request Body:**
```json
{
  "entries": [
    { "date": "2024-03-15", "start_time": "08:00", "end_time": "20:00", "availability_type": "available" },
    { "date": "2024-03-16", "start_time": "20:00", "end_time": "08:00", "availability_type": "preferred" }
  ]
}
```

**Response 201:** `list[AvailabilityRead]`

---

### `GET /api/v1/doctors/{doctor_id}/availability`

**Query Params (obligatorios):**
| Param | Tipo | Descripcion |
|-------|------|-------------|
| `start` | date | Fecha inicio |
| `end` | date | Fecha fin |

**Response 200:** `list[AvailabilityRead]`

---

### `POST /api/v1/doctors/{doctor_id}/unavailability`

Marca un periodo de indisponibilidad.

**Request Body:**
```json
{
  "start_date": "2024-04-01",
  "end_date": "2024-04-15",
  "reason": "vacation | sick_leave | personal | training | other"
}
```

**Response 201:**
```json
{
  "id": 1,
  "doctor_id": "uuid",
  "start_date": "2024-04-01",
  "end_date": "2024-04-15",
  "reason": "vacation",
  "is_approved": false
}
```

### `GET /api/v1/doctors/{doctor_id}/unavailability`

**Query Params (opcionales):** `start`, `end`

**Response 200:** `list[UnavailabilityRead]`

---

## 7. Asignaciones

### `POST /api/v1/assignments/` (Admin)

Asigna un medico a un turno. Valida elegibilidad automaticamente.

**Request Body:**
```json
{
  "shift_id": "uuid",
  "doctor_id": "uuid",
  "pay_amount": 250.0
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "shift_id": "uuid",
  "doctor_id": "uuid",
  "status": "proposed",
  "pay_amount": 250.0,
  "assigned_at": "2024-03-10T14:00:00",
  "responded_at": null
}
```

**Error 400** (si no es elegible):
```json
{
  "message": "Doctor is not eligible for this shift",
  "eligibility": {
    "is_eligible": false,
    "reasons": ["Missing required certification: ACLS", "Distance exceeds max (75km > 50km)"],
    "warnings": []
  }
}
```

---

### `DELETE /api/v1/assignments/{assignment_id}` (Admin)

**Response 204.**

---

### `GET /api/v1/assignments/check/{doctor_id}/{shift_id}`

Verifica si un medico es elegible para un turno.

**Response 200:**
```json
{
  "is_eligible": true,
  "reasons": [],
  "warnings": ["Doctor prefers day shifts, this is a night shift"]
}
```

---

### `GET /api/v1/assignments/eligible/{shift_id}`

Lista todos los medicos elegibles para un turno, rankeados por score.

**Response 200:**
```json
[
  {
    "doctor_id": "uuid",
    "first_name": "Mario",
    "last_name": "Rossi",
    "eligibility": {
      "is_eligible": true,
      "reasons": [],
      "warnings": []
    },
    "score": 85,
    "rank": 1,
    "breakdown": {
      "availability": 15,
      "shift_preference": 10,
      "site_affinity": 5,
      "workload_balance": 12,
      "distance": 18,
      "extra_qualifications": 10,
      "reliability": 8,
      "fairness": 5,
      "cost_efficiency": 2
    },
    "distance_km": 12.5,
    "certifications": ["BLS", "ACLS"],
    "languages": ["Italiano", "English"],
    "years_experience": 5,
    "can_work_alone": true,
    "can_emergency_vehicle": false
  }
]
```

---

### `GET /api/v1/assignments/shift/{shift_id}`

**Response 200:** `list[AssignmentRead]` - Todas las asignaciones de un turno.

### `GET /api/v1/assignments/doctor/{doctor_id}`

**Response 200:** `list[AssignmentRead]` - Todas las asignaciones de un medico.

---

## 8. Ofertas de Turno

### Gestion Admin

#### `POST /api/v1/shifts/{shift_id}/offers/send` (Admin)

Envia una oferta a un medico especifico.

**Request Body:**
```json
{
  "doctor_id": "uuid",
  "expires_in_hours": 12.0
}
```

**Response 201:** `OfferRead`

---

#### `POST /api/v1/shifts/{shift_id}/offers/send-batch` (Admin)

Envia ofertas masivas. Si `doctor_ids` esta vacio, auto-selecciona los N mejores elegibles.

**Request Body:**
```json
{
  "doctor_ids": ["uuid", "uuid"] ,
  "top_n": 3,
  "expires_in_hours": 12.0
}
```

**Response 201:** `list[OfferRead]`

---

#### `GET /api/v1/shifts/{shift_id}/offers/` (Admin)

**Response 200:** `list[OfferRead]`

#### `POST /api/v1/shifts/{shift_id}/offers/{offer_id}/cancel` (Admin)

**Response 200:** `OfferRead`

---

### Ofertas del Medico (Self)

#### `GET /api/v1/me/offers/`

Todas las ofertas recibidas por el medico.

#### `GET /api/v1/me/offers/pending`

Solo ofertas pendientes de respuesta.

**Response 200:**
```json
[
  {
    "id": "uuid",
    "shift_id": "uuid",
    "doctor_id": "uuid",
    "status": "proposed",
    "offered_at": "2024-03-10T14:00:00",
    "expires_at": "2024-03-11T02:00:00",
    "responded_at": null,
    "response_note": null,
    "rank_snapshot": 1,
    "score_snapshot": 85,
    "doctor_name": "Mario Rossi",
    "shift_date": "2024-03-15",
    "site_name": "Sede Centrale - Ospedale San Camillo"
  }
]
```

#### `POST /api/v1/me/offers/{offer_id}/accept`

**Response 200:** `OfferRead` con status `accepted`

#### `POST /api/v1/me/offers/{offer_id}/reject`

**Request Body (opcional):**
```json
{ "response_note": "No disponible esa fecha" }
```

**Response 200:** `OfferRead` con status `rejected`

---

## 9. Documentos

### Subida por el Medico

#### `POST /api/v1/me/documents/`

**Content-Type:** `multipart/form-data`

| Campo | Tipo | Obligatorio | Descripcion |
|-------|------|-------------|-------------|
| `file` | File | Si | PDF, JPEG o PNG |
| `document_type_id` | int | Si | ID del tipo de documento |
| `issued_at` | string | No | Fecha emision (YYYY-MM-DD) |
| `expires_at` | string | No | Fecha expiracion (YYYY-MM-DD) |

**Response 201:**
```json
{
  "id": "uuid",
  "doctor_id": "uuid",
  "document_type_id": 1,
  "document_type": {
    "id": 1,
    "code": "carta_identita",
    "name": "Carta d'Identita",
    "description": "Documento di identita",
    "validity_months": 120,
    "is_mandatory": true
  },
  "original_filename": "carta_identita.pdf",
  "file_size_bytes": 245000,
  "mime_type": "application/pdf",
  "uploaded_at": "2024-03-10T14:00:00",
  "issued_at": "2020-01-15",
  "expires_at": "2030-01-15",
  "verification_status": "pending",
  "verified_at": null,
  "rejection_reason": null,
  "created_at": "2024-03-10T14:00:00"
}
```

#### `GET /api/v1/me/documents/`

**Response 200:** `list[DocumentRead]`

#### `DELETE /api/v1/me/documents/{doc_id}`

**Response 204.**

---

### Verificacion Admin

#### `GET /api/v1/admin/documents/`

**Query Params:** `skip`, `limit`, `status` (filtrar por pending/approved/rejected/expired)

**Response 200:** `list[DocumentRead]`

#### `GET /api/v1/admin/documents/doctors/{doctor_id}`

**Response 200:** `list[DocumentRead]` del medico especifico.

#### `POST /api/v1/admin/documents/{doc_id}/approve`

**Response 200:** `DocumentRead` con status `approved`

#### `POST /api/v1/admin/documents/{doc_id}/reject`

**Request Body:**
```json
{ "status": "rejected", "rejection_reason": "Documento ilegible" }
```

**Response 200:** `DocumentRead` con status `rejected`

---

### Tipos de Documento

#### `GET /api/v1/document-types/`

**Response 200:**
```json
[
  {
    "id": 1,
    "code": "carta_identita",
    "name": "Carta d'Identita",
    "description": "Documento di identita valido",
    "validity_months": 120,
    "is_mandatory": true
  }
]
```

---

## 10. Notificaciones

> Requiere autenticacion.

### `GET /api/v1/me/notifications/`

**Query Params:** `skip` (default 0), `limit` (default 50)

**Response 200:**
```json
[
  {
    "id": "uuid",
    "type": "offer_received",
    "title": "Nueva oferta de turno",
    "body": "Tienes una oferta para el turno del 15/03 en Ospedale San Camillo",
    "status": "unread",
    "sent_at": "2024-03-10T14:00:00",
    "read_at": null,
    "related_entity_type": "shift_offer",
    "related_entity_id": "uuid"
  }
]
```

### `GET /api/v1/me/notifications/unread-count`

```json
{ "count": 5 }
```

### `PATCH /api/v1/me/notifications/{notification_id}/read`

```json
{ "ok": true }
```

### `POST /api/v1/me/notifications/read-all`

```json
{ "marked": 5 }
```

---

## 11. Analytics y KPIs

> Requieren rol admin.

### `GET /api/v1/admin/analytics/kpis`

**Response 200:**
```json
{
  "total_shifts": 350,
  "covered_shifts": 310,
  "coverage_percent": 88.57,
  "avg_fill_time_hours": 4.2,
  "total_offers_sent": 520,
  "acceptance_rate": 72.5,
  "active_doctors": 45,
  "total_assignments": 310
}
```

### `GET /api/v1/admin/analytics/kpis/by-month`

**Query Params:** `year` (int, opcional - default anno corrente)

**Response 200:**
```json
[
  {
    "month": "2024-01",
    "total_shifts": 120,
    "covered_shifts": 105,
    "coverage_percent": 87.5,
    "offers_sent": 180,
    "acceptance_rate": 70.0
  }
]
```

### `GET /api/v1/admin/analytics/doctor-stats`

**Query Params:** `skip`, `limit`

**Response 200:**
```json
[
  {
    "doctor_id": "uuid",
    "first_name": "Mario",
    "last_name": "Rossi",
    "total_offers_received": 25,
    "total_offers_accepted": 20,
    "total_offers_rejected": 3,
    "total_offers_expired": 2,
    "total_cancellations": 0,
    "avg_response_time_minutes": 45.5,
    "acceptance_rate": 80.0,
    "reliability_score": 92.5,
    "last_calculated_at": "2024-03-10T00:00:00"
  }
]
```

### `GET /api/v1/admin/analytics/doctor-stats/{doctor_id}`

**Response 200:** `DoctorStatsRead` (un solo medico)

### `POST /api/v1/admin/analytics/recalculate`

Recalcula scores de fiabilidad de todos los medicos.

```json
{ "recalculated": 45 }
```

---

## 12. Audit Log

> Requiere rol admin.

### `GET /api/v1/admin/audit-log/`

**Query Params:**
| Param | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `skip` | int | 0 | Offset |
| `limit` | int | 50 | Cantidad |
| `entity_type` | string | null | Filtrar por tipo (doctor, shift, etc.) |
| `entity_id` | string | null | Filtrar por ID de entidad |
| `action` | string | null | Filtrar por accion (create, update, delete) |

**Response 200:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "action": "update",
    "entity_type": "doctor",
    "entity_id": "uuid",
    "old_values": "{\"is_active\": true}",
    "new_values": "{\"is_active\": false}",
    "ip_address": "192.168.1.1",
    "created_at": "2024-03-10T14:00:00"
  }
]
```

---

## 13. Datos de Referencia (Lookups)

### Tipos de Certificacion

#### `GET /api/v1/lookups/certification-types`

```json
[
  { "id": 1, "name": "BLS", "description": "Basic Life Support", "validity_months": 24 },
  { "id": 2, "name": "ACLS", "description": "Advanced Cardiovascular Life Support", "validity_months": 24 }
]
```

#### `POST /api/v1/lookups/certification-types`

```json
{ "name": "PHTLS", "description": "Prehospital Trauma Life Support", "validity_months": 48 }
```

---

### Idiomas

#### `GET /api/v1/lookups/languages`

```json
[
  { "id": 1, "code": "it", "name": "Italiano" },
  { "id": 2, "code": "en", "name": "English" }
]
```

#### `POST /api/v1/lookups/languages`

```json
{ "code": "de", "name": "Deutsch" }
```

---

### Niveles de Codigo

#### `GET /api/v1/lookups/code-levels`

```json
[
  { "id": 1, "code": "bianco", "description": "Codice Bianco - Non urgente", "severity_order": 1 },
  { "id": 2, "code": "verde", "description": "Codice Verde - Poco urgente", "severity_order": 2 },
  { "id": 3, "code": "giallo", "description": "Codice Giallo - Urgente", "severity_order": 3 },
  { "id": 4, "code": "rosso", "description": "Codice Rosso - Emergenza", "severity_order": 4 }
]
```

#### `POST /api/v1/lookups/code-levels`

```json
{ "code": "arancione", "description": "Codice Arancione", "severity_order": 3 }
```

---

## 14. Enums

### ShiftStatus
| Valor | Descripcion |
|-------|-------------|
| `draft` | Borrador, no visible |
| `open` | Abierto, aceptando asignaciones |
| `partially_filled` | Parcialmente cubierto |
| `filled` | Completamente cubierto |
| `in_progress` | En curso |
| `completed` | Completado |
| `cancelled` | Cancelado |
| `proposing` | Enviando ofertas |
| `pending_confirmation` | Esperando confirmacion |
| `uncovered` | No cubierto (pasada la fecha) |

### AssignmentStatus
| Valor | Descripcion |
|-------|-------------|
| `proposed` | Propuesto al medico |
| `confirmed` | Confirmado |
| `rejected` | Rechazado |
| `cancelled` | Cancelado |
| `completed` | Completado |

### OfferStatus
| Valor | Descripcion |
|-------|-------------|
| `proposed` | Enviada, pendiente |
| `viewed` | Vista por el medico |
| `accepted` | Aceptada |
| `rejected` | Rechazada |
| `expired` | Expirada sin respuesta |
| `cancelled` | Cancelada por admin |

### AvailabilityType
| Valor | Descripcion |
|-------|-------------|
| `available` | Disponible |
| `preferred` | Preferido (quiere trabajar) |
| `reluctant` | Disponible pero reticente |

### UnavailabilityReason
`vacation` | `sick_leave` | `personal` | `training` | `other`

### UserRole
`superadmin` | `admin` | `coordinatore` | `operatore` | `medico`

### HomologationStatus
`pending` | `approved` | `suspended` | `revoked`

### VerificationStatus
`pending` | `approved` | `rejected` | `expired`

### InstitutionType
`pronto_soccorso` | `punto_primo_intervento` | `guardia_medica` | `emergenza_118` | `casa_di_comunita` | `rsa`

---

## 15. Roles y Permisos

| Endpoint | superadmin | admin | coordinatore | operatore | medico |
|----------|-----------|-------|-------------|-----------|--------|
| Auth (login/register) | - | - | - | - | - |
| GET instituciones/turnos/lookups | Si | Si | Si | Si | Si |
| CRUD medicos | Si | Si | Si | No | No |
| CRUD instituciones | Si | Si | Si | No | No |
| CRUD turnos | Si | Si | Si | No | No |
| Enviar ofertas | Si | Si | Si | No | No |
| Verificar documentos | Si | Si | Si | No | No |
| Analytics/KPIs | Si | Si | Si | No | No |
| Audit log | Si | Si | Si | No | No |
| Perfil propio (/me) | No | No | No | No | Si |
| Mis ofertas | No | No | No | No | Si |
| Mis documentos | No | No | No | No | Si |
| Notificaciones | Si | Si | Si | Si | Si |

---

## Paginacion

Todos los endpoints de lista soportan:

```
GET /api/v1/resource/?skip=0&limit=50
```

**Respuesta paginada:**
```json
{
  "items": [...],
  "total": 150,
  "skip": 0,
  "limit": 50
}
```

---

## Nota Importante: Sin Scoping Admin-Institucion

Actualmente **no existe** una relacion entre administradores e instituciones/medicos.
Cualquier usuario con rol admin puede gestionar todas las instituciones y todos los medicos del sistema.
No hay forma de saber que admin gestiona que instituciones o medicos.
