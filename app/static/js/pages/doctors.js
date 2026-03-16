document.addEventListener('alpine:init', () => {

    Alpine.data('doctorsPage', () => ({
        doctors: [],
        total: 0,
        skip: 0,
        limit: 20,
        search: '',
        loading: true,
        selectedDoctor: null,
        detailLoading: false,

        get filtered() {
            if (!this.search) return this.doctors;
            const q = this.search.toLowerCase();
            return this.doctors.filter(d =>
                d.first_name.toLowerCase().includes(q) ||
                d.last_name.toLowerCase().includes(q) ||
                d.fiscal_code.toLowerCase().includes(q) ||
                d.email.toLowerCase().includes(q)
            );
        },

        get totalPages() {
            return Math.max(1, Math.ceil(this.total / this.limit));
        },

        get currentPage() {
            return Math.floor(this.skip / this.limit) + 1;
        },

        async init() {
            await this.load();
        },

        async load() {
            this.loading = true;
            try {
                const data = await API.get('/doctors/', {
                    skip: this.skip, limit: this.limit,
                });
                this.doctors = data.items;
                this.total = data.total;
            } catch (e) {
                console.error('Doctors load failed:', e);
            }
            this.loading = false;
        },

        async nextPage() {
            if (this.skip + this.limit < this.total) {
                this.skip += this.limit;
                await this.load();
            }
        },

        async prevPage() {
            if (this.skip > 0) {
                this.skip = Math.max(0, this.skip - this.limit);
                await this.load();
            }
        },

        async selectDoctor(id) {
            this.detailLoading = true;
            try {
                this.selectedDoctor = await API.get(`/doctors/${id}`);
            } catch (e) {
                console.error('Doctor detail failed:', e);
            }
            this.detailLoading = false;
        },

        closeDetail() {
            this.selectedDoctor = null;
        },
    }));

});
