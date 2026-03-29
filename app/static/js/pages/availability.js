function availabilityPage() {
    return {
        loading: true,
        message: '',
        entries: [],
        unavailabilities: [],
        currentMonth: new Date().getMonth(),
        currentYear: new Date().getFullYear(),
        selectedDate: null,
        // Add availability form
        showAddForm: false,
        addDate: '',
        addStartTime: '08:00',
        addEndTime: '20:00',
        addType: 'available',
        savingAvail: false,
        // Add unavailability form
        showUnavForm: false,
        unavStartDate: '',
        unavEndDate: '',
        unavReason: 'vacation',
        savingUnav: false,

        async init() {
            await Promise.all([this.loadMonth(), this.loadUnavailabilities()]);
            this.loading = false;
        },

        async loadMonth() {
            try {
                const y = this.currentYear;
                const m = this.currentMonth;
                const start = this.fmtDate(y, m, 1);
                const lastDay = new Date(y, m + 1, 0).getDate();
                const end = this.fmtDate(y, m, lastDay);
                this.entries = await API.get('/me/availability', { start, end });
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        async loadUnavailabilities() {
            try {
                this.unavailabilities = await API.get('/me/unavailability');
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        // --- Calendar grid ---

        get monthName() {
            return new Date(this.currentYear, this.currentMonth, 1)
                .toLocaleDateString('it-IT', { month: 'long', year: 'numeric' });
        },

        get calendarDays() {
            const y = this.currentYear;
            const m = this.currentMonth;
            const firstDow = (new Date(y, m, 1).getDay() + 6) % 7; // Mon=0
            const daysInMonth = new Date(y, m + 1, 0).getDate();
            const days = [];
            // Padding
            for (let i = 0; i < firstDow; i++) days.push(null);
            // Actual days
            for (let d = 1; d <= daysInMonth; d++) {
                days.push({ day: d, dateStr: this.fmtDate(y, m, d) });
            }
            return days;
        },

        prevMonth() {
            if (this.currentMonth === 0) {
                this.currentMonth = 11;
                this.currentYear--;
            } else {
                this.currentMonth--;
            }
            this.selectedDate = null;
            this.loadMonth();
        },

        nextMonth() {
            if (this.currentMonth === 11) {
                this.currentMonth = 0;
                this.currentYear++;
            } else {
                this.currentMonth++;
            }
            this.selectedDate = null;
            this.loadMonth();
        },

        entriesForDate(dateStr) {
            return this.entries.filter(e => e.date === dateStr);
        },

        dayDotColor(dateStr) {
            const dayEntries = this.entriesForDate(dateStr);
            if (dayEntries.length === 0) return '';
            // Priority: preferred > available > reluctant
            const types = new Set(dayEntries.map(e => e.availability_type));
            if (types.has('preferred')) return 'bg-blue-500';
            if (types.has('available')) return 'bg-green-500';
            if (types.has('reluctant')) return 'bg-amber-500';
            return 'bg-green-500';
        },

        isToday(dateStr) {
            const today = new Date();
            return dateStr === this.fmtDate(today.getFullYear(), today.getMonth(), today.getDate());
        },

        selectDate(dateStr) {
            this.selectedDate = this.selectedDate === dateStr ? null : dateStr;
        },

        // --- Add availability ---

        openAddForDate(dateStr) {
            this.addDate = dateStr;
            this.addStartTime = '08:00';
            this.addEndTime = '20:00';
            this.addType = 'available';
            this.showAddForm = true;
        },

        async addAvailability() {
            if (!this.addDate || !this.addStartTime || !this.addEndTime) return;
            this.savingAvail = true;
            this.message = '';
            try {
                await API.post('/me/availability', {
                    date: this.addDate,
                    start_time: this.addStartTime + ':00',
                    end_time: this.addEndTime + ':00',
                    availability_type: this.addType,
                });
                await this.loadMonth();
                this.showAddForm = false;
                this.message = 'Disponibilita aggiunta';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.savingAvail = false;
            }
        },

        async deleteEntry(id) {
            if (!confirm('Eliminare questa disponibilita?')) return;
            try {
                await API.del('/me/availability/' + id);
                await this.loadMonth();
                this.message = 'Disponibilita eliminata';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        // --- Unavailability ---

        async addUnavailability() {
            if (!this.unavStartDate || !this.unavEndDate) return;
            this.savingUnav = true;
            this.message = '';
            try {
                await API.post('/me/unavailability', {
                    start_date: this.unavStartDate,
                    end_date: this.unavEndDate,
                    reason: this.unavReason,
                });
                await this.loadUnavailabilities();
                this.showUnavForm = false;
                this.unavStartDate = '';
                this.unavEndDate = '';
                this.message = 'Indisponibilita aggiunta';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.savingUnav = false;
            }
        },

        async deleteUnavailability(id) {
            if (!confirm('Eliminare questo periodo?')) return;
            try {
                await API.del('/me/unavailability/' + id);
                await this.loadUnavailabilities();
                this.message = 'Periodo eliminato';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        // --- Labels ---

        typeLabel(type) {
            return { available: 'Disponibile', preferred: 'Preferito', reluctant: 'Riluttante' }[type] || type;
        },

        typeColor(type) {
            return { available: 'badge-green', preferred: 'badge-blue', reluctant: 'badge-yellow' }[type] || '';
        },

        reasonLabel(reason) {
            return { vacation: 'Ferie', sick_leave: 'Malattia', personal: 'Personale', training: 'Formazione', other: 'Altro' }[reason] || reason;
        },

        reasonColor(reason) {
            return { vacation: 'badge-blue', sick_leave: 'badge-red', personal: 'badge-gray', training: 'badge-purple', other: 'badge-gray' }[reason] || '';
        },

        formatTime(t) {
            if (!t) return '';
            return t.substring(0, 5);
        },

        fmtDate(y, m, d) {
            return y + '-' + String(m + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
        },
    };
}
