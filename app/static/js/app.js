document.addEventListener('alpine:init', () => {

    Alpine.store('app', {
        page: 'dashboard',
        user: null,
        unreadNotifications: 0,

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
                '#/documenti': 'documenti',
                '#/mie-offerte': 'mie-offerte',
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

        async pollNotifications() {
            if (!Auth.isAuthenticated()) return;
            try {
                const data = await API.get('/me/notifications/unread-count');
                this.unreadNotifications = data.count;
            } catch {}
            setTimeout(() => this.pollNotifications(), 30000);
        },

        logout() {
            Auth.logout();
            this.user = null;
            this.page = 'login';
        },
    });

});
