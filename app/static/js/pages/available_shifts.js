document.addEventListener('alpine:init', () => {

    Alpine.data('availableShiftsPage', () => ({
        shifts: [],
        loading: true,
        applying: null,

        filterStart: '',
        filterEnd: '',
        filterType: '',
        filterNight: '',

        institutionTypes: [
            { value: 'pronto_soccorso', label: 'Pronto Soccorso' },
            { value: 'punto_primo_intervento', label: 'Punto Primo Intervento' },
            { value: 'guardia_medica', label: 'Guardia Medica' },
            { value: 'emergenza_118', label: 'Emergenza 118' },
            { value: 'casa_di_comunita', label: 'Casa di Comunità' },
            { value: 'rsa', label: 'RSA' },
        ],

        async init() {
            const today = new Date();
            this.filterStart = this.dateToStr(today);
            const end = new Date(today);
            end.setDate(end.getDate() + 30);
            this.filterEnd = this.dateToStr(end);
            await this.load();
        },

        async load() {
            this.loading = true;
            try {
                const params = { start: this.filterStart, end: this.filterEnd };
                if (this.filterType) params.institution_type = this.filterType;
                if (this.filterNight === 'night') params.is_night = true;
                else if (this.filterNight === 'day') params.is_night = false;
                this.shifts = await API.get('/me/available-shifts', params);
            } catch (e) {
                Alpine.store('app').toast('Errore nel caricamento: ' + e.message, 'error');
            }
            this.loading = false;
        },

        async apply(shiftId) {
            this.applying = shiftId;
            try {
                await API.post('/me/candidature', { shift_id: shiftId });
                Alpine.store('app').toast('Candidatura inviata con successo!', 'success');
                await this.load();
            } catch (e) {
                Alpine.store('app').toast(e.message || 'Errore nella candidatura', 'error');
            }
            this.applying = null;
        },

        fmtDate(d) {
            if (!d) return '';
            return new Date(d).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
        },

        fmtTime(d) {
            if (!d) return '';
            return new Date(d).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
        },

        fmtPay(s) {
            const pay = s.base_pay * s.urgent_multiplier;
            return pay > 0 ? '\u20AC' + pay.toFixed(0) : '-';
        },

        scoreColor(score) {
            if (score >= 70) return 'text-green-600';
            if (score >= 40) return 'text-amber-600';
            return 'text-red-500';
        },

        institutionLabel(type) {
            const found = this.institutionTypes.find(t => t.value === type);
            return found ? found.label : (type || '').replace(/_/g, ' ');
        },

        dateToStr(d) {
            return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
        },
    }));

});
