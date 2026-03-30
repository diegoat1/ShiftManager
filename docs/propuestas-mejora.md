# Propuestas de Mejora - ShiftManager

> Documento generado a partir de una revisión funcional completa de la aplicación desplegada en Railway (v0.2.0), navegando tanto el portal admin como el portal del médico.

---

## Contexto

ShiftManager es una plataforma de gestión de turnos médicos para el sistema sanitario italiano (guardia médica, pronto soccorso, 118, RSA, casa di comunità, PPI). El sistema tiene dos roles principales:

- **Admin**: Crea turnos, gestiona instituciones/sedes, evalúa elegibilidad de médicos mediante un motor de scoring (100 pts, 25+ checks), envía ofertas y asigna turnos.
- **Médico**: Declara disponibilidad, gestiona su perfil/qualifiche/documentos, recibe y responde ofertas de turno.

### Estado actual del portal del médico

| Sección | Estado | Observación |
|---------|--------|-------------|
| Dashboard | Funcional pero inadecuado | Muestra datos del admin (Medici Attivi, Istituzioni) en vez de datos relevantes para el médico |
| Profilo | Completo | Datos personales + preferenze turno editables, barra de completitud (85%) |
| Disponibilità | Funcional | Calendario mensual con selección de día y formulario para agregar slots (hora inicio/fin, tipo) |
| Qualifiche | Completo | Certificaciones con fechas + lingue con nivel de proficiencia |
| Documenti | Funcional | Upload de documentos, vacío en demo |
| Offerte | Funcional | Tabs Pendenti/Tutte, sin ofertas en demo |

---

## Problemas Detectados

### 1. Dashboard del médico reutiliza el dashboard admin

**Problema**: El dashboard muestra "Medici Attivi: 0", "Istituzioni: 0", "Turni del Mese: 0", "Turni da Assegnare: 0" y botones "Vai a Medici" / "Vai al Calendario". Estos datos no tienen sentido para un médico.

**Impacto**: El médico no obtiene información útil al entrar a la app. No sabe si tiene ofertas pendientes, cuándo es su próximo turno, ni si tiene documentos por vencer.

### 2. Sin visibilidad de turnos disponibles

**Problema**: El médico no tiene forma de ver qué turnos existen en el sistema. Solo puede declarar disponibilidad y esperar pasivamente a recibir ofertas.

**Impacto**: Modelo puramente push (admin propone) sin componente pull (médico se postula). Esto ralentiza la cobertura de turnos y reduce la autonomía del médico.

### 3. Disponibilidad sin feedback visual en calendario

**Problema**: Al declarar disponibilidad, el calendario no refleja visualmente los días/horarios cargados. Existe una leyenda (Disponibile verde, Preferito azul, Riluttante naranja) pero los días no se colorean.

**Impacto**: El médico no puede ver de un vistazo su disponibilidad declarada. Tiene que clickear día por día para verificar.

### 4. Sección Offerte sin contexto

**Problema**: "Le Mie Offerte" muestra tabs Pendenti (0) / Tutte (0) pero no hay explicación de qué son las ofertas, cómo llegan, ni qué hacer cuando aparezcan.

**Impacto**: Un médico nuevo no entiende el flujo. Falta onboarding o al menos un estado vacío informativo.

### 5. Sin calendario personal de turnos asignados

**Problema**: No existe una vista donde el médico pueda ver sus turnos confirmados/asignados en formato calendario.

**Impacto**: El médico no tiene forma visual de ver su agenda de trabajo.

### 6. Preferencias de turno con texto libre en vez de valores normalizados

**Problema**: En la sección "Preferenze Turno" del perfil, los campos "Tipi struttura preferiti" y "Livelli codice preferiti" son inputs de texto libre donde el médico escribe manualmente (ej: "pronto_soccorso, guardia_medica" o "WHITE, GREEN"). Esto es propenso a errores de tipeo, inconsistencias, y hace que el backend no pueda matchear las preferencias contra los turnos de forma confiable.

**Dato técnico**: Ya existen tanto el enum `InstitutionType` (6 valores: pronto_soccorso, punto_primo_intervento, guardia_medica, emergenza_118, casa_di_comunita, rsa) como la tabla `code_levels` en la base de datos. El modelo `DoctorPreference` guarda estos valores como `String(500)` y `String(200)` comma-separated, y el scoring engine los parsea con `.split(",")`. Es un diseño frágil.

**Impacto**: Si el médico escribe "pronto soccorso" (con espacio) en vez de "pronto_soccorso" (con guión bajo), el scoring engine no lo matchea y el médico pierde puntos de afinidad injustamente.

