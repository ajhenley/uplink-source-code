/**
 * Email panel showing player messages (inbox).
 * Supports listing messages and viewing individual message details.
 */
const EmailPanel = {
    panelBody: null,

    init() {
        this.panelBody = Panels.create('email', 'INBOX', 450, 350);
        GameState.on('messages_updated', () => this.render());
        Panels.hide('email');
    },

    /**
     * Toggle the email panel visibility.
     */
    toggle() {
        Panels.toggle('email');
        if (Panels.panels['email'] && Panels.panels['email'].isVisible) {
            this.render();
        }
    },

    /**
     * Render the message list.
     */
    render() {
        if (!this.panelBody) return;
        const msgs = GameState.messages || [];

        if (msgs.length === 0) {
            this.panelBody.innerHTML = '<div style="color:#006622;padding:20px;text-align:center;">No messages</div>';
            return;
        }

        this.panelBody.innerHTML = msgs.map(m => {
            return '<div class="email-item ' + (m.is_read ? '' : 'unread') + '" data-id="' + m.id + '">'
                + '<div class="email-from">' + this.escapeHtml(m.from_name) + '</div>'
                + '<div class="email-subject">' + this.escapeHtml(m.subject) + '</div>'
                + '</div>';
        }).join('');

        // Click to view individual message
        this.panelBody.querySelectorAll('.email-item').forEach(el => {
            el.addEventListener('click', () => {
                this.viewMessage(parseInt(el.dataset.id));
            });
        });
    },

    /**
     * View a single message by ID.
     * @param {number} id
     */
    viewMessage(id) {
        const msgs = GameState.messages || [];
        const msg = msgs.find(m => m.id === id);
        if (!msg) return;

        msg.is_read = true;

        const bodyText = this.escapeHtml(msg.body || '').replace(/\n/g, '<br>');

        this.panelBody.innerHTML = '<div class="email-detail">'
            + '<div class="email-header">FROM: ' + this.escapeHtml(msg.from_name) + '</div>'
            + '<div class="email-header">SUBJECT: ' + this.escapeHtml(msg.subject) + '</div>'
            + '<hr style="border-color:#006622;">'
            + '<div class="email-body">' + bodyText + '</div>'
            + '<button class="terminal-btn" style="margin-top:10px;font-size:11px;" onclick="EmailPanel.render()">[ BACK ]</button>'
            + '</div>';
    },

    /**
     * Escape HTML to prevent XSS.
     * @param {string} str
     * @returns {string}
     */
    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }
};
