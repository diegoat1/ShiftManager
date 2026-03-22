function documentsPage() {
    return {
        documents: [],
        documentTypes: [],
        loading: true,
        uploading: false,
        message: '',
        showUpload: false,
        uploadTypeId: '',
        uploadIssuedAt: '',
        uploadExpiresAt: '',

        async init() {
            try {
                const [docs, types] = await Promise.all([
                    API.get('/me/documents/'),
                    fetch('/api/v1/document-types/', {
                        headers: { 'Authorization': 'Bearer ' + Auth.getToken() }
                    }).then(r => r.json()),
                ]);
                this.documents = docs;
                this.documentTypes = types;
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        async upload(event) {
            const file = event.target.files[0];
            if (!file) return;
            this.uploading = true;
            this.message = '';
            try {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('document_type_id', this.uploadTypeId);
                if (this.uploadIssuedAt) formData.append('issued_at', this.uploadIssuedAt);
                if (this.uploadExpiresAt) formData.append('expires_at', this.uploadExpiresAt);

                await API.uploadFile('/me/documents/', formData);
                this.showUpload = false;
                this.message = 'Documento caricato con successo';
                // Refresh
                this.documents = await API.get('/me/documents/');
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.uploading = false;
            }
        },

        async deleteDoc(id) {
            if (!confirm('Eliminare questo documento?')) return;
            try {
                await API.del('/me/documents/' + id);
                this.documents = this.documents.filter(d => d.id !== id);
                this.message = 'Documento eliminato';
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