### 7. Disponibilidad tediosa de cargar día por día

**Problema**: Para declarar disponibilidad el médico debe seleccionar un día, completar horario y tipo, guardar, y repetir para cada día. Para un mes con 20 días laborables, son 20 operaciones manuales. No hay forma de repetir la disponibilidad del mes anterior ni de declarar patrones recurrentes.

**Impacto**: Fricción alta que desincentiva al médico a mantener su disponibilidad actualizada, lo cual degrada la calidad del motor de elegibilidad.

### 8. Qualifiche y Documenti como secciones separadas

**Problema**: Qualifiche (certificaciones + lingue) y Documenti son dos secciones distintas en el sidebar, pero conceptualmente son parte del mismo dominio: la documentación profesional del médico. Un médico espera ver todo junto: sus certificaciones, los PDFs que las respaldan, y sus idiomas.

**Impacto**: Navegación fragmentada. El médico tiene que ir a dos lugares distintos para gestionar su documentación profesional.

---

## Propuestas de Mejora

### Prioridad Alta

#### P1. Dashboard personalizado para el médico

**Descripción**: Reemplazar el dashboard genérico con uno específico para el rol médico.

**Contenido propuesto**:
- **Próximos turnos** (lista de los próximos 5 turnos asignados/confirmados con fecha, sede, horario)
- **Ofertas pendientes** (contador + lista con countdown de expiración)
- **Certificaciones por vencer** (alerta si alguna vence en los próximos 90 días)
- **Documentos faltantes** (lista de documentos obligatorios no cargados)
- **Resumen del mes** (turnos completados, horas trabajadas, ingresos estimados)
- **Barra de completitud del perfil** (reutilizar la que ya existe en Profilo)

**Archivos a modificar**:
- `app/static/js/app.js` - Lógica de renderizado del dashboard según rol
- `app/api/doctors.py` - Endpoint para stats personales del médico
- `app/services/doctor_service.py` - Lógica de agregación

**Esfuerzo estimado**: Medio

---

#### P2. Calendario personal de turnos ("I Miei Turni")

**Descripción**: Agregar una sección con calendario (FullCalendar, ya integrado) que muestre los turnos asignados/confirmados del médico logueado.

**Funcionalidades**:
- Vista mensual y semanal
- Colores por estado (confirmado=verde, propuesto=amarillo, completado=gris)
- Click en turno para ver detalle (sede, horario, pago, requisitos)
- Exportar a iCal/Google Calendar

**Archivos a modificar**:
- `app/static/js/app.js` - Nueva vista `#/miei-turni`
- `app/api/assignments.py` - Endpoint filtrado por médico actual
- Sidebar del médico - Agregar link "I Miei Turni"

**Esfuerzo estimado**: Medio

---

#### P3. Notificaciones y badges

**Descripción**: Indicadores visuales cuando hay ofertas nuevas, turnos próximos, o documentos por vencer.

**Funcionalidades**:
- Badge numérico en "Offerte" del sidebar cuando hay ofertas pendientes
- Badge en "Documenti" si hay documentos obligatorios faltantes
- Badge en "Qualifiche" si hay certificaciones por vencer
- Notificación al entrar si hay ofertas que expiran pronto (< 24h)

**Archivos a modificar**:
- `app/static/js/app.js` - Renderizado de badges en sidebar
- `app/api/notifications.py` - Ya existe, conectar al frontend del médico

**Esfuerzo estimado**: Bajo-Medio

---

#### P4. Flujo de auto-candidatura a turnos

**Descripción**: Permitir que el médico vea turnos abiertos compatibles con su perfil (elegibles según el motor de reglas) y se postule directamente.

**Funcionalidades**:
- Nueva sección "Turni Disponibili" con lista/calendario de turnos abiertos
- Filtros por fecha, sede, tipo de estructura, turno diurno/nocturno
- Indicador de compatibilidad (score) para cada turno
- Botón "Candidati" que envía la postulación al admin
- El admin recibe la candidatura y puede confirmar/rechazar

**Archivos a crear/modificar**:
- `app/static/js/app.js` - Nueva vista `#/turni-disponibili`
- `app/api/shifts.py` - Endpoint de turnos abiertos filtrados por elegibilidad del médico
- `app/models/shift_application.py` - Nuevo modelo para candidaturas
- `app/services/shift_service.py` - Lógica de candidatura

**Esfuerzo estimado**: Alto

