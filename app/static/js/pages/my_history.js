document.addEventListener('alpine:init', () => {

    Alpine.data('myHistoryPage', () => ({
        assignments: [],
        loading: true,
        filterYear: new Date().getFullYear(),
        filterMonth: '',

        async init() {
            await this.load();
        },

        async load() {
            this.loading = true;
            try {
                const params = { statuses: ['confirmed', 'completed'] };
                if (this.filterMonth) {
                    const [y, m] = this.filterMonth.split('-').map(Number);
                    params.start = y + '-' + String(m).padStart(2, '0') + '-01';
                    const lastDay = new Date(y, m, 0).getDate();
                    params.end = y + '-' + String(m).padStart(2, '0') + '-' + lastDay;
                }
                this.assignments = await API.get('/me/assignments', params);
            } catch (e) {
                console.error('History load failed:', e);
            }
            this.loading = false;
        },

        get totalShifts() {
            return this.assignments.length;
        },

        get totalHours() {
            return this.assignments.reduce((sum, a) => sum + (a.duration_hours || 0), 0).toFixed(1);
        },

        get totalPay() {
            return this.assignments.reduce((sum, a) => sum + (a.pay_amount || 0), 0).toFixed(0);
        },

        get completedCount() {
            return this.assignments.filter(a => a.status === 'completed').length;
        },

        get monthOptions() {
            const months = [];
            const now = new Date();
            for (let i = 0; i < 12; i++) {
                const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
                const val = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
                const label = d.toLocaleDateString('it-IT', { month: 'long', year: 'numeric' });
                months.push({ value: val, label: label.charAt(0).toUpperCase() + label.slice(1) });
            }
            return months;
        },

        fmtDate(d) {
            if (!d) return '';
            return new Date(d).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
        },

        fmtTime(d) {
            if (!d) return '';
            return new Date(d).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
        },

        statusLabel(s) {
            return { confirmed: 'Confermato', completed: 'Completato', proposed: 'Proposto' }[s] || s;
        },

        statusColor(s) {
            return { confirmed: 'bg-green-100 text-green-800', completed: 'bg-slate-100 text-slate-600' }[s] || 'bg-slate-100 text-slate-600';
        },
    }));

});
