/* ============================================================
   UPLINK WEB - Screen Type 0: Menu Screen
   Shows a list of clickable menu items that navigate to
   other screens on the connected computer.
   ============================================================ */

const ScreenMenu = {

    /**
     * Render a menu screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Menu title
     * @param {Array} data.items - Menu items [{label, action, next_page}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Main Menu';
        container.appendChild(title);

        // Menu items list
        const list = document.createElement('div');
        list.style.marginTop = '8px';

        const items = Array.isArray(data.items) ? data.items : [];

        if (items.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No menu options available.';
            list.appendChild(empty);
        }

        items.forEach((item, index) => {
            const row = document.createElement('div');
            row.className = 'screen-menu-item';
            row.setAttribute('role', 'button');
            row.setAttribute('tabindex', '0');

            // Index number prefix for the classic Uplink look
            const indexSpan = document.createElement('span');
            indexSpan.className = 'text-dim';
            indexSpan.textContent = (index + 1) + '. ';

            const labelSpan = document.createElement('span');
            labelSpan.textContent = escapeHtml(item.label || 'Unknown');

            row.appendChild(indexSpan);
            row.appendChild(labelSpan);

            const navigateTo = item.next_page;

            row.addEventListener('click', () => {
                GameSocket.screenAction('navigate', { next_page: navigateTo });
            });

            // Keyboard accessibility
            row.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    GameSocket.screenAction('navigate', { next_page: navigateTo });
                }
            });

            list.appendChild(row);
        });

        container.appendChild(list);
    }
};
