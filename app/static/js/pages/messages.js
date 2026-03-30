function messagesPage() {
    return {
        conversations: [],
        contacts: [],
        messages: [],
        activeUserId: null,
        activeUserName: '',
        newMessage: '',
        loading: true,
        loadingThread: false,
        sendingMsg: false,
        showNewConversation: false,

        async init() {
            await this.loadConversations();
            this.loading = false;
        },

        async loadConversations() {
            try {
                this.conversations = await API.get('/me/messages/conversations');
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
        },

        async openConversation(userId, userName) {
            this.activeUserId = userId;
            this.activeUserName = userName;
            this.loadingThread = true;
            this.showNewConversation = false;
            try {
                this.messages = await API.get('/me/messages/' + userId, { limit: 100 });
                // Mark read after loading successfully
                await API.post('/me/messages/' + userId + '/read');
                await this.loadConversations();
                // Update global unread count
                try {
                    const data = await API.get('/me/messages/unread-count');
                    Alpine.store('app').unreadMessages = data.count;
                } catch {}
                // Auto-scroll
                this.$nextTick(() => {
                    const el = document.getElementById('chat-thread');
                    if (el) el.scrollTop = el.scrollHeight;
                });
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
            this.loadingThread = false;
        },

        async sendMessage() {
            if (!this.newMessage.trim() || !this.activeUserId) return;
            this.sendingMsg = true;
            try {
                await API.post('/me/messages/' + this.activeUserId, {
                    body: this.newMessage.trim(),
                });
                this.newMessage = '';
                // Reload thread
                this.messages = await API.get('/me/messages/' + this.activeUserId, { limit: 100 });
                await this.loadConversations();
                this.$nextTick(() => {
                    const el = document.getElementById('chat-thread');
                    if (el) el.scrollTop = el.scrollHeight;
                });
            } catch (e) {
                Alpine.store('app').toast(e.message || 'Errore invio messaggio', 'error');
            }
            this.sendingMsg = false;
        },

        async loadContacts() {
            try {
                this.contacts = await API.get('/me/messages/contacts');
            } catch (e) {
                Alpine.store('app').toast('Errore: ' + e.message, 'error');
            }
        },

        async startNewConversation(contact) {
            this.showNewConversation = false;
            await this.openConversation(contact.user_id, contact.name);
        },

        async openNewConversation() {
            await this.loadContacts();
            this.showNewConversation = true;
        },

        backToList() {
            this.activeUserId = null;
            this.activeUserName = '';
            this.messages = [];
        },

        isMe(senderId) {
            const user = Alpine.store('app').user;
            return user && senderId === user.id;
        },

        timeAgo(dateStr) {
            if (!dateStr) return '';
            const diff = Date.now() - new Date(dateStr).getTime();
            const mins = Math.floor(diff / 60000);
            if (mins < 1) return 'ora';
            if (mins < 60) return mins + 'm';
            const hours = Math.floor(mins / 60);
            if (hours < 24) return hours + 'h';
            const days = Math.floor(hours / 24);
            return days + 'g';
        },

        fmtTime(dateStr) {
            if (!dateStr) return '';
            return new Date(dateStr).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
        },

        fmtDate(dateStr) {
            if (!dateStr) return '';
            return new Date(dateStr).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' });
        },

        roleLabel(role) {
            return { admin: 'Admin', superadmin: 'Admin', coordinatore: 'Coordinatore', medico: 'Medico' }[role] || role;
        },

        roleColor(role) {
            if (['admin', 'superadmin', 'coordinatore'].includes(role)) return 'badge-blue';
            return 'badge-green';
        },

        truncate(text, len) {
            if (!text) return '';
            return text.length > len ? text.substring(0, len) + '...' : text;
        },
    };
}
