document.addEventListener('alpine:init', () => {

    Alpine.data('institutionsPage', () => ({
        institutions: [],
        loading: true,
        expanded: {},

        async init() {
            await this.load();
        },

        async load() {
            this.loading = true;
            try {
                const data = await API.get('/institutions', {
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
    }));

});
