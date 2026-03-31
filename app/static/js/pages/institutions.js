document.addEventListener('alpine:init', () => {

    Alpine.data('institutionsPage', () => ({
        institutions: [],
        loading: true,
        expanded: {},
        requirements: {},
        langRequirements: {},
        siteShifts: {},
        loadingDetail: {},

        // Lookup data for modal
        codeLevels: [],
        certTypes: [],
        availableLangs: [],

        // Add structure modal
        structureModalOpen: false,
        structureSaving: false,
        structureError: '',
        newStructure: {
            inst_name: '', tax_code: '',
            inst_address: '', inst_city: '', inst_province: '',
            cooperative_id: '',
            site_name: '', site_type: '', site_address: '', site_city: '', site_province: '',
            min_years_experience: 0,
            min_code_level_id: '',
            lodging_available: false, meal_support: false, parking_available: false,
            requires_independent_work: false, requires_emergency_vehicle: false,
            certReqs: {},
            langReqs: [],
            newLangId: '',
            newLangProficiency: 2,
        },

        // Cooperative state
        cooperatives: [],
        coopModalOpen: false,
        coopSaving: false,
        coopError: '',
        editCoopId: null,
        newCoop: { name: '', partita_iva: '', city: '', province: '', email: '', phone: '' },

        // Template state
        siteTemplates: {},
        addTemplateOpen: false,
        templateSaving: false,
        templateError: '',
        templateSiteId: null,
        newTemplate: { name: '', start_time: '08:00', end_time: '20:00', required_doctors: 1, base_pay: 0, is_night: false, min_code_level_id: '', requires_emergency_vehicle: false },

        // Generate shifts state
        generateStart: {},
        generateEnd: {},
        generatingShifts: {},

        async init() {
            await Promise.all([this.load(), this.loadLookups(), this.loadCooperatives()]);
        },

        async loadLookups() {
            const [cls, cts, ls] = await Promise.all([
                API.get('/lookups/code-levels').catch(() => []),
                API.get('/lookups/certification-types').catch(() => []),
                API.get('/lookups/languages').catch(() => []),
            ]);
            this.codeLevels = cls.sort((a, b) => a.severity_order - b.severity_order);
            this.certTypes = cts;
            this.availableLangs = ls;
        },

        certName(id) {
            const ct = this.certTypes.find(c => c.id === id);
            return ct ? ct.name : 'Cert #' + id;
        },

        langName(id) {
            const l = this.availableLangs.find(l => l.id === id);
            return l ? l.name : 'Lingua #' + id;
        },

        codeLevelName(id) {
            const cl = this.codeLevels.find(c => c.id === id);
            return cl ? cl.code : 'Livello #' + id;
        },

        cefrLabel(level) {
            return ['', 'A1/A2', 'B1', 'B2', 'C1', 'C2'][level] || level;
        },

        async deleteInstitution(instId) {
            if (!confirm('Eliminare questa istituzione e tutte le sue sedi e turni?')) return;
            try {
                await API.del(`/institutions/${instId}`);
                await this.load();
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
        },

        async deleteSite(siteId, instId) {
            if (!confirm('Eliminare questa sede e tutti i suoi turni?')) return;
            try {
                await API.del(`/institutions/sites/${siteId}`);
                await this.load();
                delete this.requirements[instId];
                await this.loadInstitutionDetail(instId);
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
        },

        async load() {
            this.loading = true;
            try {
                const data = await API.get('/institutions/', { skip: 0, limit: 200 });
                this.institutions = data.items;
            } catch (e) {
                console.error('Institutions load failed:', e);
            }
            this.loading = false;
        },

        async toggle(id) {
            this.expanded[id] = !this.expanded[id];
            if (this.expanded[id] && !this.requirements[id]) {
                await this.loadInstitutionDetail(id);
            }
        },

        async loadInstitutionDetail(instId) {
            this.loadingDetail[instId] = true;
            try {
                const [reqs, langReqs] = await Promise.all([
                    API.get(`/institutions/${instId}/requirements`).catch(() => []),
                    API.get(`/institutions/${instId}/language-requirements`).catch(() => []),
                ]);
                this.requirements[instId] = reqs;
                this.langRequirements[instId] = langReqs;

                const inst = this.institutions.find(i => i.id === instId);
                if (inst?.sites) {
                    const now = new Date();
                    const start = now.toISOString().split('T')[0];
                    const endDate = new Date(now);
                    endDate.setDate(endDate.getDate() + 30);
                    const end = endDate.toISOString().split('T')[0];
                    for (const site of inst.sites) {
                        this.siteShifts[site.id] = await API.get(`/shifts/calendar/${site.id}`, { start, end }).catch(() => []);
                    }
                }
            } catch (e) {
                console.error('Detail load failed:', e);
            }
            this.loadingDetail[instId] = false;
        },

        async loadSiteShifts(siteId) {
            const now = new Date();
            const start = now.toISOString().split('T')[0];
            const endDate = new Date(now);
            endDate.setDate(endDate.getDate() + 30);
            const end = endDate.toISOString().split('T')[0];
            this.siteShifts[siteId] = await API.get(`/shifts/calendar/${siteId}`, { start, end }).catch(() => []);
        },

        isExpanded(id) {
            return !!this.expanded[id];
        },

        fmtDate(d) {
            if (!d) return '';
            return new Date(d).toLocaleDateString('it-IT');
        },

        fmtDt(dt) {
            if (!dt) return '';
            return new Date(dt).toLocaleString('it-IT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
        },

        shiftStatusLabel(s) {
            return { draft: 'Bozza', open: 'Aperto', partially_filled: 'Parziale', filled: 'Completo', in_progress: 'In corso', completed: 'Completato', cancelled: 'Annullato', proposing: 'In proposta', uncovered: 'Scoperto' }[s] || s;
        },

        shiftStatusColor(s) {
            return { open: 'badge-blue', partially_filled: 'badge-yellow', filled: 'badge-green', draft: 'badge-gray', cancelled: 'badge-red', in_progress: 'badge-purple', completed: 'badge-teal', proposing: 'badge-blue', uncovered: 'badge-red' }[s] || '';
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
            return labels[type?.toUpperCase()] || type || 'N/D';
        },

        proficiencyLabel(level) {
            return ['', 'A1/A2', 'B1', 'B2', 'C1', 'C2/Madrelingua'][level] || level;
        },

        codeLevelLabel(cl) {
            if (!cl) return '';
            return cl.code;
        },

        async openStructureModal() {
            if (!this.codeLevels.length) await this.loadLookups();
            this.resetStructureForm();
            this.structureModalOpen = true;
        },

        toggleCertReq(ctId, checked) {
            this.newStructure.certReqs[ctId] = {
                selected: checked,
                is_mandatory: this.newStructure.certReqs[ctId]?.is_mandatory ?? true,
            };
        },

        setCertMandatory(ctId, isMandatory) {
            if (this.newStructure.certReqs[ctId]) {
                this.newStructure.certReqs[ctId].is_mandatory = isMandatory;
            }
        },

        addLangReq() {
            const id = parseInt(this.newStructure.newLangId);
            if (!id) return;
            if (this.newStructure.langReqs.find(r => r.language_id === id)) return;
            const lang = this.availableLangs.find(l => l.id === id);
            if (!lang) return;
            this.newStructure.langReqs.push({
                language_id: lang.id,
                language_name: lang.name,
                min_proficiency: this.newStructure.newLangProficiency || 2,
            });
            this.newStructure.newLangId = '';
            this.newStructure.newLangProficiency = 2;
        },

        removeLangReq(idx) {
            this.newStructure.langReqs.splice(idx, 1);
        },

        async submitStructure() {
            this.structureError = '';
            const s = this.newStructure;
            if (!s.inst_name || !s.tax_code || !s.site_name) {
                this.structureError = 'Nome istituzione, codice fiscale e nome sede sono obbligatori.';
                return;
            }
            this.structureSaving = true;
            try {
                const inst = await API.post('/institutions/', {
                    name: s.inst_name,
                    tax_code: s.tax_code,
                    address: s.inst_address || null,
                    city: s.inst_city || null,
                    province: s.inst_province || null,
                    cooperative_id: s.cooperative_id || null,
                });

                await API.post(`/institutions/${inst.id}/sites`, {
                    name: s.site_name,
                    site_type: s.site_type || null,
                    address: s.site_address || null,
                    city: s.site_city || null,
                    province: s.site_province || null,
                    lodging_available: s.lodging_available,
                    meal_support: s.meal_support,
                    parking_available: s.parking_available,
                    requires_independent_work: s.requires_independent_work,
                    requires_emergency_vehicle: s.requires_emergency_vehicle,
                    min_years_experience: s.min_years_experience || 0,
                    min_code_level_id: s.min_code_level_id ? parseInt(s.min_code_level_id) : null,
                });

                // Certification requirements
                for (const [ctId, req] of Object.entries(s.certReqs)) {
                    if (req.selected) {
                        await API.post(`/institutions/${inst.id}/requirements`, {
                            certification_type_id: parseInt(ctId),
                            is_mandatory: req.is_mandatory,
                        }).catch(() => {});
                    }
                }

                // Language requirements
                for (const lr of s.langReqs) {
                    await API.post(`/institutions/${inst.id}/language-requirements`, {
                        language_id: lr.language_id,
                        min_proficiency: lr.min_proficiency,
                    }).catch(() => {});
                }

                this.structureModalOpen = false;
                this.resetStructureForm();
                await this.load();
            } catch (e) {
                this.structureError = 'Errore: ' + e.message;
            }
            this.structureSaving = false;
        },

        resetStructureForm() {
            this.newStructure = {
                inst_name: '', tax_code: '',
                inst_address: '', inst_city: '', inst_province: '',
                cooperative_id: '',
                site_name: '', site_type: '', site_address: '', site_city: '', site_province: '',
                min_years_experience: 0,
                min_code_level_id: '',
                lodging_available: false, meal_support: false, parking_available: false,
                requires_independent_work: false, requires_emergency_vehicle: false,
                certReqs: Object.fromEntries((this.certTypes || []).map(ct => [ct.id, { selected: false, is_mandatory: true }])),
                langReqs: [],
                newLangId: '',
                newLangProficiency: 2,
            };
            this.structureError = '';
        },

        // --- Cooperatives ---

        async loadCooperatives() {
            try {
                this.cooperatives = await API.get('/cooperatives/', { limit: 200 });
            } catch (e) {
                console.error('Cooperatives load failed:', e);
            }
        },

        openCoopModal(coop = null) {
            this.editCoopId = coop ? coop.id : null;
            this.newCoop = coop
                ? { name: coop.name, partita_iva: coop.partita_iva || '', city: coop.city || '', province: coop.province || '', email: coop.email || '', phone: coop.phone || '' }
                : { name: '', partita_iva: '', city: '', province: '', email: '', phone: '' };
            this.coopError = '';
            this.coopModalOpen = true;
        },

        async saveCoop() {
            this.coopError = '';
            if (!this.newCoop.name) { this.coopError = 'Il nome è obbligatorio.'; return; }
            this.coopSaving = true;
            try {
                const payload = {
                    name: this.newCoop.name,
                    partita_iva: this.newCoop.partita_iva || null,
                    city: this.newCoop.city || null,
                    province: this.newCoop.province || null,
                    email: this.newCoop.email || null,
                    phone: this.newCoop.phone || null,
                };
                if (this.editCoopId) {
                    await API.patch(`/cooperatives/${this.editCoopId}`, payload);
                } else {
                    await API.post('/cooperatives/', payload);
                }
                this.coopModalOpen = false;
                await this.loadCooperatives();
                Alpine.store('app').toast('Cooperativa salvata', 'success');
            } catch (e) {
                this.coopError = 'Errore: ' + e.message;
            }
            this.coopSaving = false;
        },

        // --- Templates ---

        async loadTemplates(siteId) {
            try {
                const templates = await API.get(`/shifts/templates/${siteId}`);
                this.siteTemplates = { ...this.siteTemplates, [siteId]: templates };
            } catch (e) {
                console.error('Templates load failed:', e);
            }
        },

        openAddTemplate(siteId) {
            this.templateSiteId = siteId;
            this.newTemplate = { name: '', start_time: '08:00', end_time: '20:00', required_doctors: 1, base_pay: 0, is_night: false, min_code_level_id: '', requires_emergency_vehicle: false };
            this.templateError = '';
            this.addTemplateOpen = true;
        },

        async saveTemplate() {
            this.templateError = '';
            if (!this.newTemplate.name) { this.templateError = 'Il nome è obbligatorio.'; return; }
            this.templateSaving = true;
            try {
                await API.post('/shifts/templates', {
                    site_id: this.templateSiteId,
                    name: this.newTemplate.name,
                    start_time: this.newTemplate.start_time + ':00',
                    end_time: this.newTemplate.end_time + ':00',
                    required_doctors: this.newTemplate.required_doctors || 1,
                    base_pay: this.newTemplate.base_pay || 0,
                    is_night: this.newTemplate.is_night,
                    min_code_level_id: this.newTemplate.min_code_level_id ? parseInt(this.newTemplate.min_code_level_id) : null,
                    requires_emergency_vehicle: this.newTemplate.requires_emergency_vehicle,
                });
                this.addTemplateOpen = false;
                await this.loadTemplates(this.templateSiteId);
                Alpine.store('app').toast('Template salvato', 'success');
            } catch (e) {
                this.templateError = 'Errore: ' + e.message;
            }
            this.templateSaving = false;
        },

        async deleteTemplate(templateId, siteId) {
            if (!confirm('Eliminare questo template?')) return;
            try {
                await API.del(`/shifts/templates/item/${templateId}`);
                await this.loadTemplates(siteId);
                Alpine.store('app').toast('Template eliminato', 'success');
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
        },

        async generateFromTemplates(siteId) {
            const start = this.generateStart[siteId];
            const end = this.generateEnd[siteId];
            if (!start || !end) { Alpine.store('app').toast('Seleziona le date', 'error'); return; }
            const templates = this.siteTemplates[siteId] || [];
            if (!templates.length) return;
            this.generatingShifts = { ...this.generatingShifts, [siteId]: true };
            try {
                const created = await API.post('/shifts/generate', {
                    site_id: siteId,
                    template_ids: templates.map(t => t.id),
                    start_date: start,
                    end_date: end,
                });
                await this.loadSiteShifts(siteId);
                Alpine.store('app').toast(created.length + ' turni generati', 'success');
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
            this.generatingShifts = { ...this.generatingShifts, [siteId]: false };
        },
    }));

});
