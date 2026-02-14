/* ============================================================
   UPLINK WEB - Screen: Software Sales Store
   Lists available software for purchase, grouped by name,
   with version, cost, size, and description.
   ============================================================ */

const ScreenSWSales = {

    /**
     * Render a software sales screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.software - [{name, version, cost, size, description}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Software Sales';
        container.appendChild(title);

        const software = Array.isArray(data.software) ? data.software : [];

        if (software.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No software currently available for purchase.';
            container.appendChild(empty);
            return;
        }

        // Group software by name
        const groups = {};
        software.forEach((sw, index) => {
            const name = sw.name || 'Unknown';
            if (!groups[name]) groups[name] = [];
            groups[name].push({ ...sw, _index: index });
        });

        // Render each group
        Object.keys(groups).forEach(groupName => {
            const groupTitle = document.createElement('div');
            groupTitle.style.cssText = 'padding:6px 8px;color:var(--highlight);font-size:12px;' +
                'font-weight:700;border-bottom:1px solid rgba(0,255,65,0.15);margin-top:4px;';
            groupTitle.textContent = this._esc(groupName);
            container.appendChild(groupTitle);

            groups[groupName].forEach(sw => {
                const item = document.createElement('div');
                item.style.cssText = 'padding:8px;border-bottom:1px solid rgba(0,102,34,0.1);';

                // Top row: version + cost
                const topRow = document.createElement('div');
                topRow.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;';

                const verSpan = document.createElement('span');
                verSpan.style.cssText = 'color:var(--primary);font-size:12px;';
                verSpan.textContent = 'v' + (sw.version || '1.0');

                const costSpan = document.createElement('span');
                costSpan.style.cssText = 'color:var(--warning);font-weight:700;font-size:12px;';
                costSpan.textContent = (sw.cost || 0).toLocaleString() + 'c';

                topRow.appendChild(verSpan);
                topRow.appendChild(costSpan);
                item.appendChild(topRow);

                // Size
                if (sw.size !== undefined) {
                    const sizeSpan = document.createElement('div');
                    sizeSpan.style.cssText = 'font-size:10px;color:var(--dim);margin-bottom:4px;';
                    sizeSpan.textContent = 'Size: ' + sw.size + ' GQ';
                    item.appendChild(sizeSpan);
                }

                // Description
                if (sw.description) {
                    const desc = document.createElement('div');
                    desc.style.cssText = 'font-size:11px;color:var(--primary);margin-bottom:6px;';
                    desc.textContent = this._esc(sw.description);
                    item.appendChild(desc);
                }

                // Buy button
                const btnWrap = document.createElement('div');
                btnWrap.style.textAlign = 'right';

                const buyBtn = document.createElement('button');
                buyBtn.className = 'terminal-btn';
                buyBtn.style.fontSize = '10px';
                buyBtn.textContent = 'BUY';

                buyBtn.addEventListener('click', () => {
                    buyBtn.disabled = true;
                    buyBtn.textContent = 'PURCHASING...';
                    GameSocket.screenAction('buy_software', { index: sw._index });
                });

                btnWrap.appendChild(buyBtn);
                item.appendChild(btnWrap);
                container.appendChild(item);
            });
        });
    },

    _esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
