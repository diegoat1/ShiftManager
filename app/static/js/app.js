document.addEventListener('alpine:init', () => {

    Alpine.store('app', {
        page: 'dashboard',
        user: null,
        unreadNotifications: 0,

        // Toast system
        toasts: [],
        _toastCounter: 0,
        toast(message, type = 'success', duration = 4000) {
            const id = ++this._toastCounter;
            this.toasts.push({ id, message, type });
            setTimeout(() => { this.toasts = this.toasts.filter(t => t.id !== id); }, duration);
        },

        // Messages
        unreadMessages: 0,

        // Doctor badge counts
        pendingOffersCount: 0,
        missingDocsCount: 0,
        expiringCertsCount: 0,

        init() {
            this.user = Auth.getUser();
            this.handleRoute();
            window.addEventListener('hashchange', () => this.handleRoute());
            if (this.user) this.pollNotifications();
        },

        handleRoute() {
            const hash = window.location.hash || '#/';

            // Public routes
            if (hash === '#/login' || hash === '#/register') {
                this.page = hash.substring(2);
                return;
            }

            // Auth check
            if (!Auth.isAuthenticated()) {
                window.location.hash = '#/login';
                this.page = 'login';
                return;
            }

            this.user = Auth.getUser();

            const routes = {
                '#/': 'dashboard',
                '#/medici': 'medici',
                '#/strutture': 'strutture',
                '#/calendario': 'calendario',
                '#/profilo': 'profilo',
                '#/disponibilita': 'disponibilita',
                '#/messaggi': 'messaggi',
                '#/turni-disponibili': 'turni-disponibili',
                '#/miei-turni': 'miei-turni',
                '#/qualifiche': 'documentazione',
                '#/documenti': 'documentazione',
                '#/documentazione': 'documentazione',
                '#/mie-offerte': 'mie-offerte',
                '#/storico': 'storico',
                '#/admin/documenti': 'admin-documenti',
                '#/analytics': 'analytics',
            };
            this.page = routes[hash] || 'dashboard';
        },

        navigate(hash) {
            window.location.hash = hash;
        },

        isAdmin() {
            return this.user && ['superadmin', 'admin', 'coordinatore'].includes(this.user.role);
        },

        isMedico() {
            return this.user && this.user.role === 'medico';
        },

        setDoctorBadgeCounts(data) {
            this.pendingOffersCount = data.pending_offers_count || 0;
            this.missingDocsCount = (data.missing_mandatory_docs || []).length;
            this.expiringCertsCount = (data.expiring_certifications || []).length;
        },

        async pollNotifications() {
            if (!Auth.isAuthenticated()) return;
            try {
                const data = await API.get('/me/notifications/unread-count');
                this.unreadNotifications = data.count;

                // Fetch unread messages count
                try {
                    const msgData = await API.get('/me/messages/unread-count');
                    this.unreadMessages = msgData.count;
                } catch {}

                // Fetch badge counts for doctors
                if (this.isMedico()) {
                    try {
                        const dashboard = await API.get('/me/dashboard');
                        this.setDoctorBadgeCounts(dashboard);
                    } catch {}
                }
            } catch {}
            setTimeout(() => this.pollNotifications(), 60000);
        },

        logout() {
            Auth.logout();
            this.user = null;
            this.page = 'login';
        },
    });

});
