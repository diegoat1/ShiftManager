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

        // Add structure modal
        structureModalOpen: false,
        structureSaving: false,
        structureError: '',
        newStructure: {
            inst_name: '', tax_code: '', institution_type: '',
            inst_address: '', inst_city: '', inst_province: '',
            site_name: '', site_address: '', site_city: '', site_province: '',
            lodging_available: false, meal_support: false, parking_available: false,
            requires_independent_work: false, requires_emergency_vehicle: false,
            min_years_experience: 0,
        },

        // Add doctor modal
        doctorModalOpen: false,
        doctorSaving: false,
        doctorError: '',
        newDoctor: {
            fiscal_code: '', first_name: '', last_name: '',
            email: '', phone: '', password: '',
            max_shifts_per_month: 20, max_night_shifts_per_month: null,
            years_experience: 0, max_distance_km: 50,
            can_work_alone: false, can_emergency_vehicle: false,
            willing_to_relocate: false, willing_overnight_stay: false,
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

        async submitStructure() {
            this.structureError = '';
            const s = this.newStructure;
            if (!s.inst_name || !s.tax_code || !s.site_name) {
                this.structureError = 'Nome istituzione, codice fiscale e nome sede sono obbligatori.';
                return;
            }
            this.structureSaving = true;
            try {
                const inst = await API.post('/institutions/', {
                    name: s.inst_name,
                    tax_code: s.tax_code,
                    institution_type: s.institution_type || null,
                    address: s.inst_address || null,
                    city: s.inst_city || null,
                    province: s.inst_province || null,
                });
                await API.post(`/institutions/${inst.id}/sites`, {
                    name: s.site_name,
                    address: s.site_address || null,
                    city: s.site_city || null,
                    province: s.site_province || null,
                    lodging_available: s.lodging_available,
                    meal_support: s.meal_support,
                    parking_available: s.parking_available,
                    requires_independent_work: s.requires_independent_work,
                    requires_emergency_vehicle: s.requires_emergency_vehicle,
                    min_years_experience: s.min_years_experience || 0,
                });
                // Refresh institutions list
                const data = await API.get('/institutions/', { skip: 0, limit: 200 });
                this.institutions = data.items;
                this.structureModalOpen = false;
                this.resetStructureForm();
            } catch (e) {
                this.structureError = 'Errore: ' + e.message;
            }
            this.structureSaving = false;
        },

        resetStructureForm() {
            this.newStructure = {
                inst_name: '', tax_code: '', institution_type: '',
                inst_address: '', inst_city: '', inst_province: '',
                site_name: '', site_address: '', site_city: '', site_province: '',
                lodging_available: false, meal_support: false, parking_available: false,
                requires_independent_work: false, requires_emergency_vehicle: false,
                min_years_experience: 0,
            };
            this.structureError = '';
        },

        async submitDoctor() {
            this.doctorError = '';
            const d = this.newDoctor;
            if (!d.fiscal_code || !d.first_name || !d.last_name || !d.email || !d.password) {
                this.doctorError = 'Codice fiscale, nome, cognome, email e password sono obbligatori.';
                return;
            }
            this.doctorSaving = true;
            try {
                await API.post('/doctors/', {
                    fiscal_code: d.fiscal_code,
                    first_name: d.first_name,
                    last_name: d.last_name,
                    email: d.email,
                    phone: d.phone || null,
                    password: d.password,
                    max_shifts_per_month: d.max_shifts_per_month || 20,
                    max_night_shifts_per_month: d.max_night_shifts_per_month || null,
                    years_experience: d.years_experience || 0,
                    max_distance_km: d.max_distance_km || 50,
                    can_work_alone: d.can_work_alone,
                    can_emergency_vehicle: d.can_emergency_vehicle,
                    willing_to_relocate: d.willing_to_relocate,
                    willing_overnight_stay: d.willing_overnight_stay,
                });
                this.doctorModalOpen = false;
                this.resetDoctorForm();
            } catch (e) {
                this.doctorError = 'Errore: ' + e.message;
            }
            this.doctorSaving = false;
        },

        resetDoctorForm() {
            this.newDoctor = {
                fiscal_code: '', first_name: '', last_name: '',
                email: '', phone: '', password: '',
                max_shifts_per_month: 20, max_night_shifts_per_month: null,
                years_experience: 0, max_distance_km: 50,
                can_work_alone: false, can_emergency_vehicle: false,
                willing_to_relocate: false, willing_overnight_stay: false,
            };
            this.doctorError = '';
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
