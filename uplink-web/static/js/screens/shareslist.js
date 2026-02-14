/* ============================================================
   UPLINK WEB - Screen: Stock Market Listing
   Displays available stocks with prices, change indicators,
   and inline buy/sell trade controls.
   ============================================================ */

const ScreenSharesList = {

    /**
     * Render a stock market listing screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.stocks - [{company_name, price, change}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Stock Market';
        container.appendChild(title);

        const stocks = Array.isArray(data.stocks) ? data.stocks : [];

        if (stocks.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No stocks currently listed.';
            container.appendChild(empty);
            return;
        }

        // Table header
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;color:var(--dim);' +
            'border-bottom:1px solid var(--dim);font-weight:700;';
        header.innerHTML = '<span style="flex:2">COMPANY</span>' +
            '<span style="flex:1;text-align:right">PRICE</span>' +
            '<span style="flex:1;text-align:right">CHANGE</span>';
        container.appendChild(header);

        // Stock rows
        stocks.forEach(stock => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;padding:6px 8px;font-size:11px;' +
                'border-bottom:1px solid rgba(0,102,34,0.1);cursor:pointer;transition:background 0.15s;';

            row.addEventListener('mouseenter', () => {
                row.style.background = 'rgba(0,255,65,0.05)';
            });
            row.addEventListener('mouseleave', () => {
                row.style.background = 'transparent';
            });

            const nameSpan = document.createElement('span');
            nameSpan.style.cssText = 'flex:2;color:var(--highlight);';
            nameSpan.textContent = this._esc(stock.company_name || '---');

            const priceSpan = document.createElement('span');
            priceSpan.style.cssText = 'flex:1;text-align:right;color:var(--warning);font-weight:600;';
            priceSpan.textContent = (stock.price || 0).toLocaleString() + 'c';

            const change = stock.change || 0;
            const changeSpan = document.createElement('span');
            changeSpan.style.cssText = 'flex:1;text-align:right;font-weight:600;';
            if (change > 0) {
                changeSpan.style.color = '#00ff41';
                changeSpan.textContent = '+' + change.toLocaleString();
            } else if (change < 0) {
                changeSpan.style.color = 'var(--danger)';
                changeSpan.textContent = change.toLocaleString();
            } else {
                changeSpan.style.color = 'var(--dim)';
                changeSpan.textContent = '0';
            }

            row.appendChild(nameSpan);
            row.appendChild(priceSpan);
            row.appendChild(changeSpan);

            // Click to show inline trade controls
            row.addEventListener('click', () => {
                this._toggleTradeControls(container, row, stock);
            });

            container.appendChild(row);
        });
    },

    /**
     * Toggle inline buy/sell trade controls beneath a stock row.
     * @param {HTMLElement} container
     * @param {HTMLElement} row - The clicked row element
     * @param {Object} stock - The stock data
     */
    _toggleTradeControls(container, row, stock) {
        // Remove any existing trade panel
        const existing = container.querySelector('.trade-controls');
        if (existing) {
            existing.remove();
            return;
        }

        const panel = document.createElement('div');
        panel.className = 'trade-controls';
        panel.style.cssText = 'padding:8px;background:rgba(0,255,65,0.03);' +
            'border-bottom:1px solid rgba(0,255,65,0.15);display:flex;align-items:center;gap:8px;';

        const label = document.createElement('span');
        label.style.cssText = 'color:var(--highlight);font-size:11px;flex-shrink:0;';
        label.textContent = this._esc(stock.company_name) + ':';
        panel.appendChild(label);

        const sharesInput = document.createElement('input');
        sharesInput.type = 'number';
        sharesInput.className = 'terminal-input';
        sharesInput.placeholder = 'Shares';
        sharesInput.min = '1';
        sharesInput.style.cssText = 'width:80px;font-size:11px;';
        panel.appendChild(sharesInput);

        const buyBtn = document.createElement('button');
        buyBtn.className = 'terminal-btn';
        buyBtn.style.fontSize = '10px';
        buyBtn.textContent = 'BUY';
        buyBtn.addEventListener('click', () => {
            const shares = parseInt(sharesInput.value, 10);
            if (!shares || shares <= 0) return;
            buyBtn.disabled = true;
            buyBtn.textContent = 'BUYING...';
            GameSocket.screenAction('buy_stock', {
                company_name: stock.company_name,
                shares: shares
            });
        });
        panel.appendChild(buyBtn);

        const sellBtn = document.createElement('button');
        sellBtn.className = 'terminal-btn';
        sellBtn.style.fontSize = '10px';
        sellBtn.textContent = 'SELL';
        sellBtn.addEventListener('click', () => {
            const shares = parseInt(sharesInput.value, 10);
            if (!shares || shares <= 0) return;
            sellBtn.disabled = true;
            sellBtn.textContent = 'SELLING...';
            GameSocket.screenAction('sell_stock', {
                company_name: stock.company_name,
                shares: shares
            });
        });
        panel.appendChild(sellBtn);

        // Insert after the clicked row
        row.after(panel);
    },

    _esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
