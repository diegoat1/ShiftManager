function documentazionePage() {
    return {
        loading: true,
        message: '',
        tab: 'certificazioni',

        // Certifications
        certifications: [],
        certificationTypes: [],
        showAddCert: false,
        newCertTypeId: '',
        newCertObtainedDate: '',
        newCertExpiryDate: '',
        savingCert: false,

        // Languages
        languages: [],
        availableLanguages: [],
        showAddLang: false,
        newLangId: '',
        newLangProficiency: 3,
        savingLang: false,

        // Documents
        documents: [],
        documentTypes: [],
        showUpload: false,
        uploadTypeId: '',
        uploadIssuedAt: '',
        uploadExpiresAt: '',
        uploading: false,

        async init() {
            try {
                const [certs, langs, certTypes, allLangs, docs, docTypes] = await Promise.all([
                    API.get('/me/certifications'),
                    API.get('/me/languages'),
                    API.get('/lookups/certification-types'),
                    API.get('/lookups/languages'),
                    API.get('/me/documents/'),
                    fetch('/api/v1/document-types/', {
                        headers: { 'Authorization': 'Bearer ' + Auth.getToken() }
                    }).then(r => r.json()),
                ]);
                this.certifications = certs;
                this.languages = langs;
                this.certificationTypes = certTypes;
                this.availableLanguages = allLangs;
                this.documents = docs;
                this.documentTypes = docTypes;
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        // --- Completeness ---

        get completeness() {
            const mandatoryTypes = this.documentTypes.filter(t => t.is_mandatory);
            const uploadedTypeIds = new Set(this.documents.map(d => d.document_type_id));
            const uploaded = mandatoryTypes.filter(t => uploadedTypeIds.has(t.id)).length;
            const total = mandatoryTypes.length;
            return { uploaded, total, percent: total > 0 ? Math.round((uploaded / total) * 100) : 100 };
        },

        get alertItems() {
            const items = [];
            // Expiring certs
            for (const cert of this.certifications) {
                const days = this.certDaysLeft(cert);
                if (days !== null && days <= 90) {
                    items.push({
                        type: days <= 0 ? 'error' : days <= 30 ? 'critical' : 'warning',
                        text: (cert.certification_type?.name || 'Certificazione') + (days <= 0 ? ' - Scaduta!' : ' - Scade tra ' + days + ' giorni'),
                    });
                }
            }
            // Missing mandatory docs
            const mandatoryTypes = this.documentTypes.filter(t => t.is_mandatory);
            const uploadedTypeIds = new Set(this.documents.map(d => d.document_type_id));
            for (const dt of mandatoryTypes) {
                if (!uploadedTypeIds.has(dt.id)) {
                    items.push({ type: 'error', text: dt.name + ' - Documento obbligatorio mancante' });
                }
            }
            // Expiring docs
            for (const doc of this.documents) {
                if (doc.expires_at) {
                    const days = Math.ceil((new Date(doc.expires_at) - new Date()) / (1000 * 60 * 60 * 24));
                    if (days <= 90) {
                        const typeName = this.documentTypes.find(t => t.id === doc.document_type_id)?.name || doc.original_filename;
                        items.push({
                            type: days <= 0 ? 'error' : days <= 30 ? 'critical' : 'warning',
                            text: typeName + (days <= 0 ? ' - Scaduto!' : ' - Scade tra ' + days + ' giorni'),
                        });
                    }
                }
            }
            return items;
        },

        // --- Certifications ---

        get filteredCertTypes() {
            const held = new Set(this.certifications.map(c => c.certification_type_id));
            return this.certificationTypes.filter(t => !held.has(t.id));
        },

        async addCertification() {
            if (!this.newCertTypeId || !this.newCertObtainedDate) return;
            this.savingCert = true;
            this.message = '';
            try {
                await API.post('/me/certifications', {
                    certification_type_id: parseInt(this.newCertTypeId),
                    obtained_date: this.newCertObtainedDate,
                    expiry_date: this.newCertExpiryDate || null,
                });
                this.certifications = await API.get('/me/certifications');
                this.showAddCert = false;
                this.newCertTypeId = '';
                this.newCertObtainedDate = '';
                this.newCertExpiryDate = '';
                this.message = 'Certificazione aggiunta';
            } catch (e) {
                this.message = e.message.includes('409') || e.message.includes('already')
                    ? 'Certificazione gia presente' : 'Errore: ' + e.message;
            } finally { this.savingCert = false; }
        },

        async removeCertification(certTypeId) {
            if (!confirm('Rimuovere questa certificazione?')) return;
            try {
                await API.del('/me/certifications/' + certTypeId);
                this.certifications = await API.get('/me/certifications');
                this.message = 'Certificazione rimossa';
            } catch (e) { this.message = 'Errore: ' + e.message; }
        },

        certStatus(cert) {
            if (!cert.expiry_date) return cert.is_active ? 'active' : 'inactive';
            const exp = new Date(cert.expiry_date);
            const now = new Date();
            if (exp < now) return 'expired';
            const diff = (exp - now) / (1000 * 60 * 60 * 24);
            if (diff <= 30) return 'critical';
            if (diff <= 90) return 'expiring';
            return 'active';
        },

        certDaysLeft(cert) {
            if (!cert.expiry_date) return null;
            return Math.ceil((new Date(cert.expiry_date) - new Date()) / (1000 * 60 * 60 * 24));
        },

        certStatusLabel(cert) {
            const s = this.certStatus(cert);
            return { active: 'Attiva', expiring: 'In Scadenza', critical: 'Scade Presto', expired: 'Scaduta', inactive: 'Inattiva' }[s] || s;
        },

        certStatusColor(cert) {
            const s = this.certStatus(cert);
            return { active: 'badge-green', expiring: 'badge-yellow', critical: 'badge-red', expired: 'badge-red', inactive: 'badge-gray' }[s] || '';
        },

        // --- Languages ---

        get filteredLangs() {
            const held = new Set(this.languages.map(l => l.language_id));
            return this.availableLanguages.filter(l => !held.has(l.id));
        },

        async addLanguage() {
            if (!this.newLangId) return;
            this.savingLang = true;
            this.message = '';
            try {
                await API.post('/me/languages', {
                    language_id: parseInt(this.newLangId),
                    proficiency_level: parseInt(this.newLangProficiency),
                });
                this.languages = await API.get('/me/languages');
                this.showAddLang = false;
                this.newLangId = '';
                this.newLangProficiency = 3;
                this.message = 'Lingua aggiunta';
            } catch (e) {
                this.message = e.message.includes('409') || e.message.includes('already')
                    ? 'Lingua gia presente' : 'Errore: ' + e.message;
            } finally { this.savingLang = false; }
        },

        async removeLanguage(languageId) {
            if (!confirm('Rimuovere questa lingua?')) return;
            try {
                await API.del('/me/languages/' + languageId);
                this.languages = await API.get('/me/languages');
                this.message = 'Lingua rimossa';
            } catch (e) { this.message = 'Errore: ' + e.message; }
        },

        proficiencyLabel(level) {
            return { 1: 'Base', 2: 'Elementare', 3: 'Intermedio', 4: 'Avanzato', 5: 'Madrelingua' }[level] || level;
        },

        // --- Documents ---

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
                this.documents = await API.get('/me/documents/');
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally { this.uploading = false; }
        },

        async deleteDoc(id) {
            if (!confirm('Eliminare questo documento?')) return;
            try {
                await API.del('/me/documents/' + id);
                this.documents = this.documents.filter(d => d.id !== id);
                this.message = 'Documento eliminato';
            } catch (e) { this.message = 'Errore: ' + e.message; }
        },

        docStatusLabel(status) {
            return { pending: 'In attesa', approved: 'Approvato', rejected: 'Rifiutato', expired: 'Scaduto' }[status] || status;
        },

        docStatusColor(status) {
            return { pending: 'badge-yellow', approved: 'badge-green', rejected: 'badge-red', expired: 'badge-gray' }[status] || '';
        },

        docTypeName(typeId) {
            const dt = this.documentTypes.find(t => t.id === typeId);
            return dt ? dt.name : 'Documento';
        },

        formatFileSize(bytes) {
            if (!bytes) return '';
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / 1048576).toFixed(1) + ' MB';
        },
    };
}
