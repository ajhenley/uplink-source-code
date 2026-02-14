/* ============================================================
   UPLINK WEB - Screen: Company Information
   Displays company details in a terminal-styled info block
   with labeled fields.
   ============================================================ */

const ScreenCompanyInfo = {

    /**
     * Render a company info screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Object} data.company - Company details
     * @param {string} data.company.name - Company name
     * @param {number} data.company.size - Company size
     * @param {number} data.company.growth - Growth rate
     * @param {string} data.company.alignment - Alignment (e.g., "Neutral", "Good", "Evil")
     * @param {string} data.company.boss_name - Name of the company boss
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Company Information';
        container.appendChild(title);

        const company = data.company || {};

        if (!company.name) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No company data available.';
            container.appendChild(empty);
            return;
        }

        // Info block
        const block = document.createElement('div');
        block.style.padding = '12px 8px';

        const fields = [
            { label: 'COMPANY NAME', value: company.name },
            { label: 'SIZE',         value: company.size != null ? String(company.size) : '---' },
            { label: 'GROWTH',       value: company.growth != null ? String(company.growth) : '---' },
            { label: 'ALIGNMENT',    value: company.alignment || '---' },
            { label: 'BOSS',         value: company.boss_name || '---' }
        ];

        fields.forEach(field => {
            const row = document.createElement('div');
            row.style.marginBottom = '8px';
            row.style.display = 'flex';
            row.style.gap = '8px';

            const label = document.createElement('span');
            label.className = 'text-dim';
            label.style.fontSize = '11px';
            label.style.minWidth = '130px';
            label.style.textTransform = 'uppercase';
            label.textContent = field.label + ':';

            const value = document.createElement('span');
            value.style.color = 'var(--primary)';
            value.textContent = this._esc(field.value);

            row.appendChild(label);
            row.appendChild(value);
            block.appendChild(row);
        });

        container.appendChild(block);
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
