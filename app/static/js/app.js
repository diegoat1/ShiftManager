document.addEventListener('alpine:init', () => {

    Alpine.store('app', {
        page: 'dashboard',

        init() {
            this.handleRoute();
            window.addEventListener('hashchange', () => this.handleRoute());
        },

        handleRoute() {
            const hash = window.location.hash || '#/';
            const routes = {
                '#/': 'dashboard',
                '#/medici': 'medici',
                '#/strutture': 'strutture',
                '#/calendario': 'calendario',
            };
            this.page = routes[hash] || 'dashboard';
        },

        navigate(hash) {
            window.location.hash = hash;
        },
    });

});