**Nota**: Esta funcionalidad cambia el modelo de negocio de push-only a push+pull, lo cual puede acelerar significativamente la cobertura de turnos.

---

### Prioridad Media

#### P5. Normalización de preferencias de turno (checkboxes en vez de texto libre)

**Descripción**: Reemplazar los campos de texto libre "Tipi struttura preferiti" y "Livelli codice preferiti" con controles normalizados que usen los valores que ya existen en el sistema.

**Problema actual**: El médico escribe manualmente (ej: "pronto_soccorso, guardia_medica"). Si escribe "pronto soccorso" (con espacio) o "PS" o cualquier variante, el scoring engine no lo matchea porque hace `.split(",")` y compara strings exactos.

**Solución**:
- **Tipi struttura**: Grupo de checkboxes con los 6 valores del enum `InstitutionType`:
  - [ ] Pronto Soccorso
  - [ ] Punto Primo Intervento
  - [ ] Guardia Medica
  - [ ] Emergenza 118
  - [ ] Casa di Comunità
  - [ ] RSA
- **Livelli codice**: Grupo de checkboxes con los valores de la tabla `code_levels` (cargados dinámicamente via API `/api/v1/lookups/code-levels`):
  - [ ] WHITE
  - [ ] GREEN
  - [ ] YELLOW
  - [ ] RED
- El frontend serializa los valores seleccionados como comma-separated al guardar (compatible con el formato actual del backend)
- El frontend al cargar parsea el string comma-separated y pre-selecciona los checkboxes correspondientes

**Archivos a modificar**:
- `app/static/index.html` o `app/static/js/pages/profile.js` - Reemplazar `<input>` con checkboxes dinámicos
- `app/api/lookups.py` - Verificar que los endpoints de lookups devuelvan los datos necesarios
- (Opcional, futuro) `app/models/doctor.py` - Migrar de `String(500)` a tabla relacional many-to-many para mayor robustez

**Esfuerzo estimado**: Bajo

**Nota**: Esta es la solución más simple y retrocompatible. El backend no necesita cambios porque sigue recibiendo/devolviendo strings comma-separated. La mejora es 100% frontend.

---

#### P6. Disponibilidad recurrente y repetir mes anterior

**Descripción**: Reducir la fricción de declarar disponibilidad con dos mecanismos complementarios: patrones recurrentes y copia del mes anterior.

**Problema actual**: Cargar disponibilidad día por día es tedioso (20+ operaciones para un mes). Esto desincentiva al médico a mantenerla actualizada.

**Funcionalidades**:

**Opción A - Disponibilidad recurrente**:
- Formulario "Disponibilità Ricorrente" con:
  - Días de la semana (checkboxes: Lun, Mar, Mer, Gio, Ven, Sab, Dom)
  - Horario (inicio/fin)
  - Tipo (Disponibile, Preferito, Riluttante)
  - Rango de fechas (dal/al)
- Preview de los días que se generarían antes de confirmar
- Botón "Genera" que crea todos los slots individuales
- Posibilidad de eliminar excepciones individuales después

**Opción B - Repetir mes anterior**:
- Botón "Ripeti mese precedente" visible cuando el mes actual/próximo está vacío
- Copia todos los slots de disponibilidad del mes anterior al mes seleccionado, ajustando las fechas (ej: "lunes 3 marzo 08-20" se copia como "lunes 6 abril 08-20", matcheando día de la semana)
- Preview antes de confirmar con opción de deseleccionar días específicos
- Si el mes anterior también está vacío, el botón se deshabilita con tooltip explicativo

**Opción C - Plantillas de disponibilidad** (más avanzado):
- El médico guarda un patrón como plantilla con nombre (ej: "Settimana tipo", "Solo mattine")
- Botón "Applica plantilla" para aplicar sobre un rango de fechas
- Útil para médicos con horarios estables

**Recomendación**: Implementar Opción B primero (menor esfuerzo, mayor impacto inmediato), luego Opción A.

**Archivos a modificar**:
- `app/static/js/pages/availability.js` - Botón y lógica de copia/recurrencia
- `app/api/availability.py` - Endpoint batch para crear múltiples slots y endpoint para leer slots de un mes
- `app/services/availability_service.py` - Lógica de generación recurrente y copia

**Esfuerzo estimado**: Medio

---

#### P7. Vista semanal interactiva para disponibilidad

**Descripción**: Agregar vista semanal tipo Google Calendar donde el médico puede hacer drag para declarar bloques de disponibilidad.

