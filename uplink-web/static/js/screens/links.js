/* ============================================================
   UPLINK WEB - Screen: Links
   Shows clickable IP address links. Each link can be added
   to the player's bounce chain via GameSocket.bounceAdd().
   ============================================================ */

const ScreenLinks = {

    /**
     * Render a links screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.links - Array of link objects [{ip, label, visible_name}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Links';
        container.appendChild(title);

        const links = Array.isArray(data.links) ? data.links : [];

        if (links.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No links available.';
            container.appendChild(empty);
            return;
        }

        // Links list
        const list = document.createElement('div');
        list.style.marginTop = '8px';

        links.forEach((link, index) => {
            const row = document.createElement('div');
            row.className = 'screen-menu-item';
            row.setAttribute('role', 'button');
            row.setAttribute('tabindex', '0');
            row.style.display = 'flex';
            row.style.alignItems = 'center';
            row.style.gap = '8px';

            // Index prefix
            const indexSpan = document.createElement('span');
            indexSpan.className = 'text-dim';
            indexSpan.style.fontSize = '11px';
            indexSpan.style.minWidth = '24px';
            indexSpan.textContent = (index + 1) + '.';

            // IP address
            const ipSpan = document.createElement('span');
            ipSpan.style.color = 'var(--highlight)';
            ipSpan.style.fontFamily = 'inherit';
            ipSpan.textContent = this._esc(link.ip || '0.0.0.0');

            // Label / visible name
            const labelSpan = document.createElement('span');
            labelSpan.className = 'text-dim';
            labelSpan.style.fontSize = '11px';
            const displayName = link.label || link.visible_name || '';
            if (displayName) {
                labelSpan.textContent = '(' + displayName + ')';
            }

            row.appendChild(indexSpan);
            row.appendChild(ipSpan);
            if (displayName) {
                row.appendChild(labelSpan);
            }

            const ip = link.ip;

            row.addEventListener('click', () => {
                GameSocket.bounceAdd(ip);
                row.style.opacity = '0.5';
                setTimeout(() => { row.style.opacity = '1'; }, 300);
            });

            // Keyboard accessibility
            row.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    GameSocket.bounceAdd(ip);
                }
            });

            list.appendChild(row);
        });

        container.appendChild(list);

        // Summary
        const summary = document.createElement('div');
        summary.className = 'text-dim';
        summary.style.padding = '8px';
        summary.style.fontSize = '11px';
        summary.textContent = links.length + ' link(s) available. Click to add to bounce route.';
        container.appendChild(summary);
    },

    /**
     * Escape a string for safe HTML insertion.
     * @param {string} s
     * @returns {string}
     */
    _esc(s) {
        const div = document.createElement('div');
        div.textContent = s || '';
        return div.innerHTML;
    }
};
