document.addEventListener('alpine:init', () => {

    const ASSIGNMENT_COLORS = {
        'confirmed': '#16A34A',
        'proposed': '#EAB308',
        'completed': '#9CA3AF',
        'cancelled': '#EF4444',
        'rejected': '#F97316',
    };

    Alpine.data('myCalendarPage', () => ({
        calendar: null,
        selectedAssignment: null,
        modalOpen: false,

        init() {
            this.$nextTick(() => {
                const el = document.getElementById('my-fullcalendar');
                if (!el || typeof FullCalendar === 'undefined') return;

                if (this.calendar) {
                    this.calendar.destroy();
                    this.calendar = null;
                }

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
                    eventClick: (info) => {
                        this.selectedAssignment = info.event.extendedProps.assignment;
                        this.modalOpen = true;
                    },
                    eventDisplay: 'block',
                });
                this.calendar.render();
            });
        },

        destroy() {
            if (this.calendar) {
                this.calendar.destroy();
                this.calendar = null;
            }
        },

        async fetchEvents(info, success, failure) {
            try {
                const start = info.startStr.split('T')[0];
                const end = info.endStr.split('T')[0];
                const assignments = await API.get('/me/assignments', { start, end });
                const events = (assignments || []).map(a => ({
                    id: a.id,
                    title: (a.site_name || 'Turno') + (a.is_night ? ' (notte)' : ''),
                    start: a.start_datetime,
                    end: a.end_datetime,
                    backgroundColor: ASSIGNMENT_COLORS[a.status] || '#6B7280',
                    borderColor: ASSIGNMENT_COLORS[a.status] || '#6B7280',
                    extendedProps: { assignment: a },
                }));
                success(events);
            } catch (e) {
                console.error('Failed to fetch my assignments:', e);
                failure(e);
            }
        },

        closeDetail() {
            this.modalOpen = false;
            this.selectedAssignment = null;
        },

        fmtDt(dt) {
            if (!dt) return '';
            const d = new Date(dt);
            return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })
                + ' ' + d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
        },

        fmtPay(n) {
            if (n == null) return '-';
            return '€' + Number(n).toFixed(0);
        },

        statusLabel(s) {
            const labels = { proposed: 'Proposto', confirmed: 'Confermato', completed: 'Completato', rejected: 'Rifiutato', cancelled: 'Annullato' };
            return labels[s] || s;
        },

        statusColor(s) {
            const colors = { proposed: 'bg-yellow-100 text-yellow-800', confirmed: 'bg-green-100 text-green-800', completed: 'bg-slate-100 text-slate-600' };
            return colors[s] || 'bg-slate-100 text-slate-600';
        },
    }));

});
