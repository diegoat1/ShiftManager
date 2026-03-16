document.addEventListener('alpine:init', () => {

    Alpine.data('dashboardPage', () => ({
        stats: { doctors: 0, institutions: 0, shiftsThisMonth: 0, unassigned: 0 },
        loading: true,

        async init() {
            await this.loadStats();
        },

        async loadStats() {
            this.loading = true;
            try {
                const [doctors, instData] = await Promise.all([
                    API.get('/doctors', { skip: 0, limit: 1 }),
                    API.get('/institutions', { skip: 0, limit: 200 }),
                ]);
                this.stats.doctors = doctors.total;
                this.stats.institutions = instData.total;

                const now = new Date();
                const start = new Date(now.getFullYear(), now.getMonth(), 1)
                    .toISOString().split('T')[0];
                const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
                    .toISOString().split('T')[0];

                const siteRequests = [];
                for (const inst of instData.items) {
                    for (const site of (inst.sites || [])) {
                        siteRequests.push(
                            API.get(`/shifts/calendar/${site.id}`, { start, end })
                                .catch(() => [])
                        );
                    }
                }
                const results = await Promise.all(siteRequests);
                let total = 0, open = 0;
                for (const shifts of results) {
                    total += shifts.length;
                    open += shifts.filter(s =>
                        s.status === 'open' || s.status === 'draft'
                    ).length;
                }
                this.stats.shiftsThisMonth = total;
                this.stats.unassigned = open;
            } catch (e) {
                console.error('Dashboard load failed:', e);
            }
            this.loading = false;
        },
    }));

});
