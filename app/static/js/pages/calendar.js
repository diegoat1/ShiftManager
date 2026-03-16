document.addEventListener('alpine:init', () => {

    const STATUS_COLORS = {
        'FILLED': '#16A34A',
        'PARTIALLY_FILLED': '#EAB308',
        'OPEN': '#2563EB',
        'DRAFT': '#9CA3AF',
        'IN_PROGRESS': '#8B5CF6',
        'COMPLETED': '#059669',
        'CANCELLED': '#DC2626',
    };

    Alpine.data('calendarPage', () => ({
        institutions: [],
        selectedSite: '',
        calendar: null,
        loading: true,

        // Modal
        modalOpen: false,
        modalShift: null,
        modalEligible: [],
        modalAssignments: [],
        modalLoading: false,
        assigning: false,

        async init() {
            try {
                const data = await API.get('/institutions', { skip: 0, limit: 200 });
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
                await API.post('/assignments', {
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
