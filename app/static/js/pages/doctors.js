document.addEventListener('alpine:init', () => {

    Alpine.data('doctorsPage', () => ({
        doctors: [],
        total: 0,
        skip: 0,
        limit: 20,
        search: '',
        loading: true,
        selectedDoctor: null,
        detailLoading: false,

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

        get filtered() {
            if (!this.search) return this.doctors;
            const q = this.search.toLowerCase();
            return this.doctors.filter(d =>
                d.first_name.toLowerCase().includes(q) ||
                d.last_name.toLowerCase().includes(q) ||
                d.fiscal_code.toLowerCase().includes(q) ||
                d.email.toLowerCase().includes(q)
            );
        },

        get totalPages() {
            return Math.max(1, Math.ceil(this.total / this.limit));
        },

        get currentPage() {
            return Math.floor(this.skip / this.limit) + 1;
        },

        async init() {
            await this.load();
        },

        async load() {
            this.loading = true;
            try {
                const data = await API.get('/doctors/', {
                    skip: this.skip, limit: this.limit,
                });
                this.doctors = data.items;
                this.total = data.total;
            } catch (e) {
                console.error('Doctors load failed:', e);
            }
            this.loading = false;
        },

        async nextPage() {
            if (this.skip + this.limit < this.total) {
                this.skip += this.limit;
                await this.load();
            }
        },

        async prevPage() {
            if (this.skip > 0) {
                this.skip = Math.max(0, this.skip - this.limit);
                await this.load();
            }
        },

        async selectDoctor(id) {
            this.detailLoading = true;
            try {
                this.selectedDoctor = await API.get(`/doctors/${id}`);
            } catch (e) {
                console.error('Doctor detail failed:', e);
            }
            this.detailLoading = false;
        },

        closeDetail() {
            this.selectedDoctor = null;
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
                await this.load();
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
    }));

});
