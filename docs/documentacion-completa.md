# ShiftManager — Documentación Completa

## Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura del Backend](#arquitectura-del-backend)
3. [Autenticación y Autorización](#autenticación-y-autorización)
4. [Endpoints del API](#endpoints-del-api)
5. [Frontend — Páginas y Funcionalidad](#frontend--páginas-y-funcionalidad)
6. [Motor de Eligibilidad](#motor-de-eligibilidad)
7. [Sistema de Scoring](#sistema-de-scoring)
8. [Base de Datos](#base-de-datos)

---

## Descripción General

ShiftManager es un sistema de gestión de turnos médicos para instituciones sanitarias italianas. Permite:

- **Gestionar médicos**, instituciones y sedes con sus requisitos
- **Crear y asignar turnos** con verificación automática de elegibilidad (16 checks)
- **Puntuar candidatos** con un sistema de scoring de 9 dimensiones (0-100 puntos)
- **Gestionar documentos** de médicos con workflow de aprobación
- **Enviar ofertas de turno** a médicos con flujo de aceptación/rechazo
- **Analizar KPIs** de cobertura, aceptación y fiabilidad

**Stack tecnológico:**
- Backend: Python 3.12 + FastAPI + SQLAlchemy async + PostgreSQL
- Frontend: Alpine.js + Tailwind CSS + FullCalendar (SPA con hash routing)
- Auth: JWT (JSON Web Tokens) con bcrypt
- Migraciones: Alembic
- Deploy: Docker + Railway

---

## Arquitectura del Backend

```
app/
├── api/              → Endpoints HTTP (routers FastAPI)
├── models/           → Modelos SQLAlchemy ORM (tablas de BD)
├── schemas/          → Schemas Pydantic (validación request/response)
├── services/         → Lógica de negocio (orquestación)
├── repositories/     → Capa de acceso a datos (queries SQL)
├── rules/            → Motor de elegibilidad y scoring
├── core/             → Configuración, DB engine, seguridad
├── utils/            → Enums, seed data, utilidades
├── static/           → Frontend SPA (HTML, JS, CSS)
└── tests/            → Suite de tests (72 tests)
```

### Flujo de una request:
```
Request → Router (api/) → Service (services/) → Repository (repositories/) → Database
                                               → Rules (rules/) para eligibilidad/scoring
```

---

## Autenticación y Autorización

### Cómo funciona

1. El usuario hace `POST /auth/login` con email y password
2. El backend valida credenciales y retorna un JWT token
3. El frontend almacena el token en `localStorage`
4. Cada request incluye el header `Authorization: Bearer <token>`
5. Los endpoints protegidos verifican el token y el rol del usuario

### Roles de usuario

| Rol | Permisos |
|-----|----------|
| `superadmin` | Acceso total a todo el sistema |
| `admin` | CRUD de médicos, instituciones, turnos, asignaciones, ofertas, documentos, analytics |
| `coordinatore` | Mismo que admin |
| `operatore` | Acceso básico (endpoints públicos) |
| `medico` | Portal propio: perfil, documentos, ofertas, notificaciones |

### Niveles de acceso en endpoints

- **Público**: Sin token requerido (listar instituciones, turnos, lookups)
- **Autenticado**: Token válido de cualquier rol
- **Admin**: Token con rol superadmin, admin, o coordinatore
- **Médico**: Token con rol medico (solo accede a sus propios datos)

---

## Endpoints del API

### Auth (raíz — sin prefijo `/api/v1`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/auth/login` | No | Login. Recibe `{email, password}`. Retorna `{access_token, token_type}` |
| `POST` | `/auth/register` | No | Registro. Recibe `{email, password, role, fiscal_code, first_name, last_name, phone}`. Si role=medico, crea también el perfil Doctor vinculado. Retorna JWT |
| `GET` | `/auth/me` | Sí | Retorna datos del usuario autenticado: `{id, email, role, is_active, last_login_at, created_at}` |

---

### Portal del Médico — Perfil (`/api/v1/me`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/me/profile` | Médico | Retorna el perfil completo del doctor vinculado al usuario: datos personales, certificaciones, idiomas, preferencias, % de completitud del perfil |
| `PATCH` | `/me/profile` | Médico | Actualiza campos del perfil: `first_name, last_name, phone, birth_date, residence_address, domicile_city, ordine_province, ordine_number, has_own_vehicle, max_distance_km, willing_to_relocate, willing_overnight_stay, max_shifts_per_month`. Recalcula automáticamente el `profile_completion_percent` |

---

### Portal del Médico — Documentos (`/api/v1/me/documents`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/me/documents/` | Médico | Lista todos los documentos del médico con su tipo y estado de verificación |
| `POST` | `/me/documents/` | Médico | Sube un documento. Acepta `multipart/form-data` con: `file` (PDF, JPEG, PNG, max 10MB), `document_type_id`, `issued_at` (opcional), `expires_at` (opcional). El archivo se guarda en `/uploads/{doctor_id}/`. Retorna el documento creado con estado `pending` |
| `DELETE` | `/me/documents/{doc_id}` | Médico | Elimina un documento propio. Solo permite eliminar documentos en estado `pending` |

---

### Portal del Médico — Ofertas (`/api/v1/me/offers`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/me/offers/` | Médico | Lista todas las ofertas recibidas (todas los estados) ordenadas por fecha |
| `GET` | `/me/offers/pending` | Médico | Lista solo las ofertas pendientes (status: proposed o viewed) ordenadas por expiración |
| `POST` | `/me/offers/{offer_id}/accept` | Médico | Acepta una oferta. Automáticamente crea un `ShiftAssignment` y actualiza el estado del turno. Solo funciona si la oferta está en status proposed/viewed |
| `POST` | `/me/offers/{offer_id}/reject` | Médico | Rechaza una oferta. Acepta `{response_note}` opcional. Solo funciona si la oferta está en status proposed/viewed |

---

### Portal del Médico — Notificaciones (`/api/v1/me/notifications`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/me/notifications/` | Autenticado | Lista notificaciones del usuario. Acepta `skip` y `limit` como query params. Retorna array de `{id, type, title, body, status, sent_at, read_at, related_entity_type, related_entity_id}` |
| `GET` | `/me/notifications/unread-count` | Autenticado | Retorna `{count: N}` con la cantidad de notificaciones no leídas |
| `PATCH` | `/me/notifications/{id}/read` | Autenticado | Marca una notificación como leída |
| `POST` | `/me/notifications/read-all` | Autenticado | Marca todas las notificaciones como leídas. Retorna `{marked: N}` |

---

### Gestión de Médicos (`/api/v1/doctors`) — Solo Admin

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/doctors/` | Admin | Crea un doctor. Recibe: `fiscal_code, first_name, last_name, email, password, phone, lat, lon, max_distance_km, willing_to_relocate, willing_overnight_stay, max_shifts_per_month, max_night_shifts_per_month, max_code_level_id, can_work_alone, can_emergency_vehicle, years_experience`. Retorna doctor completo con relaciones |
| `GET` | `/doctors/` | Admin | Lista doctores paginados. Query: `skip`, `limit`. Retorna `{items: [...], total, skip, limit}`. Cada item: `{id, fiscal_code, first_name, last_name, email, is_active}` |
| `GET` | `/doctors/{id}` | Admin | Retorna doctor completo con certificaciones, idiomas y preferencias |
| `PATCH` | `/doctors/{id}` | Admin | Actualiza campos del doctor |
| `DELETE` | `/doctors/{id}` | Admin | Elimina doctor (cascade elimina certificaciones, idiomas, preferencias) |
| `POST` | `/doctors/{id}/certifications` | Admin | Agrega certificación: `{certification_type_id, obtained_date, expiry_date}` |
| `DELETE` | `/doctors/{id}/certifications/{cert_type_id}` | Admin | Elimina certificación |
| `POST` | `/doctors/{id}/languages` | Admin | Agrega idioma: `{language_id, proficiency_level}` |
| `DELETE` | `/doctors/{id}/languages/{lang_id}` | Admin | Elimina idioma |

---

### Gestión de Instituciones (`/api/v1/institutions`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/institutions/` | Admin | Crea institución: `{name, tax_code, address, city, province, institution_type}` |
| `GET` | `/institutions/` | Público | Lista instituciones paginadas con sus sedes |
| `GET` | `/institutions/{id}` | Público | Detalle de institución |
| `PATCH` | `/institutions/{id}` | Admin | Actualiza institución |
| `DELETE` | `/institutions/{id}` | Admin | Elimina institución |
| `POST` | `/institutions/{id}/sites` | Admin | Crea sede: `{name, address, city, province, lat, lon, lodging_available, meal_support, parking_available, ...}` |
| `GET` | `/institutions/{id}/sites` | Público | Lista sedes de una institución |
| `PATCH` | `/institutions/sites/{site_id}` | Público | Actualiza sede |
| `POST` | `/institutions/{id}/requirements` | Público | Agrega requisito de certificación a la institución |
| `GET` | `/institutions/{id}/requirements` | Público | Lista requisitos de certificación |
| `POST` | `/institutions/{id}/language-requirements` | Público | Agrega requisito de idioma |
| `GET` | `/institutions/{id}/language-requirements` | Público | Lista requisitos de idioma |

---

### Gestión de Turnos (`/api/v1/shifts`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/shifts/` | Admin | Crea turno: `{site_id, date, start_datetime, end_datetime, required_doctors, base_pay, urgent_multiplier, is_night, shift_type, priority, min_code_level_id, ...}`. Los requisitos de la institución se copian automáticamente al turno |
| `GET` | `/shifts/` | Público | Lista turnos paginados |
| `GET` | `/shifts/{id}` | Público | Detalle del turno con requisitos |
| `PATCH` | `/shifts/{id}` | Admin | Actualiza turno |
| `DELETE` | `/shifts/{id}` | Admin | Elimina turno |
| `POST` | `/shifts/{id}/requirements` | Público | Agrega requisito de certificación al turno |
| `POST` | `/shifts/{id}/language-requirements` | Público | Agrega requisito de idioma al turno |
| `GET` | `/shifts/calendar/{site_id}?start=&end=` | Público | Retorna turnos de una sede en un rango de fechas (para el calendario) |
| `POST` | `/shifts/templates` | Público | Crea template de turno: `{site_id, name, start_time, end_time, required_doctors, base_pay, is_night}` |
| `GET` | `/shifts/templates/{site_id}` | Público | Lista templates de una sede |
| `POST` | `/shifts/generate` | Admin | Genera turnos masivamente desde templates para un rango de fechas |

---

### Asignaciones (`/api/v1/assignments`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/assignments/` | Admin | Asigna doctor a turno: `{shift_id, doctor_id, pay_amount}`. Ejecuta los 18 checks de elegibilidad antes de asignar. Si no es elegible, retorna 400 con los motivos. Actualiza automáticamente el estado del turno (open → partially_filled → filled) |
| `DELETE` | `/assignments/{id}` | Admin | Cancela asignación. Actualiza estado del turno |
| `GET` | `/assignments/check/{doctor_id}/{shift_id}` | Público | Verifica elegibilidad sin asignar. Retorna `{is_eligible, reasons[], warnings[]}` |
| `GET` | `/assignments/eligible/{shift_id}` | Público | Lista TODOS los doctores ordenados por elegibilidad y score. Elegibles primero (con ranking 1..N y score 0-100 con breakdown), luego inelegibles (con motivos). Incluye: distancia, certificaciones, idiomas, experiencia, capacidades |
| `GET` | `/assignments/shift/{shift_id}` | Público | Lista asignaciones de un turno |
| `GET` | `/assignments/doctor/{doctor_id}` | Público | Lista asignaciones de un doctor |

---

### Ofertas de Turno — Admin (`/api/v1/shifts/{shift_id}/offers`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/shifts/{id}/offers/send` | Admin | Envía oferta individual: `{doctor_id, expires_in_hours}`. Crea oferta con countdown de expiración. Cambia estado del turno a `proposing` |
| `POST` | `/shifts/{id}/offers/send-batch` | Admin | Envío masivo: `{doctor_ids, top_n, expires_in_hours}`. Si no se envían doctor_ids, selecciona automáticamente los top N doctores elegibles |
| `GET` | `/shifts/{id}/offers/` | Admin | Lista todas las ofertas del turno con nombre del doctor, fecha, sede |
| `POST` | `/shifts/{id}/offers/{offer_id}/cancel` | Admin | Cancela una oferta pendiente |

---

### Admin — Documentos (`/api/v1/admin/documents`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/admin/documents/` | Admin | Lista todos los documentos. Filtrable por `status` (pending/approved/rejected). Paginado con `skip`, `limit` |
| `GET` | `/admin/documents/doctors/{doctor_id}` | Admin | Lista documentos de un doctor específico |
| `POST` | `/admin/documents/{doc_id}/approve` | Admin | Aprueba documento. Registra quién lo aprobó y cuándo |
| `POST` | `/admin/documents/{doc_id}/reject` | Admin | Rechaza documento. Requiere `{rejection_reason}` en el body |

---

### Tipos de Documento (`/api/v1/document-types`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/api/v1/document-types/` | Público | Lista todos los tipos de documento. Cada tipo: `{id, code, name, description, validity_months, is_mandatory}` |

**Tipos pre-cargados:**

| Código | Nombre | Obligatorio | Validez |
|--------|--------|-------------|---------|
| `assicurazione` | Assicurazione Professionale | Sí | 12 meses |
| `laurea` | Laurea in Medicina | Sí | — |
| `abilitazione` | Abilitazione Professionale | Sí | — |
| `iscrizione_ordine` | Iscrizione Ordine dei Medici | Sí | 12 meses |
| `documento_identita` | Documento di Identità | Sí | 120 meses |
| `codice_fiscale` | Codice Fiscale | No | — |
| `cv` | Curriculum Vitae | No | — |
| `attestato_bls` | Attestato BLS-D | No | 24 meses |
| `attestato_acls` | Attestato ACLS | No | 24 meses |

---

### Analytics (`/api/v1/admin/analytics`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/admin/analytics/kpis` | Admin | KPIs globales: `{total_shifts, covered_shifts, coverage_percent, total_offers_sent, acceptance_rate, active_doctors, total_assignments}` |
| `GET` | `/admin/analytics/kpis/by-month?year=` | Admin | KPIs mensuales (12 meses): `[{month, total_shifts, covered_shifts, coverage_percent}]` |
| `GET` | `/admin/analytics/doctor-stats` | Admin | Stats de fiabilidad de doctores: ofertas recibidas/aceptadas/rechazadas/expiradas, tasa de aceptación, tiempo promedio de respuesta, puntaje de fiabilidad |
| `GET` | `/admin/analytics/doctor-stats/{doctor_id}` | Admin | Stats de un doctor específico |
| `POST` | `/admin/analytics/recalculate` | Admin | Recalcula scores de fiabilidad para todos los doctores activos |

---

### Audit Log (`/api/v1/admin/audit-log`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/admin/audit-log/` | Admin | Lista registros de auditoría. Filtrable por `entity_type`, `entity_id`, `action`. Paginado con `skip`, `limit`. Cada registro: `{id, user_id, action, entity_type, entity_id, old_values, new_values, ip_address, created_at}` |

---

### Lookups — Datos de Referencia (`/api/v1/lookups`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/lookups/certification-types` | Público | Lista tipos de certificación: `{id, name, description, validity_months}` |
| `POST` | `/lookups/certification-types` | Público | Crea tipo de certificación |
| `GET` | `/lookups/languages` | Público | Lista idiomas: `{id, code, name}` |
| `POST` | `/lookups/languages` | Público | Crea idioma |
| `GET` | `/lookups/code-levels` | Público | Lista niveles de código (WHITE, GREEN, YELLOW, RED) |
| `POST` | `/lookups/code-levels` | Público | Crea nivel de código |

---

### Disponibilidad (`/api/v1/doctors/{doctor_id}`)

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/doctors/{id}/availability` | Público | Establece disponibilidad: `{date, start_time, end_time, availability_type}` donde type es: `available`, `preferred`, o `reluctant` |
| `POST` | `/doctors/{id}/availability/bulk` | Público | Establece disponibilidad masiva para múltiples fechas |
| `GET` | `/doctors/{id}/availability?start=&end=` | Público | Lista disponibilidad en un rango de fechas |
| `POST` | `/doctors/{id}/unavailability` | Público | Crea indisponibilidad: `{start_date, end_date, reason}` donde reason es: `vacation`, `sick_leave`, `personal`, `training`, `other` |
| `GET` | `/doctors/{id}/unavailability` | Público | Lista indisponibilidades |

---

## Frontend — Páginas y Funcionalidad

El frontend es una SPA (Single Page Application) con hash routing (`#/ruta`).

### Pantalla de Login (`#/login`)

- Formulario de email y password
- Botón para alternar entre Login y Registro
- En modo Registro: pide nombre, apellido, código fiscal, teléfono, email y password
- Al registrarse como médico, se crea automáticamente el perfil Doctor vinculado
- Al hacer login exitoso, guarda el JWT en localStorage y redirige al Dashboard

### Dashboard (`#/`)

**Visible para todos los roles autenticados.**

Muestra 4 KPI cards:
- **Medici Attivi**: cantidad de doctores activos
- **Istituzioni**: cantidad de instituciones
- **Turni del Mese**: turnos del mes actual
- **Turni da Assegnare**: turnos sin cubrir completamente

Debajo: tabla de **Turni da Completare** con turnos en estado open/partially_filled/draft, mostrando sede, fecha, tipo, estado y cantidad de médicos asignados vs requeridos.

### Medici (`#/medici`) — Solo Admin

- Tabla paginada de doctores con búsqueda por nombre/código fiscal
- Al hacer click en un doctor, se expande un panel de detalle mostrando:
  - Información personal (CF, email, teléfono, experiencia, límites de turnos)
  - Certificaciones activas
  - Idiomas y nivel de competencia
  - Preferencias (día/noche/weekend)

### Strutture (`#/strutture`) — Solo Admin

- Lista de instituciones con sus sedes expandibles
- Cada institución muestra: nombre, tipo, ciudad, cantidad de sedes
- Al expandir: detalle de cada sede con:
  - Dirección y ciudad
  - Amenidades: alojamiento, comidas, estacionamiento
  - Requisitos: trabajo autónomo, vehículo de emergencia, experiencia mínima

### Calendario (`#/calendario`) — Solo Admin

- Selector de sede en dropdown agrupado por institución
- Calendario mensual/semanal (FullCalendar) con turnos como eventos
- **Colores por estado**: azul (abierto), amarillo (parcial), verde (completo), gris (borrador), rojo (cancelado), púrpura (en progreso)
- Al hacer click en un turno, se abre un modal con:
  - Información del turno (fecha, horario, pago, prioridad)
  - Asignaciones actuales con botón de desasignar
  - Lista de doctores elegibles ordenados por score con breakdown de puntaje
  - Botón de asignar para cada doctor elegible
- Botones de acceso rápido para crear institución/sede y doctor

### Profilo (`#/profilo`) — Solo Médico

- Avatar con iniciales y barra de completitud del perfil (%)
- Formulario editable con:
  - Nombre, apellido, teléfono
  - Fecha de nacimiento
  - Dirección de residencia, ciudad de domicilio
  - Provincia y número del Ordine dei Medici
  - Distancia máxima, checkboxes: vehículo propio, disponible a trasladarse, disponible para noches
- Botón "Salva Profilo"

### Documenti (`#/documenti`) — Solo Médico

- Lista de documentos propios con estado (badge de color), nombre del archivo, tamaño
- Botón "+ Carica" para subir nuevo documento:
  - Selector de tipo de documento
  - Campos opcionales: fecha emisión, fecha vencimiento
  - Selector de archivo (PDF, JPG, PNG)
- Documentos pendientes pueden eliminarse
- Documentos rechazados muestran el motivo

### Offerte (`#/mie-offerte`) — Solo Médico

- Dos pestañas: **Pendenti** y **Tutte**
- Cada oferta muestra: sede, fecha del turno, estado (badge de color)
- Las ofertas pendientes muestran countdown de expiración
- Botones **Accetta** (verde) y **Rifiuta** (rojo) para ofertas pendientes
- Al aceptar, se crea automáticamente la asignación

### Gestione Documenti (`#/admin/documenti`) — Solo Admin

- Lista de todos los documentos de todos los médicos
- Filtro por estado (todos/pendientes/aprobados/rechazados)
- Cada documento muestra: nombre del doctor, tipo de documento, archivo
- Botones **Approva** y **Rifiuta** para documentos pendientes
- Al rechazar, se abre modal para escribir el motivo

### Analytics (`#/analytics`) — Solo Admin

- 4 KPI cards: Copertura Turni (%), Offerte Inviate, Tasso Accettazione (%), Medici Attivi
- Botón "Ricalcola Reliability" para recalcular scores de fiabilidad
- Tabla mensual con: mes, turnos totales, turnos cubiertos, porcentaje de cobertura

---

## Motor de Eligibilidad

Ejecuta **18 checks** antes de permitir una asignación. Si algún check hard falla, el doctor no es elegible.

### Checks Hard (bloquean asignación)

| # | Check | Descripción |
|---|-------|-------------|
| 1 | Estado activo | El doctor debe estar activo |
| 2 | Disponibilidad | El doctor debe tener disponibilidad declarada para la fecha/hora del turno |
| 3 | Certificaciones obligatorias | Debe tener todas las certificaciones requeridas por el turno |
| 4 | Certificaciones vigentes | Las certificaciones requeridas no pueden estar vencidas a la fecha del turno |
| 5 | Idiomas requeridos | Debe hablar todos los idiomas requeridos por el turno |
| 6 | Distancia | La distancia al sitio no puede exceder el máximo del doctor (salvo willing_to_relocate) |
| 7 | Superposición | No puede tener otro turno que se superponga en horario |
| 8 | Descanso | Debe haber mínimo 11 horas de descanso entre turnos |
| 9 | Días consecutivos | No puede exceder 6 días consecutivos de trabajo |
| 10 | Límite nocturno global | No puede exceder 8 turnos nocturnos por mes |
| 11 | Nivel de código | El nivel de código del doctor debe alcanzar el mínimo del turno |
| 12 | Trabajo independiente | Si el turno requiere trabajo autónomo, el doctor debe poder |
| 13 | Vehículo emergencia | Si el turno requiere vehículo de emergencia, el doctor debe tener |
| 14 | Experiencia | Los años de experiencia deben alcanzar el mínimo del turno |
| 15 | Límite mensual | No puede exceder su límite personal de turnos por mes |
| 16 | Límite nocturno personal | No puede exceder su límite personal de turnos nocturnos |
| 17 | Documentos obligatorios | Debe tener todos los documentos obligatorios aprobados |
| 18 | Documentos vigentes | Los documentos aprobados no pueden estar vencidos a la fecha del turno |

### Checks Soft (advertencias, no bloquean)

- Nivel de idioma inferior al requerido pero idioma presente
- Distancia excedida pero doctor dispuesto a reubicarse

---

## Sistema de Scoring

Los doctores elegibles se puntúan de 0 a 100 en 9 dimensiones:

| Dimensión | Máx. | Criterio |
|-----------|------|----------|
| **Disponibilidad** | 20 | preferred=20, available=12, reluctant=4 |
| **Reliability** | 15 | Basado en historial de ofertas: tasa de aceptación, tiempo de respuesta, cancelaciones |
| **Afinidad con sede** | 15 | Misma sede=15, misma institución=10, tipo preferido=6, sin historial=3 |
| **Preferencia de turno** | 10 | Match con preferencia día/noche/weekend del doctor |
| **Balance de carga** | 10 | Menos turnos asignados en el mes = mayor puntaje |
| **Distancia** | 10 | ≤10km=10, ≤25km=8, ≤50km=5, >50km=2 |
| **Equidad (Fairness)** | 10 | Doctores con menos asignaciones recientes tienen prioridad |
| **Cualificaciones extra** | 5 | Certificaciones, idiomas y experiencia por encima de los requisitos mínimos |
| **Eficiencia de costo** | 5 | Cercanía (menos viaje), vehículo propio, sin necesidad de alojamiento |

---

## Base de Datos

### Tablas principales (24 tablas)

**Usuarios y Médicos:**
- `users` — Identidad de login (email, password_hash, role)
- `doctors` — Perfil profesional del médico (vinculado a user)
- `doctor_certifications` — Certificaciones del médico
- `doctor_languages` — Idiomas del médico
- `doctor_preferences` — Preferencias de turno

**Instituciones:**
- `institutions` — Instituciones sanitarias
- `institution_sites` — Sedes de cada institución
- `institution_requirements` — Requisitos de certificación por institución
- `institution_language_requirements` — Requisitos de idioma por institución

**Turnos:**
- `shifts` — Turnos individuales
- `shift_templates` — Templates para generación masiva
- `shift_requirements` — Requisitos de certificación por turno
- `shift_language_requirements` — Requisitos de idioma por turno

**Asignaciones y Ofertas:**
- `shift_assignments` — Asignaciones de doctor a turno
- `shift_offers` — Ofertas de turno enviadas a doctores
- `notifications` — Notificaciones in-app

**Documentos:**
- `document_types` — Tipos de documento (9 pre-cargados)
- `documents` — Documentos subidos por médicos

**Analytics:**
- `doctor_reliability_stats` — Stats calculados de fiabilidad
- `audit_logs` — Registro de auditoría de acciones

**Lookup:**
- `certification_types` — Tipos de certificación
- `languages` — Idiomas
- `code_levels` — Niveles de código (WHITE, GREEN, YELLOW, RED)

**Disponibilidad:**
- `doctor_availabilities` — Disponibilidad declarada
- `doctor_unavailabilities` — Indisponibilidades (vacaciones, enfermedad, etc.)
