function qualificationsPage() {
    return {
        loading: true,
        message: '',
        certifications: [],
        languages: [],
        certificationTypes: [],
        availableLanguages: [],
        // Add cert form
        showAddCert: false,
        newCertTypeId: '',
        newCertObtainedDate: '',
        newCertExpiryDate: '',
        savingCert: false,
        // Add language form
        showAddLang: false,
        newLangId: '',
        newLangProficiency: 3,
        savingLang: false,

        async init() {
            try {
                const [certs, langs, certTypes, allLangs] = await Promise.all([
                    API.get('/me/certifications'),
                    API.get('/me/languages'),
                    API.get('/lookups/certification-types'),
                    API.get('/lookups/languages'),
                ]);
                this.certifications = certs;
                this.languages = langs;
                this.certificationTypes = certTypes;
                this.availableLanguages = allLangs;
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.loading = false;
            }
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
                    ? 'Certificazione gia presente'
                    : 'Errore: ' + e.message;
            } finally {
                this.savingCert = false;
            }
        },

        async removeCertification(certTypeId) {
            if (!confirm('Rimuovere questa certificazione?')) return;
            try {
                await API.del('/me/certifications/' + certTypeId);
                this.certifications = await API.get('/me/certifications');
                this.message = 'Certificazione rimossa';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
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
            const exp = new Date(cert.expiry_date);
            const now = new Date();
            return Math.ceil((exp - now) / (1000 * 60 * 60 * 24));
        },

        certStatusLabel(cert) {
            const s = this.certStatus(cert);
            return { active: 'Attiva', expiring: 'In Scadenza', critical: 'Scade Presto', expired: 'Scaduta', inactive: 'Inattiva' }[s] || s;
        },

        certStatusColor(cert) {
            const s = this.certStatus(cert);
            return { active: 'badge-green', expiring: 'badge-yellow', critical: 'badge-red', expired: 'badge-red', inactive: 'badge-gray' }[s] || '';
        },

        get expiringCerts() {
            return this.certifications.filter(c => {
                const s = this.certStatus(c);
                return s === 'expiring' || s === 'critical' || s === 'expired';
            });
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
                    ? 'Lingua gia presente'
                    : 'Errore: ' + e.message;
            } finally {
                this.savingLang = false;
            }
        },

        async removeLanguage(languageId) {
            if (!confirm('Rimuovere questa lingua?')) return;
            try {
                await API.del('/me/languages/' + languageId);
                this.languages = await API.get('/me/languages');
                this.message = 'Lingua rimossa';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        proficiencyLabel(level) {
            return { 1: 'Base', 2: 'Elementare', 3: 'Intermedio', 4: 'Avanzato', 5: 'Madrelingua' }[level] || level;
        },
    };
}
