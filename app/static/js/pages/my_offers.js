function myOffersPage() {
    return {
        offers: [],
        pendingOffers: [],
        loading: true,
        message: '',
        tab: 'pending',

        async init() {
            try {
                const [all, pending] = await Promise.all([
                    API.get('/me/offers/'),
                    API.get('/me/offers/pending'),
                ]);
                this.offers = all;
                this.pendingOffers = pending;
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        async accept(offerId) {
            try {
                await API.post('/me/offers/' + offerId + '/accept');
                this.message = 'Offerta accettata';
                await this.init();
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        async reject(offerId) {
            try {
                await API.post('/me/offers/' + offerId + '/reject', {});
                this.message = 'Offerta rifiutata';
                await this.init();
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        statusLabel(status) {
            const labels = {
                proposed: 'Proposta', viewed: 'Vista', accepted: 'Accettata',
                rejected: 'Rifiutata', expired: 'Scaduta', cancelled: 'Annullata',
            };
            return labels[status] || status;
        },

        statusColor(status) {
            const colors = {
                proposed: 'badge-blue', viewed: 'badge-blue', accepted: 'badge-green',
                rejected: 'badge-red', expired: 'badge-gray', cancelled: 'badge-gray',
            };
            return colors[status] || '';
        },

        timeLeft(expiresAt) {
            if (!expiresAt) return '';
            const diff = new Date(expiresAt) - new Date();
            if (diff <= 0) return 'Scaduta';
            const hours = Math.floor(diff / 3600000);
            const mins = Math.floor((diff % 3600000) / 60000);
            return `${hours}h ${mins}m`;
        },
    };
}
