document.addEventListener('alpine:init', () => {

    const STATUS_COLORS = {
        'filled': '#16A34A',
        'partially_filled': '#EAB308',
        'open': '#2563EB',
        'draft': '#9CA3AF',
        'in_progress': '#8B5CF6',
        'completed': '#059669',
        'cancelled': '#DC2626',
    };

    Alpine.data('calendarPage', () => ({
        institutions: [],
        codeLevels: [],
        selectedSite: '',
        calendar: null,
        loading: true,

        // Shift detail modal
        modalOpen: false,
        modalShift: null,
        modalEligible: [],
        modalAssignments: [],
        modalLoading: false,
        assigning: false,

        // Create shift modal
        createOpen: false,
        createSaving: false,
        createError: '',
        siteTemplates: [],
        newShift: {
            date: '', endDate: '', rangeMode: false,
            startTime: '08:00', endTime: '20:00',
            required_doctors: 2, base_pay: 0, is_night: false,
            shift_type: '', status: 'open',
            min_code_level_id: null, requires_emergency_vehicle: false,
        },

        async init() {
            try {
                const [data, cls] = await Promise.all([
                    API.get('/institutions/', { skip: 0, limit: 200 }),
                    API.get('/lookups/code-levels').catch(() => []),
                ]);
                this.institutions = data.items;
                this.codeLevels = cls.sort((a, b) => a.severity_order - b.severity_order);
            } catch (e) {
                console.error('Calendar init failed:', e);
            }
            this.loading = false;

            this.$nextTick(() => {
                const el = document.getElementById('fullcalendar');
                if (!el || typeof FullCalendar === 'undefined') return;
                this.calendar = new FullCalendar.Calendar(el, {
                    initialView: 'dayGridMonth',
                    locale: 'it',
                    headerToolbar: {
                        left: 'prev,next today',
                        center: 'title',
                        right: 'dayGridMonth,timeGridWeek',
                    },
                    height: 'auto',
                    nextDayThreshold: '09:00:00',
                    events: (info, ok, fail) => this.fetchEvents(info, ok, fail),
                    eventClick: (info) => this.openModal(info.event.extendedProps.shiftId),
                    eventDisplay: 'block',
                });
                this.calendar.render();
            });
        },

        onSiteChange() {
            if (this.calendar) this.calendar.refetchEvents();
        },

        async fetchEvents(info, success, failure) {
            if (!this.selectedSite) { success([]); return; }
            try {
                const start = info.startStr.split('T')[0];
                const end = info.endStr.split('T')[0];
                const shifts = await API.get(
                    `/shifts/calendar/${this.selectedSite}`, { start, end }
                );
                success(shifts.map(s => ({
                    id: s.id,
                    title: `${s.shift_type || 'Turno'} (${s.required_doctors})`,
                    start: s.start_datetime,
                    end: s.end_datetime,
                    backgroundColor: STATUS_COLORS[s.status] || '#6B7280',
                    borderColor: STATUS_COLORS[s.status] || '#6B7280',
                    extendedProps: { shiftId: s.id },
                })));
            } catch (e) {
                failure(e);
            }
        },

        async openModal(shiftId) {
            this.modalOpen = true;
            this.modalLoading = true;
            this.modalShift = null;
            this.modalEligible = [];
            this.modalAssignments = [];
            try {
                const [shift, eligible, assignments] = await Promise.all([
                    API.get(`/shifts/${shiftId}`),
                    API.get(`/assignments/eligible/${shiftId}`),
                    API.get(`/assignments/shift/${shiftId}`),
                ]);
                this.modalShift = shift;
                this.modalEligible = eligible;
                this.modalAssignments = assignments;
            } catch (e) {
                console.error('Shift modal failed:', e);
            }
            this.modalLoading = false;
        },

        closeModal() {
            this.modalOpen = false;
            this.modalShift = null;
        },

        async assignDoctor(doctorId) {
            if (!this.modalShift || this.assigning) return;
            this.assigning = true;
            try {
                await API.post('/assignments/', {
                    shift_id: this.modalShift.id,
                    doctor_id: doctorId,
                    pay_amount: this.modalShift.base_pay * this.modalShift.urgent_multiplier,
                });
                await this.openModal(this.modalShift.id);
                if (this.calendar) this.calendar.refetchEvents();
            } catch (e) {
                alert('Errore: ' + e.message);
            }
            this.assigning = false;
        },

        async removeAssignment(id) {
            if (!confirm('Rimuovere questa assegnazione?')) return;
            try {
                await API.del(`/assignments/${id}`);
                await this.openModal(this.modalShift.id);
                if (this.calendar) this.calendar.refetchEvents();
            } catch (e) {
                alert('Errore: ' + e.message);
            }
        },

        _updateIsNight() {
            const [sh] = this.newShift.startTime.split(':').map(Number);
            const [eh] = this.newShift.endTime.split(':').map(Number);
            this.newShift.is_night = sh >= 20 || (eh <= 8 && eh < sh);
        },

        openCreate() {
            if (!this.selectedSite) {
                Alpine.store('app').toast('Seleziona una sede prima di creare un turno', 'error');
                return;
            }
            // Default date to tomorrow
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            const dateStr = tomorrow.toISOString().split('T')[0];
            this.newShift.date = dateStr;
            this.newShift.endDate = dateStr;
            this.newShift.rangeMode = false;
            this.createError = '';
            this._updateIsNight();
            // Load templates for the selected site
            this.siteTemplates = [];
            API.get(`/shifts/templates/${this.selectedSite}`).then(t => { this.siteTemplates = t; }).catch(() => {});
            this.createOpen = true;
        },

        applyTemplate(t) {
            const pad = n => String(n).padStart(2, '0');
            this.newShift.startTime = pad(t.start_time.substring(0, 2)) + ':' + pad(t.start_time.substring(3, 5));
            this.newShift.endTime = pad(t.end_time.substring(0, 2)) + ':' + pad(t.end_time.substring(3, 5));
            this.newShift.required_doctors = t.required_doctors;
            this.newShift.base_pay = t.base_pay;
            this.newShift.is_night = t.is_night;
            this.newShift.min_code_level_id = t.min_code_level_id || null;
            this.newShift.requires_emergency_vehicle = t.requires_emergency_vehicle;
            this.newShift.shift_type = t.name;
        },

        get createRangeDays() {
            const s = this.newShift;
            if (!s.rangeMode || !s.date || !s.endDate) return 1;
            const start = new Date(s.date + 'T00:00:00');
            const end = new Date(s.endDate + 'T00:00:00');
            if (end < start) return 0;
            return Math.round((end - start) / 86400000) + 1;
        },

        _buildShiftPayload(dateStr) {
            const s = this.newShift;
            const [sh, sm] = s.startTime.split(':').map(Number);
            const [eh, em] = s.endTime.split(':').map(Number);
            let endDateStr = dateStr;
            if (eh * 60 + em <= sh * 60 + sm) {
                // End crosses midnight — advance end date by 1
                const d = new Date(dateStr + 'T00:00:00');
                d.setDate(d.getDate() + 1);
                endDateStr = d.toISOString().split('T')[0];
            }
            return {
                site_id: this.selectedSite,
                date: dateStr,
                start_datetime: `${dateStr}T${s.startTime}:00`,
                end_datetime: `${endDateStr}T${s.endTime}:00`,
                required_doctors: parseInt(s.required_doctors) || 1,
                base_pay: parseFloat(s.base_pay) || 0,
                is_night: s.is_night,
                shift_type: s.shift_type || null,
                min_code_level_id: s.min_code_level_id ? parseInt(s.min_code_level_id) : null,
                requires_emergency_vehicle: s.requires_emergency_vehicle,
            };
        },

        _datesBetween(startStr, endStr) {
            const dates = [];
            const current = new Date(startStr + 'T00:00:00');
            const end = new Date(endStr + 'T00:00:00');
            while (current <= end) {
                dates.push(current.toISOString().split('T')[0]);
                current.setDate(current.getDate() + 1);
            }
            return dates;
        },

        async submitCreate() {
            this.createError = '';
            const s = this.newShift;
            if (!s.date || !s.startTime || !s.endTime) {
                this.createError = 'Data, ora inizio e ora fine sono obbligatori.';
                return;
            }
            if (s.rangeMode && (!s.endDate || s.endDate < s.date)) {
                this.createError = 'La data di fine deve essere uguale o successiva alla data di inizio.';
                return;
            }
            this.createSaving = true;
            try {
                const dates = s.rangeMode ? this._datesBetween(s.date, s.endDate) : [s.date];
                let created = 0;
                for (const dateStr of dates) {
                    const payload = this._buildShiftPayload(dateStr);
                    const result = await API.post('/shifts/', payload);
                    if (s.status === 'open') {
                        await API.patch(`/shifts/${result.id}`, { status: 'open' });
                    }
                    created++;
                }
                this.createOpen = false;
                if (this.calendar) this.calendar.refetchEvents();
                Alpine.store('app').toast(
                    created === 1 ? 'Turno creato!' : `${created} turni creati!`,
                    'success'
                );
            } catch (e) {
                this.createError = 'Errore: ' + e.message;
            }
            this.createSaving = false;
        },

        fmtDt(dt) {
            if (!dt) return '';
            return new Date(dt).toLocaleString('it-IT', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit',
            });
        },

        fmtPay(n) {
            return new Intl.NumberFormat('it-IT', {
                style: 'currency', currency: 'EUR',
            }).format(n || 0);
        },
    }));

});
