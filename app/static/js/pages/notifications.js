function notificationsDropdown() {
    return {
        notifications: [],
        open: false,
        loading: false,

        async toggle() {
            this.open = !this.open;
            if (this.open) await this.load();
        },

        async load() {
            this.loading = true;
            try {
                this.notifications = await API.get('/me/notifications/', { limit: 10 });
            } catch {}
            this.loading = false;
        },

        async markRead(id) {
            try {
                await API.patch('/me/notifications/' + id + '/read');
                const n = this.notifications.find(n => n.id === id);
                if (n) n.status = 'read';
                Alpine.store('app').unreadNotifications = Math.max(0, Alpine.store('app').unreadNotifications - 1);
            } catch {}
        },

        async markAllRead() {
            try {
                await API.post('/me/notifications/read-all');
                this.notifications.forEach(n => n.status = 'read');
                Alpine.store('app').unreadNotifications = 0;
            } catch {}
        },

        timeAgo(dateStr) {
            const diff = Date.now() - new Date(dateStr).getTime();
            const mins = Math.floor(diff / 60000);
            if (mins < 60) return `${mins}m fa`;
            const hours = Math.floor(mins / 60);
            if (hours < 24) return `${hours}h fa`;
            return `${Math.floor(hours / 24)}g fa`;
        },
    };
}
