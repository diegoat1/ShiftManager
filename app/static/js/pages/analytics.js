function analyticsPage() {
    return {
        kpis: null,
        monthlyKpis: [],
        doctorStats: [],
        loading: true,
        message: '',
        selectedYear: new Date().getFullYear(),

        async init() {
            try {
                const [kpis, monthly, stats] = await Promise.all([
                    API.get('/admin/analytics/kpis'),
                    API.get('/admin/analytics/kpis/by-month', { year: this.selectedYear }),
                    API.get('/admin/analytics/doctor-stats', { limit: 20 }),
                ]);
                this.kpis = kpis;
                this.monthlyKpis = monthly;
                this.doctorStats = stats;
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.loading = false;
            }
        },

        async recalculate() {
            try {
                const result = await API.post('/admin/analytics/recalculate');
                this.message = `Ricalcolati stats per ${result.recalculated} medici`;
                await this.init();
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },
    };
}
