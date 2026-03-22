function offersAdminPage() {
    return {
        // This is used within the calendar/shift detail modal
        offers: [],
        loading: false,
        message: '',

        async loadOffers(shiftId) {
            this.loading = true;
            try {
                this.offers = await API.get('/shifts/' + shiftId + '/offers/');
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        async sendOffer(shiftId, doctorId) {
            try {
                await API.post('/shifts/' + shiftId + '/offers/send', {
                    doctor_id: doctorId,
                    expires_in_hours: 12,
                });
                this.message = 'Offerta inviata';
                await this.loadOffers(shiftId);
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        async sendBatch(shiftId, topN = 3) {
            try {
                await API.post('/shifts/' + shiftId + '/offers/send-batch', {
                    top_n: topN,
                    expires_in_hours: 12,
                });
                this.message = `Offerte inviate ai top ${topN} medici`;
                await this.loadOffers(shiftId);
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        async cancelOffer(shiftId, offerId) {
            try {
                await API.post('/shifts/' + shiftId + '/offers/' + offerId + '/cancel');
                this.message = 'Offerta annullata';
                await this.loadOffers(shiftId);
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
    };
}
