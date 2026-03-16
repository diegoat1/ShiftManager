const API = {
    BASE: '/api/v1',

    async request(method, path, body, params) {
        const url = new URL(this.BASE + path, window.location.origin);
        if (params) {
            Object.entries(params).forEach(([k, v]) => {
                if (v !== null && v !== undefined) url.searchParams.set(k, v);
            });
        }
        const opts = { method, headers: {} };
        if (body) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        }
        const res = await fetch(url, opts);
        if (res.status === 204) return null;
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return res.json();
    },

    get(path, params) { return this.request('GET', path, null, params); },
    post(path, body) { return this.request('POST', path, body); },
    patch(path, body) { return this.request('PATCH', path, body); },
    del(path) { return this.request('DELETE', path); },
};
