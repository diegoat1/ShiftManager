const Auth = {
    TOKEN_KEY: 'shiftmanager_token',
    USER_KEY: 'shiftmanager_user',

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    setToken(token) {
        localStorage.setItem(this.TOKEN_KEY, token);
    },

    getUser() {
        const u = localStorage.getItem(this.USER_KEY);
        return u ? JSON.parse(u) : null;
    },

    setUser(user) {
        localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    },

    isAuthenticated() {
        return !!this.getToken();
    },

    isAdmin() {
        const user = this.getUser();
        return user && ['superadmin', 'admin', 'coordinatore'].includes(user.role);
    },

    isMedico() {
        const user = this.getUser();
        return user && user.role === 'medico';
    },

    logout() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        window.location.hash = '#/login';
    },

    async fetchMe() {
        try {
            const res = await fetch('/auth/me', {
                headers: { 'Authorization': 'Bearer ' + this.getToken() }
            });
            if (!res.ok) {
                this.logout();
                return null;
            }
            const user = await res.json();
            this.setUser(user);
            return user;
        } catch {
            this.logout();
            return null;
        }
    }
};
