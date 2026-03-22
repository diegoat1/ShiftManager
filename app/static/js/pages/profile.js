function profilePage() {
    return {
        profile: null,
        loading: true,
        saving: false,
        message: '',

        async init() {
            try {
                this.profile = await API.get('/me/profile');
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.loading = false;
            }
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
                };
                this.profile = await API.patch('/me/profile', data);
                this.message = 'Profilo aggiornato con successo';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.saving = false;
            }
        },
    };
}
