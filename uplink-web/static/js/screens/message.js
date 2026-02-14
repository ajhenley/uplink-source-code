/* ============================================================
   UPLINK WEB - Screen Type 1: Message / Info Display Screen
   Shows a title, body text, and optional navigation button.
   ============================================================ */

const ScreenMessage = {

    /**
     * Render a message screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Message title
     * @param {string} data.body - Message body (may contain newlines)
     * @param {string} [data.button_label] - Optional button text
     * @param {number} [data.next_page] - Optional page to navigate to on button click
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Message';
        container.appendChild(title);

        // Body text
        const body = document.createElement('div');
        body.style.padding = '12px 8px';
        body.style.lineHeight = '1.6';
        body.style.color = 'var(--primary)';
        body.style.whiteSpace = 'pre-wrap';

        // Convert the body text: escape HTML then preserve newlines
        const rawText = data.body || '';
        const lines = rawText.split('\n');
        for (let i = 0; i < lines.length; i++) {
            if (i > 0) {
                body.appendChild(document.createElement('br'));
            }
            body.appendChild(document.createTextNode(lines[i]));
        }

        container.appendChild(body);

        // Optional navigation button
        if (data.button_label) {
            const btnWrap = document.createElement('div');
            btnWrap.style.padding = '12px 8px';
            btnWrap.style.textAlign = 'center';

            const btn = document.createElement('button');
            btn.className = 'terminal-btn';
            btn.textContent = data.button_label;

            if (data.next_page !== undefined && data.next_page !== null) {
                btn.addEventListener('click', () => {
                    GameSocket.screenAction('navigate', { next_page: data.next_page });
                });
            }

            btnWrap.appendChild(btn);
            container.appendChild(btnWrap);
        }
    }
};
