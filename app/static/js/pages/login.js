function loginPage() {
    return {
        email: '',
        password: '',
        error: '',
        loading: false,
        isRegister: false,
        // Register fields
        firstName: '',
        lastName: '',
        fiscalCode: '',
        phone: '',

        async login() {
            this.error = '';
            this.loading = true;
            try {
                const res = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: this.email, password: this.password }),
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || 'Login fallito');
                }
                const data = await res.json();
                Auth.setToken(data.access_token);
                await Auth.fetchMe();
                Alpine.store('app').user = Auth.getUser();
                window.location.hash = '#/';
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },

        async register() {
            this.error = '';
            this.loading = true;
            try {
                const body = {
                    email: this.email,
                    password: this.password,
                    role: 'medico',
                    fiscal_code: this.fiscalCode,
                    first_name: this.firstName,
                    last_name: this.lastName,
                    phone: this.phone || null,
                };
                const res = await fetch('/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || 'Registrazione fallita');
                }
                const data = await res.json();
                Auth.setToken(data.access_token);
                await Auth.fetchMe();
                Alpine.store('app').user = Auth.getUser();
                window.location.hash = '#/';
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },

        toggleMode() {
            this.isRegister = !this.isRegister;
            this.error = '';
        }
    };
}
