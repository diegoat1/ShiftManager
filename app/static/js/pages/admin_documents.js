function adminDocumentsPage() {
    return {
        documents: [],
        loading: true,
        message: '',
        filterStatus: '',
        rejectReason: '',
        rejectDocId: null,
        showRejectModal: false,

        async init() {
            await this.loadDocuments();
        },

        async loadDocuments() {
            this.loading = true;
            try {
                const params = {};
                if (this.filterStatus) params.status = this.filterStatus;
                this.documents = await API.get('/admin/documents/', params);
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        async approve(docId) {
            try {
                await API.post('/admin/documents/' + docId + '/approve');
                this.message = 'Documento approvato';
                await this.loadDocuments();
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        openReject(docId) {
            this.rejectDocId = docId;
            this.rejectReason = '';
            this.showRejectModal = true;
        },

        async confirmReject() {
            if (!this.rejectReason.trim()) return;
            try {
                await API.post('/admin/documents/' + this.rejectDocId + '/reject', {
                    status: 'rejected',
                    rejection_reason: this.rejectReason,
                });
                this.showRejectModal = false;
                this.message = 'Documento rifiutato';
                await this.loadDocuments();
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        statusLabel(status) {
            const labels = { pending: 'In attesa', approved: 'Approvato', rejected: 'Rifiutato', expired: 'Scaduto' };
            return labels[status] || status;
        },

        statusColor(status) {
            const colors = { pending: 'badge-yellow', approved: 'badge-green', rejected: 'badge-red', expired: 'badge-gray' };
            return colors[status] || '';
        },
    };
}
