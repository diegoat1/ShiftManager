function availabilityPage() {
    return {
        loading: true,
        message: '',
        entries: [],
        unavailabilities: [],
        currentMonth: new Date().getMonth(),
        currentYear: new Date().getFullYear(),
        selectedDate: null,
        // View mode: 'month' or 'week'
        viewMode: 'month',
        weekStart: null, // Date object for Monday of current week
        // Add availability form
        showAddForm: false,
        addDate: '',
        addStartTime: '08:00',
        addEndTime: '20:00',
        addType: 'available',
        savingAvail: false,
        // Recurring availability
        showRecurringForm: false,
        recurDays: [false, false, false, false, false, false, false], // Mon-Sun
        recurStartTime: '08:00',
        recurEndTime: '20:00',
        recurType: 'available',
        recurStartDate: '',
        recurEndDate: '',
        savingRecur: false,
        recurPreview: [],
        recurBothShifts: false, // create day+night entries per selected day
        // Repeat month
        repeatingMonth: false,
        // Add unavailability form
        showUnavForm: false,
        unavStartDate: '',
        unavEndDate: '',
        unavReason: 'vacation',
        savingUnav: false,

        async init() {
            // Default week start to current Monday
            const today = new Date();
            const dayOfWeek = (today.getDay() + 6) % 7;
            this.weekStart = new Date(today);
            this.weekStart.setDate(today.getDate() - dayOfWeek);

            // Default recurring range to current month
            const y = this.currentYear, m = this.currentMonth;
            this.recurStartDate = this.fmtDate(y, m, 1);
            const lastDay = new Date(y, m + 1, 0).getDate();
            this.recurEndDate = this.fmtDate(y, m, lastDay);

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

        async loadWeek() {
            try {
                const start = this.dateToStr(this.weekStart);
                const endDate = new Date(this.weekStart);
                endDate.setDate(endDate.getDate() + 6);
                const end = this.dateToStr(endDate);
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

        async reloadEntries() {
            if (this.viewMode === 'week') await this.loadWeek();
            else await this.loadMonth();
        },

        // --- View mode toggle ---

        setView(mode) {
            this.viewMode = mode;
            if (mode === 'week') {
                // Set week to contain first day of current displayed month
                const d = new Date(this.currentYear, this.currentMonth, 1);
                const dow = (d.getDay() + 6) % 7;
                this.weekStart = new Date(d);
                this.weekStart.setDate(d.getDate() - dow);
                this.loadWeek();
            } else {
                this.loadMonth();
            }
        },

        // --- Weekly view ---

        get weekDays() {
            const days = [];
            for (let i = 0; i < 7; i++) {
                const d = new Date(this.weekStart);
                d.setDate(d.getDate() + i);
                days.push({
                    date: new Date(d),
                    dateStr: this.dateToStr(d),
                    label: d.toLocaleDateString('it-IT', { weekday: 'short' }),
                    dayNum: d.getDate(),
                    monthLabel: d.toLocaleDateString('it-IT', { month: 'short' }),
                    isToday: this.dateToStr(d) === this.dateToStr(new Date()),
                });
            }
            return days;
        },

        get weekHours() {
            const hours = [];
            for (let h = 6; h <= 23; h++) hours.push(h);
            return hours;
        },

        weekEntriesForDay(dateStr) {
            return this.entries.filter(e => e.date === dateStr);
        },

        entryTop(entry) {
            const h = parseInt(entry.start_time.substring(0, 2));
            const m = parseInt(entry.start_time.substring(3, 5));
            return ((h - 6) * 48 + m * 0.8) + 'px';
        },

        entryHeight(entry) {
            const sh = parseInt(entry.start_time.substring(0, 2));
            const sm = parseInt(entry.start_time.substring(3, 5));
            const eh = parseInt(entry.end_time.substring(0, 2));
            const em = parseInt(entry.end_time.substring(3, 5));
            const mins = (eh * 60 + em) - (sh * 60 + sm);
            return Math.max(mins * 0.8, 16) + 'px';
        },

        entryBgColor(type) {
            return { available: 'bg-green-200 border-green-400', preferred: 'bg-blue-200 border-blue-400', reluctant: 'bg-amber-200 border-amber-400' }[type] || 'bg-slate-200 border-slate-400';
        },

        prevWeek() {
            this.weekStart = new Date(this.weekStart);
            this.weekStart.setDate(this.weekStart.getDate() - 7);
            this.loadWeek();
        },

        nextWeek() {
            this.weekStart = new Date(this.weekStart);
            this.weekStart.setDate(this.weekStart.getDate() + 7);
            this.loadWeek();
        },

        get weekTitle() {
            const end = new Date(this.weekStart);
            end.setDate(end.getDate() + 6);
            return this.weekStart.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
                + ' - ' + end.toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });
        },

        weekDayClick(dateStr, hour) {
            this.addDate = dateStr;
            this.addStartTime = String(hour).padStart(2, '0') + ':00';
            this.addEndTime = String(Math.min(hour + 12, 23)).padStart(2, '0') + ':00';
            this.addType = 'available';
            this.showAddForm = true;
            this.showRecurringForm = false;
        },

        // --- Calendar grid (month view) ---

        get monthName() {
            return new Date(this.currentYear, this.currentMonth, 1)
                .toLocaleDateString('it-IT', { month: 'long', year: 'numeric' });
        },

        get calendarDays() {
            const y = this.currentYear;
            const m = this.currentMonth;
            const firstDow = (new Date(y, m, 1).getDay() + 6) % 7;
            const daysInMonth = new Date(y, m + 1, 0).getDate();
            const days = [];
            for (let i = 0; i < firstDow; i++) days.push(null);
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
            this.showRecurringForm = false;
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
                await this.reloadEntries();
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
                await this.reloadEntries();
                this.message = 'Disponibilita eliminata';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            }
        },

        // --- Recurring availability (P6) ---

        openRecurringForm() {
            const y = this.currentYear, m = this.currentMonth;
            this.recurStartDate = this.fmtDate(y, m, 1);
            const lastDay = new Date(y, m + 1, 0).getDate();
            this.recurEndDate = this.fmtDate(y, m, lastDay);
            this.recurDays = [false, false, false, false, false, false, false];
            this.recurStartTime = '08:00';
            this.recurEndTime = '20:00';
            this.recurType = 'available';
            this.recurPreview = [];
            this.recurBothShifts = false;
            this.showRecurringForm = true;
            this.showAddForm = false;
        },

        openDayPreset() {
            this.openRecurringForm();
            this.recurStartTime = '08:00';
            this.recurEndTime = '20:00';
            this.recurBothShifts = false;
        },

        openNightPreset() {
            this.openRecurringForm();
            this.recurStartTime = '20:00';
            this.recurEndTime = '08:00';
            this.recurBothShifts = false;
        },

        openBothPreset() {
            this.openRecurringForm();
            this.recurStartTime = '08:00';
            this.recurEndTime = '20:00';
            this.recurBothShifts = true;
        },

        get recurDayLabels() {
            return ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'];
        },

        updateRecurPreview() {
            this.recurPreview = this.generateRecurDates();
        },

        generateRecurDates() {
            if (!this.recurStartDate || !this.recurEndDate) return [];
            const selectedDays = [];
            this.recurDays.forEach((checked, i) => { if (checked) selectedDays.push(i); });
            if (selectedDays.length === 0) return [];

            const dates = [];
            const start = new Date(this.recurStartDate + 'T00:00:00');
            const end = new Date(this.recurEndDate + 'T00:00:00');
            const current = new Date(start);

            while (current <= end) {
                const dow = (current.getDay() + 6) % 7; // Mon=0
                if (selectedDays.includes(dow)) {
                    dates.push(this.dateToStr(current));
                }
                current.setDate(current.getDate() + 1);
            }
            return dates;
        },

        async saveRecurring() {
            const dates = this.generateRecurDates();
            if (dates.length === 0) {
                this.message = 'Seleziona almeno un giorno della settimana';
                return;
            }
            this.savingRecur = true;
            this.message = '';
            try {
                let entries;
                if (this.recurBothShifts) {
                    // Create one day entry (08:00-20:00) and one night entry (20:00-08:00) per date
                    entries = dates.flatMap(d => [
                        { date: d, start_time: '08:00:00', end_time: '20:00:00', availability_type: this.recurType },
                        { date: d, start_time: '20:00:00', end_time: '08:00:00', availability_type: this.recurType },
                    ]);
                } else {
                    entries = dates.map(d => ({
                        date: d,
                        start_time: this.recurStartTime + ':00',
                        end_time: this.recurEndTime + ':00',
                        availability_type: this.recurType,
                    }));
                }
                await API.post('/me/availability/bulk', { entries });
                await this.reloadEntries();
                this.showRecurringForm = false;
                this.message = (this.recurBothShifts ? dates.length * 2 : dates.length) + ' disponibilita create con successo';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.savingRecur = false;
            }
        },

        // --- Repeat previous month (P6) ---

        get currentMonthHasEntries() {
            return this.entries.length > 0;
        },

        async repeatPreviousMonth() {
            this.repeatingMonth = true;
            this.message = '';
            try {
                // Get previous month range
                let prevMonth = this.currentMonth - 1;
                let prevYear = this.currentYear;
                if (prevMonth < 0) { prevMonth = 11; prevYear--; }

                const prevStart = this.fmtDate(prevYear, prevMonth, 1);
                const prevLastDay = new Date(prevYear, prevMonth + 1, 0).getDate();
                const prevEnd = this.fmtDate(prevYear, prevMonth, prevLastDay);

                const prevEntries = await API.get('/me/availability', { start: prevStart, end: prevEnd });
                if (prevEntries.length === 0) {
                    this.message = 'Il mese precedente non ha disponibilita da copiare';
                    return;
                }

                // Map dates by matching day-of-week
                const targetYear = this.currentYear;
                const targetMonth = this.currentMonth;
                const targetLastDay = new Date(targetYear, targetMonth + 1, 0).getDate();

                const newEntries = [];
                for (const entry of prevEntries) {
                    const srcDate = new Date(entry.date + 'T00:00:00');
                    const srcDow = srcDate.getDay();

                    // Find same day-of-week in target month
                    for (let d = 1; d <= targetLastDay; d++) {
                        const targetDate = new Date(targetYear, targetMonth, d);
                        if (targetDate.getDay() === srcDow) {
                            // Match by week number within month
                            const srcWeek = Math.floor((srcDate.getDate() - 1) / 7);
                            const targetWeek = Math.floor((d - 1) / 7);
                            if (srcWeek === targetWeek) {
                                newEntries.push({
                                    date: this.dateToStr(targetDate),
                                    start_time: entry.start_time,
                                    end_time: entry.end_time,
                                    availability_type: entry.availability_type,
                                });
                                break;
                            }
                        }
                    }
                }

                if (newEntries.length === 0) {
                    this.message = 'Nessuna disponibilita mappabile al mese corrente';
                    return;
                }

                await API.post('/me/availability/bulk', { entries: newEntries });
                await this.loadMonth();
                this.message = newEntries.length + ' disponibilita copiate dal mese precedente';
            } catch (e) {
                this.message = 'Errore: ' + e.message;
            } finally {
                this.repeatingMonth = false;
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

        dateToStr(d) {
            return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
        },
    };
}