**Funcionalidades**:
- Grilla horaria (6:00 - 24:00) x 7 días
- Drag & drop para crear bloques
- Colores por tipo de disponibilidad
- Click en bloque existente para editar/eliminar
- Toggle entre vista mensual (actual) y semanal (nueva)

**Archivos a modificar**:
- `app/static/js/app.js` - Integración con FullCalendar en modo timeGridWeek
- CSS para estilos de bloques de disponibilidad

**Esfuerzo estimado**: Medio

---

#### P8. Historial de turnos trabajados

**Descripción**: Sección con el historial completo de turnos completados por el médico.

**Funcionalidades**:
- Tabla con: fecha, sede, horario, duración, pago, estado
- Filtros por mes/año y por institución
- Resumen: total horas, total turnos, ingreso acumulado
- Exportar a CSV/PDF

**Archivos a modificar**:
- `app/static/js/app.js` - Nueva vista `#/storico-turni`
- `app/api/assignments.py` - Endpoint de historial con filtros y agregación
- Sidebar del médico - Agregar link "Storico"

**Esfuerzo estimado**: Medio

---

#### P9. Alertas de vencimiento de certificaciones y documentos

**Descripción**: Sistema de alertas proactivas cuando certificaciones o documentos están próximos a vencer.

**Funcionalidades**:
- Alerta en dashboard a 90, 60, 30 días de vencimiento
- Indicador visual en Qualifiche (icono amarillo/rojo según urgencia)
- Banner en la parte superior de la app para alertas críticas (< 30 días)
- Marcar certificación como "en renovación" para que el admin sepa
- (Futuro) Email automático de recordatorio

**Archivos a modificar**:
- `app/static/js/app.js` - Componente de alertas
- `app/api/doctors.py` - Endpoint de alertas de vencimiento
- `app/services/doctor_service.py` - Lógica de cálculo de vencimientos

**Esfuerzo estimado**: Bajo-Medio

---

#### P10. Unificar Qualifiche y Documenti en una sola sección

**Descripción**: Fusionar las secciones "Le Mie Qualifiche" y "I Miei Documenti" en una única sección "Documentazione" o "I Miei Documenti e Qualifiche" que agrupe todo lo que es documentación profesional del médico.

**Problema actual**: El médico tiene que navegar a dos secciones distintas (Qualifiche y Documenti) para gestionar su documentación profesional. Las certificaciones están en Qualifiche pero los PDFs que las respaldan están en Documenti. No hay conexión visual entre una certificación y su documento asociado.

**Estructura propuesta de la nueva sección "Documentazione"**:

```
Documentazione
├── Certificazioni (tab o accordion)
│   ├── BLSD - Ottenuta: 2025-02-16 - Scade: 2027-02-06 [Attiva]
│   │   └── 📎 certificato_blsd.pdf [Caricato] [Approvato]
│   ├── ACLS - Ottenuta: 2025-05-27 - Scade: 2027-05-17 [Attiva]
│   │   └── 📎 Nessun documento allegato [+ Carica]
│   └── [+ Aggiungi Certificazione]
│
├── Lingue (tab o accordion)
│   ├── Italiano ●●●●● Madrelingua
│   ├── English ●●●○○ Intermedio
│   └── [+ Aggiungi Lingua]
│
├── Documenti Obbligatori (tab o accordion)
│   ├── ✅ Documento d'identità - Scade: 2028-01-15
│   ├── ❌ Polizza assicurativa - Non caricato
│   ├── ❌ Iscrizione Ordine - Non caricato
│   └── [+ Carica Documento]
│
└── Altri Documenti (tab o accordion)
    └── [+ Carica Documento]
```

**Funcionalidades**:
- Vista unificada con tabs o accordion sections
- Vincular certificaciones con sus documenti di supporto
- Indicatore di completezza (ej: "3/5 documenti obbligatori caricati")
- Alerta inline per documenti/certificazioni in scadenza
- Drag & drop per upload rapido di documenti
- Preview inline di PDF senza dover scaricare

**Cambios en el sidebar del médico**:
- Eliminar "Qualifiche" y "Documenti" como items separados
- Agregar "Documentazione" como item único
- Badge con contatore de documenti mancanti/in scadenza

**Archivos a modificar**:
- `app/static/js/pages/` - Crear `documentation.js` unificando lógica de qualifiche + documenti
- `app/static/index.html` - Nueva vista `#/documentazione`
- `app/static/js/app.js` - Actualizar sidebar y routing
- `app/api/doctors.py` - Endpoint que devuelva certificaciones + documentos juntos con estado de completitud
- (Opcional) `app/models/document.py` - Agregar FK opcional a `doctor_certifications` para vincular documento con certificación

