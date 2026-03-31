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
        availability: [],
        unavailability: [],
        assignments: [],
        documents: [],
        detailTab: 'info',

        // Lookup data
        codeLevels: [],
        certTypes: [],
        availableLangs: [],

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

        // Edit doctor modal
        editModalOpen: false,
        editSaving: false,
        editError: '',
        editDoctor: {},

        // Inline cert management
        addCertOpen: false,
        newCert: { certTypeId: '', obtainedDate: '', expiryDate: '' },
        certSaving: false,

        // Inline lang management
        addLangOpen: false,
        newLang: { langId: '', proficiency: 3 },
        langSaving: false,

        get totalPages() {
            return Math.max(1, Math.ceil(this.total / this.limit));
        },

        get currentPage() {
            return Math.floor(this.skip / this.limit) + 1;
        },

        async init() {
            await Promise.all([this.load(), this.loadLookups()]);
            this.$watch('search', () => {
                clearTimeout(this._searchTimer);
                this._searchTimer = setTimeout(() => {
                    this.skip = 0;
                    this.load();
                }, 400);
            });
        },

        async loadLookups() {
            const [cls, cts, ls] = await Promise.all([
                API.get('/lookups/code-levels').catch(() => []),
                API.get('/lookups/certification-types').catch(() => []),
                API.get('/lookups/languages').catch(() => []),
            ]);
            this.codeLevels = cls.sort((a, b) => a.severity_order - b.severity_order);
            this.certTypes = cts;
            this.availableLangs = ls;
        },

        certTypeName(id) {
            const ct = this.certTypes.find(c => c.id === id);
            return ct ? ct.name : 'Tipo #' + id;
        },

        langName(id) {
            const l = this.availableLangs.find(l => l.id === id);
            return l ? l.name : 'Lingua #' + id;
        },

        get availableCertTypes() {
            if (!this.selectedDoctor) return this.certTypes;
            const held = new Set((this.selectedDoctor.certifications || []).map(c => c.certification_type_id));
            return this.certTypes.filter(ct => !held.has(ct.id));
        },

        get availableLangOptions() {
            if (!this.selectedDoctor) return this.availableLangs;
            const held = new Set((this.selectedDoctor.languages || []).map(l => l.language_id));
            return this.availableLangs.filter(l => !held.has(l.id));
        },

        async load() {
            this.loading = true;
            try {
                const params = { skip: this.skip, limit: this.limit };
                if (this.search) params.search = this.search;
                const data = await API.get('/doctors/', params);
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
            this.detailTab = 'info';
            this.availability = [];
            this.unavailability = [];
            this.assignments = [];
            this.documents = [];
            this.addCertOpen = false;
            this.addLangOpen = false;
            try {
                const now = new Date();
                const start = now.toISOString().split('T')[0];
                const endDate = new Date(now);
                endDate.setDate(endDate.getDate() + 90);
                const end = endDate.toISOString().split('T')[0];

                const [doctor, avail, unavail, assigns, docs] = await Promise.all([
                    API.get(`/doctors/${id}`),
                    API.get(`/doctors/${id}/availability`, { start, end }).catch(() => []),
                    API.get(`/doctors/${id}/unavailability`, { start, end }).catch(() => []),
                    API.get(`/assignments/doctor/${id}`).catch(() => []),
                    API.get(`/admin/documents/doctors/${id}`).catch(() => []),
                ]);
                this.selectedDoctor = doctor;
                this.availability = avail;
                this.unavailability = unavail;
                this.assignments = assigns;
                this.documents = docs;
            } catch (e) {
                console.error('Doctor detail failed:', e);
            }
            this.detailLoading = false;
        },

        async refreshSelectedDoctor() {
            if (!this.selectedDoctor) return;
            try {
                this.selectedDoctor = await API.get(`/doctors/${this.selectedDoctor.id}`);
            } catch (e) {
                console.error('Refresh doctor failed:', e);
            }
        },

        closeDetail() {
            this.selectedDoctor = null;
            this.availability = [];
            this.unavailability = [];
            this.assignments = [];
            this.documents = [];
            this.addCertOpen = false;
            this.addLangOpen = false;
        },

        // --- Edit doctor modal ---

        openEditModal(doctor) {
            this.editDoctor = {
                first_name: doctor.first_name,
                last_name: doctor.last_name,
                email: doctor.email,
                phone: doctor.phone || '',
                years_experience: doctor.years_experience,
                max_shifts_per_month: doctor.max_shifts_per_month,
                max_night_shifts_per_month: doctor.max_night_shifts_per_month ?? '',
                max_distance_km: doctor.max_distance_km,
                max_code_level_id: doctor.max_code_level_id ?? '',
                can_work_alone: doctor.can_work_alone,
                can_emergency_vehicle: doctor.can_emergency_vehicle,
                willing_to_relocate: doctor.willing_to_relocate,
                willing_overnight_stay: doctor.willing_overnight_stay,
                has_own_vehicle: doctor.has_own_vehicle,
                birth_date: doctor.birth_date || '',
                residence_address: doctor.residence_address || '',
                domicile_city: doctor.domicile_city || '',
                ordine_province: doctor.ordine_province || '',
                ordine_number: doctor.ordine_number || '',
                is_active: doctor.is_active,
            };
            this.editError = '';
            this.editModalOpen = true;
        },

        async saveEdit() {
            this.editError = '';
            this.editSaving = true;
            try {
                const d = this.editDoctor;
                const payload = {
                    first_name: d.first_name || null,
                    last_name: d.last_name || null,
                    email: d.email || null,
                    phone: d.phone || null,
                    years_experience: d.years_experience !== '' ? parseInt(d.years_experience) : null,
                    max_shifts_per_month: d.max_shifts_per_month !== '' ? parseInt(d.max_shifts_per_month) : null,
                    max_night_shifts_per_month: d.max_night_shifts_per_month !== '' ? parseInt(d.max_night_shifts_per_month) : null,
                    max_distance_km: d.max_distance_km !== '' ? parseFloat(d.max_distance_km) : null,
                    max_code_level_id: d.max_code_level_id !== '' ? parseInt(d.max_code_level_id) : null,
                    can_work_alone: d.can_work_alone,
                    can_emergency_vehicle: d.can_emergency_vehicle,
                    willing_to_relocate: d.willing_to_relocate,
                    willing_overnight_stay: d.willing_overnight_stay,
                    has_own_vehicle: d.has_own_vehicle,
                    birth_date: d.birth_date || null,
                    residence_address: d.residence_address || null,
                    domicile_city: d.domicile_city || null,
                    ordine_province: d.ordine_province || null,
                    ordine_number: d.ordine_number || null,
                    is_active: d.is_active,
                };
                await API.patch(`/doctors/${this.selectedDoctor.id}`, payload);
                this.editModalOpen = false;
                await this.refreshSelectedDoctor();
                await this.load();
            } catch (e) {
                this.editError = 'Errore: ' + e.message;
            }
            this.editSaving = false;
        },

        // --- Certifications ---

        async saveCert() {
            if (!this.newCert.certTypeId || !this.newCert.obtainedDate) return;
            this.certSaving = true;
            try {
                await API.post(`/doctors/${this.selectedDoctor.id}/certifications`, {
                    certification_type_id: parseInt(this.newCert.certTypeId),
                    obtained_date: this.newCert.obtainedDate,
                    expiry_date: this.newCert.expiryDate || null,
                });
                this.newCert = { certTypeId: '', obtainedDate: '', expiryDate: '' };
                this.addCertOpen = false;
                await this.refreshSelectedDoctor();
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
            this.certSaving = false;
        },

        async removeCert(certTypeId) {
            if (!confirm('Rimuovere questa certificazione?')) return;
            try {
                await API.del(`/doctors/${this.selectedDoctor.id}/certifications/${certTypeId}`);
                await this.refreshSelectedDoctor();
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
        },

        // --- Languages ---

        async saveLang() {
            if (!this.newLang.langId) return;
            this.langSaving = true;
            try {
                await API.post(`/doctors/${this.selectedDoctor.id}/languages`, {
                    language_id: parseInt(this.newLang.langId),
                    proficiency_level: parseInt(this.newLang.proficiency),
                });
                this.newLang = { langId: '', proficiency: 3 };
                this.addLangOpen = false;
                await this.refreshSelectedDoctor();
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
            this.langSaving = false;
        },

        async removeLang(languageId) {
            if (!confirm('Rimuovere questa lingua?')) return;
            try {
                await API.del(`/doctors/${this.selectedDoctor.id}/languages/${languageId}`);
                await this.refreshSelectedDoctor();
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
        },

        // --- Activate / Deactivate ---

        async toggleActive(doctor) {
            const newState = !doctor.is_active;
            const label = newState ? 'attivare' : 'disattivare';
            if (!confirm(`Vuoi ${label} il medico ${doctor.first_name} ${doctor.last_name}?`)) return;
            try {
                await API.patch(`/doctors/${doctor.id}`, { is_active: newState });
                await this.refreshSelectedDoctor();
                await this.load();
                Alpine.store('app').toast(newState ? 'Medico attivato' : 'Medico disattivato', 'success');
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
        },

        // --- Formatters ---

        fmtDate(d) {
            if (!d) return '';
            return new Date(d).toLocaleDateString('it-IT');
        },

        fmtDt(dt) {
            if (!dt) return '';
            return new Date(dt).toLocaleString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        },

        availTypeLabel(type) {
            return { available: 'Disponibile', preferred: 'Preferito', reluctant: 'Riluttante' }[type] || type;
        },

        availTypeColor(type) {
            return { available: 'badge-green', preferred: 'badge-blue', reluctant: 'badge-yellow' }[type] || '';
        },

        unavailReasonLabel(r) {
            return { vacation: 'Ferie', sick_leave: 'Malattia', personal: 'Personale', training: 'Formazione', other: 'Altro' }[r] || r;
        },

        statusLabel(s) {
            return { proposed: 'Proposto', confirmed: 'Confermato', rejected: 'Rifiutato', cancelled: 'Annullato', completed: 'Completato' }[s] || s;
        },

        statusColor(s) {
            return { proposed: 'badge-blue', confirmed: 'badge-green', rejected: 'badge-red', cancelled: 'badge-gray', completed: 'badge-teal' }[s] || '';
        },

        docStatusLabel(s) {
            return { pending: 'In attesa', approved: 'Approvato', rejected: 'Rifiutato', expired: 'Scaduto' }[s] || s;
        },

        docStatusColor(s) {
            return { pending: 'badge-yellow', approved: 'badge-green', rejected: 'badge-red', expired: 'badge-gray' }[s] || '';
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
