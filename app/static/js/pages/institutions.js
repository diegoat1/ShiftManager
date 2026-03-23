document.addEventListener('alpine:init', () => {

    Alpine.data('institutionsPage', () => ({
        institutions: [],
        loading: true,
        expanded: {},

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

        async init() {
            await this.load();
        },

        async load() {
            this.loading = true;
            try {
                const data = await API.get('/institutions/', {
                    skip: 0, limit: 200,
                });
                this.institutions = data.items;
            } catch (e) {
                console.error('Institutions load failed:', e);
            }
            this.loading = false;
        },

        toggle(id) {
            this.expanded[id] = !this.expanded[id];
        },

        isExpanded(id) {
            return !!this.expanded[id];
        },

        typeLabel(type) {
            const labels = {
                'PRONTO_SOCCORSO': 'Pronto Soccorso',
                'PUNTO_PRIMO_INTERVENTO': 'Punto Primo Intervento',
                'GUARDIA_MEDICA': 'Guardia Medica',
                'EMERGENZA_118': 'Emergenza 118',
                'CASA_DI_COMUNITA': 'Casa di Comunita',
                'RSA': 'RSA',
            };
            return labels[type] || type || 'N/D';
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
                this.structureModalOpen = false;
                this.resetStructureForm();
                await this.load();
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
    }));

});