**Esfuerzo estimado**: Medio

---

### Prioridad Baja

#### P11. Mejoras de UI/UX

**Descripción**: Pulir la interfaz para una experiencia más profesional.

**Funcionalidades**:
- Estado vacío informativo (empty states con iconos y texto explicativo en cada sección)
- Onboarding wizard para médicos nuevos (completar perfil paso a paso)
- Confirmaciones visuales al guardar (toast notifications)
- Animaciones de transición entre vistas
- Responsive design mejorado para tablets

**Esfuerzo estimado**: Medio

---

#### P12. Progressive Web App (PWA)

**Descripción**: Convertir la app en PWA para uso desde el celular sin instalar nada.

**Funcionalidades**:
- Service Worker para cache offline
- Manifest.json para "Add to Home Screen"
- Push notifications nativas para ofertas nuevas
- Modo offline para consultar turnos y disponibilidad

**Archivos a crear**:
- `app/static/manifest.json`
- `app/static/sw.js`
- Iconos en múltiples resoluciones

**Esfuerzo estimado**: Medio

---

#### P13. Integración con calendario externo

**Descripción**: Sincronizar turnos asignados con el calendario personal del médico.

**Funcionalidades**:
- Endpoint que genera feed iCal (.ics) con turnos del médico
- URL suscribible desde Google Calendar / Apple Calendar / Outlook
- Actualización automática cuando cambian los turnos
- Incluir detalles en el evento: sede, dirección, contacto, requisitos

**Archivos a crear/modificar**:
- `app/api/calendar_feed.py` - Endpoint iCal
- Dependencia: `icalendar` (Python)

**Esfuerzo estimado**: Bajo

---

#### P14. Sistema de mensajes internos

**Descripción**: Chat o mensajería interna entre admin y médicos.

**Funcionalidades**:
- Mensajes asociados a un turno o generales
- Notificación de mensaje nuevo
- Historial de conversación
- (Futuro) Chat en tiempo real con WebSocket

**Archivos a crear**:
- `app/models/message.py`
- `app/api/messages.py`
- `app/services/message_service.py`
- Vista frontend `#/messaggi`

**Esfuerzo estimado**: Alto

---

## Roadmap sugerido

### Fase 1 - Portal médico funcional (2-3 semanas)
- [ ] P1 - Dashboard personalizado para el médico
- [ ] P2 - Calendario personal de turnos
- [ ] P3 - Notificaciones y badges
- [ ] P5 - Normalización de preferencias (checkboxes)

### Fase 2 - Productividad del médico (2-3 semanas)
- [ ] P6 - Disponibilidad recurrente + repetir mes anterior
- [ ] P7 - Vista semanal disponibilidad
- [ ] P8 - Historial de turnos
- [ ] P9 - Alertas de vencimiento
- [ ] P10 - Unificar Qualifiche + Documenti

### Fase 3 - Modelo bidireccional (3-4 semanas)
- [ ] P4 - Auto-candidatura a turnos
- [ ] P11 - Mejoras UI/UX (empty states, toasts, onboarding)
- [ ] P13 - Integración calendario externo

### Fase 4 - Plataforma completa (3-4 semanas)
- [ ] P12 - PWA
- [ ] P14 - Mensajes internos

---

## Notas técnicas

- El frontend es vanilla JS + Alpine.js, lo cual simplifica agregar nuevas vistas sin build steps.
- FullCalendar ya está integrado, se puede reutilizar para P2 y P7.
- El motor de elegibilidad y scoring ya está completo en el backend, P4 lo aprovecharía directamente.
- La API de notificaciones ya existe (`app/api/notifications.py`), solo falta conectarla al frontend del médico.
- Todos los endpoints del médico ya usan autenticación JWT y filtran por `current_user`.
- Para P5 (preferencias normalizadas): el enum `InstitutionType` ya tiene los 6 tipos y el endpoint `/api/v1/lookups/code-levels` ya devuelve los niveles. El cambio es 100% frontend, sin tocar backend ni DB.
- Para P6 (repetir mes anterior): el endpoint `GET /api/v1/availability?doctor_id=X&month=Y` ya devuelve los slots de un mes, solo falta un endpoint batch POST para crear múltiples slots de una vez.
- Para P10 (unificar secciones): las certificaciones y documentos ya comparten el concepto de "vencimiento" (`expires_at`). Agregar un FK opcional en `documents` hacia `doctor_certifications` permitiría vincularlos sin romper nada existente.
