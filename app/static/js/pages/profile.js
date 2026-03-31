function parseCsv(value) {
    if (!value) return [];
    return [...new Set(value.split(',').map(v => v.trim()).filter(Boolean))];
}

function toCsv(values) {
    return [...new Set(values)].join(',');
}

function profilePage() {
    return {
        profile: null,
        preferences: null,
        loading: true,
        saving: false,
        savingPrefs: false,
        message: '',
        tab: 'dati',

        // P5: normalized preference options
        institutionTypeOptions: [
            { value: 'pronto_soccorso', label: 'Pronto Soccorso' },
            { value: 'punto_primo_intervento', label: 'Punto Primo Intervento' },
            { value: 'guardia_medica', label: 'Guardia Medica' },
            { value: 'emergenza_118', label: 'Emergenza 118' },
            { value: 'casa_di_comunita', label: 'Casa di Comunità' },
            { value: 'rsa', label: 'RSA' },
        ],
        codeLevelOptions: [],
        selectedInstitutionTypes: [],
        selectedCodeLevels: [],

        async init() {
            try {
                const [profile, prefs] = await Promise.all([
                    API.get('/me/profile'),
                    API.get('/me/preferences'),
                ]);
                this.profile = profile;
                this.preferences = prefs || {
                    prefers_day: true,
                    prefers_night: false,
                    prefers_weekends: false,
                    avoids_weekends: false,
                    preferred_institution_types: '',
                    preferred_code_levels: '',
                    min_pay_per_shift: null,
                    max_preferred_distance_km: null,
                };

                // Parse comma-separated strings to arrays
                this.selectedInstitutionTypes = parseCsv(this.preferences.preferred_institution_types);
                this.selectedCodeLevels = parseCsv(this.preferences.preferred_code_levels);

                // Load code levels from API
                try {
                    this.codeLevelOptions = await API.get('/lookups/code-levels');
                } catch {
                    this.codeLevelOptions = [];
                }
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        toggleInstitutionType(value) {
            const idx = this.selectedInstitutionTypes.indexOf(value);
            if (idx >= 0) this.selectedInstitutionTypes.splice(idx, 1);
            else this.selectedInstitutionTypes.push(value);
        },

        toggleCodeLevel(code) {
            const idx = this.selectedCodeLevels.indexOf(code);
            if (idx >= 0) this.selectedCodeLevels.splice(idx, 1);
            else this.selectedCodeLevels.push(code);
        },

        async save() {
            this.saving = true;
            this.message = '';
            try {
                const data = {
                    first_name: this.profile.first_name,
                    last_name: this.profile.last_name,
                    phone: this.profile.phone,
                    birth_date: this.profile.birth_date,
                    residence_address: this.profile.residence_address,
                    domicile_city: this.profile.domicile_city,
                    ordine_province: this.profile.ordine_province,
                    ordine_number: this.profile.ordine_number,
                    has_own_vehicle: this.profile.has_own_vehicle,
                    max_distance_km: this.profile.max_distance_km,
                    willing_to_relocate: this.profile.willing_to_relocate,
                    willing_overnight_stay: this.profile.willing_overnight_stay,
                    max_shifts_per_month: this.profile.max_shifts_per_month,
                    years_experience: this.profile.years_experience,
                };
                this.profile = await API.patch('/me/profile', data);
                this.message = 'Profilo aggiornato con successo';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.saving = false;
            }
        },

        async savePreferences() {
            this.savingPrefs = true;
            this.message = '';
            try {
                // Sync arrays to comma-separated strings before saving
                this.preferences.preferred_institution_types = toCsv(this.selectedInstitutionTypes);
                this.preferences.preferred_code_levels = toCsv(this.selectedCodeLevels);

                this.preferences = await API.put('/me/preferences', {
                    prefers_day: !!this.preferences.prefers_day,
                    prefers_night: !!this.preferences.prefers_night,
                    prefers_weekends: !!this.preferences.prefers_weekends,
                    avoids_weekends: !!this.preferences.avoids_weekends,
                    preferred_institution_types: this.preferences.preferred_institution_types || null,
                    preferred_code_levels: this.preferences.preferred_code_levels || null,
                    min_pay_per_shift: this.preferences.min_pay_per_shift || null,
                    max_preferred_distance_km: this.preferences.max_preferred_distance_km || null,
                });

                // Re-parse from saved response
                this.selectedInstitutionTypes = parseCsv(this.preferences.preferred_institution_types);
                this.selectedCodeLevels = parseCsv(this.preferences.preferred_code_levels);

                this.message = 'Preferenze aggiornate con successo';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.savingPrefs = false;
            }
        },
    };
}
