/* ============================================================
   UPLINK WEB - Screen: Single Stock Detail View
   Shows detailed information for a single company stock.
   ============================================================ */

const ScreenSharesView = {

    /**
     * Render a single stock detail view into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {string} data.company_name - Company name
     * @param {number} data.price - Current share price
     * @param {number} data.change - Price change
     * @param {number} data.shares_owned - Shares owned by player
     * @param {number} data.high - All-time high price
     * @param {number} data.low - All-time low price
     */
    render(container, data) {
        container.innerHTML = '';

        // Back button
        const back = document.createElement('div');
        back.className = 'screen-menu-item';
        back.style.color = 'var(--dim)';
        back.textContent = '< Back to market';
        back.addEventListener('click', () => {
            GameSocket.screenAction('go_back');
        });
        container.appendChild(back);

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Stock Detail';
        container.appendChild(title);

        // Company name
        const companyName = document.createElement('div');
        companyName.style.cssText = 'padding:12px 8px;color:var(--highlight);font-size:16px;font-weight:700;';
        companyName.textContent = this._esc(data.company_name || '---');
        container.appendChild(companyName);

        // Price info
        const info = document.createElement('div');
        info.style.cssText = 'padding:0 8px 12px;';

        const fields = [
            { label: 'Current Price', value: (data.price || 0).toLocaleString() + 'c', color: 'var(--warning)' },
            { label: 'Change', value: this._formatChange(data.change || 0), color: (data.change || 0) >= 0 ? '#00ff41' : 'var(--danger)' },
            { label: 'Shares Owned', value: String(data.shares_owned || 0), color: 'var(--primary)' }
        ];

        if (data.high !== undefined) {
            fields.push({ label: 'High', value: (data.high || 0).toLocaleString() + 'c', color: '#00ff41' });
        }
        if (data.low !== undefined) {
            fields.push({ label: 'Low', value: (data.low || 0).toLocaleString() + 'c', color: 'var(--danger)' });
        }

        fields.forEach(field => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;justify-content:space-between;padding:4px 0;font-size:12px;';

            const label = document.createElement('span');
            label.className = 'text-dim';
            label.textContent = field.label + ':';

            const val = document.createElement('span');
            val.style.color = field.color;
            val.style.fontWeight = '600';
            val.textContent = field.value;

            row.appendChild(label);
            row.appendChild(val);
            info.appendChild(row);
        });

        container.appendChild(info);
    },

    /**
     * Format a change value with sign and color indicator.
     * @param {number} change
     * @returns {string}
     */
    _formatChange(change) {
        if (change > 0) return '+' + change.toLocaleString();
        if (change < 0) return change.toLocaleString();
        return '0';
    },

    _esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
