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
        newShift: {
            date: '', startTime: '08:00', endTime: '20:00',
            required_doctors: 2, base_pay: 0, is_night: false,
            shift_type: '', status: 'open',
        },

        async init() {
            try {
                const data = await API.get('/institutions/', { skip: 0, limit: 200 });
                this.institutions = data.items;
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

        openCreate() {
            if (!this.selectedSite) {
                Alpine.store('app').toast('Seleziona una sede prima di creare un turno', 'error');
                return;
            }
            // Default date to tomorrow
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            this.newShift.date = tomorrow.toISOString().split('T')[0];
            this.createError = '';
            this.createOpen = true;
        },

        async submitCreate() {
            this.createError = '';
            const s = this.newShift;
            if (!s.date || !s.startTime || !s.endTime) {
                this.createError = 'Data, ora inizio e ora fine sono obbligatori.';
                return;
            }
            this.createSaving = true;
            try {
                // Build naive datetime strings (no timezone) to match TIMESTAMP WITHOUT TIME ZONE columns
                let endDate = s.date;
                const [sh, sm] = s.startTime.split(':').map(Number);
                const [eh, em] = s.endTime.split(':').map(Number);
                if (eh * 60 + em <= sh * 60 + sm) {
                    // End crosses midnight — advance date by 1
                    const d = new Date(s.date + 'T00:00:00');
                    d.setDate(d.getDate() + 1);
                    endDate = d.toISOString().split('T')[0];
                }

                const payload = {
                    site_id: this.selectedSite,
                    date: s.date,
                    start_datetime: `${s.date}T${s.startTime}:00`,
                    end_datetime: `${endDate}T${s.endTime}:00`,
                    required_doctors: parseInt(s.required_doctors) || 1,
                    base_pay: parseFloat(s.base_pay) || 0,
                    is_night: s.is_night,
                    shift_type: s.shift_type || null,
                };
                const created = await API.post('/shifts/', payload);
                // If status is 'open', update it (default is 'draft')
                if (s.status === 'open') {
                    await API.patch(`/shifts/${created.id}`, { status: 'open' });
                }
                this.createOpen = false;
                if (this.calendar) this.calendar.refetchEvents();
                Alpine.store('app').toast('Turno creato!', 'success');
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
