document.addEventListener('alpine:init', () => {

    Alpine.data('dashboardPage', () => ({
        stats: { doctors: 0, institutions: 0, shiftsThisMonth: 0, unassigned: 0 },
        incompleteShifts: [],
        loading: true,

        // Doctor dashboard
        isDoctorView: false,
        doctorDashboard: null,
        doctorDashboardError: null,

        async init() {
            if (Alpine.store('app').isMedico()) {
                this.isDoctorView = true;
                await this.loadDoctorDashboard();
            } else {
                await this.loadStats();
            }
        },

        async loadDoctorDashboard() {
            this.loading = true;
            this.doctorDashboardError = null;
            try {
                this.doctorDashboard = await API.get('/me/dashboard');
                Alpine.store('app').setDoctorBadgeCounts(this.doctorDashboard);
            } catch (e) {
                this.doctorDashboardError = 'Errore nel caricamento della dashboard';
                console.error('Doctor dashboard load failed:', e);
            }
            this.loading = false;
        },

        fmtDate(d) {
            if (!d) return '';
            return new Date(d).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
        },

        fmtTime(d) {
            if (!d) return '';
            return new Date(d).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
        },

        fmtDt(d) {
            if (!d) return '';
            return this.fmtDate(d) + ' ' + this.fmtTime(d);
        },

        timeLeft(expiresAt) {
            if (!expiresAt) return '';
            const diff = new Date(expiresAt) - new Date();
            if (diff <= 0) return 'Scaduta';
            const hours = Math.floor(diff / 3600000);
            const mins = Math.floor((diff % 3600000) / 60000);
            return hours + 'h ' + mins + 'm';
        },

        statusLabel(s) {
            const labels = { proposed: 'Proposto', confirmed: 'Confermato', completed: 'Completato', rejected: 'Rifiutato', cancelled: 'Annullato' };
            return labels[s] || s;
        },

        statusColor(s) {
            const colors = { proposed: 'bg-yellow-100 text-yellow-800', confirmed: 'bg-green-100 text-green-800', completed: 'bg-slate-100 text-slate-600' };
            return colors[s] || 'bg-slate-100 text-slate-600';
        },

        async acceptOffer(offerId) {
            try {
                await API.post(`/me/offers/${offerId}/accept`);
                await this.loadDoctorDashboard();
            } catch (e) {
                console.error('Accept failed:', e);
            }
        },

        async rejectOffer(offerId) {
            try {
                await API.post(`/me/offers/${offerId}/reject`);
                await this.loadDoctorDashboard();
            } catch (e) {
                console.error('Reject failed:', e);
            }
        },

        async loadStats() {
            this.loading = true;
            try {
                const [doctors, instData] = await Promise.all([
                    API.get('/doctors/', { skip: 0, limit: 1 }),
                    API.get('/institutions/', { skip: 0, limit: 200 }),
                ]);
                this.stats.doctors = doctors.total;
                this.stats.institutions = instData.total;

                const now = new Date();
                const start = new Date(now.getFullYear(), now.getMonth(), 1)
                    .toISOString().split('T')[0];
                const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
                    .toISOString().split('T')[0];

                const siteNames = {};
                const siteRequests = [];
                for (const inst of instData.items) {
                    for (const site of (inst.sites || [])) {
                        siteNames[site.id] = site.name + (site.city ? ' - ' + site.city : '');
                        siteRequests.push(
                            API.get(`/shifts/calendar/${site.id}`, { start, end })
                                .then(shifts => shifts.map(s => ({ ...s, site_id: site.id })))
                                .catch(() => [])
                        );
                    }
                }
                const results = await Promise.all(siteRequests);
                let total = 0, open = 0;
                const incomplete = [];
                for (const shifts of results) {
                    total += shifts.length;
                    for (const s of shifts) {
                        if (s.status === 'open' || s.status === 'partially_filled' || s.status === 'draft') {
                            open++;
                            incomplete.push({
                                id: s.id,
                                site_name: siteNames[s.site_id] || 'N/D',
                                start_datetime: s.start_datetime,
                                shift_type: s.shift_type,
                                status: s.status,
                                required_doctors: s.required_doctors,
                                assigned: s.assigned_doctors || 0,
                            });
                        }
                    }
                }
                this.stats.shiftsThisMonth = total;
                this.stats.unassigned = open;
                incomplete.sort((a, b) => new Date(a.start_datetime) - new Date(b.start_datetime));
                this.incompleteShifts = incomplete;
            } catch (e) {
                console.error('Dashboard load failed:', e);
            }
            this.loading = false;
        },
    }));

});
