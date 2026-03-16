document.addEventListener('alpine:init', () => {

    Alpine.data('dashboardPage', () => ({
        stats: { doctors: 0, institutions: 0, shiftsThisMonth: 0, unassigned: 0 },
        incompleteShifts: [],
        loading: true,

        async init() {
            await this.loadStats();
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

                // Build a map of site id -> site name
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
                // Sort by date ascending
                incomplete.sort((a, b) => new Date(a.start_datetime) - new Date(b.start_datetime));
                this.incompleteShifts = incomplete;
            } catch (e) {
                console.error('Dashboard load failed:', e);
            }
            this.loading = false;
        },
    }));

});
