/* ============================================================
   UPLINK WEB - Screen: Hardware Sales
   Hardware catalog with buy buttons for upgrading gateway.
   ============================================================ */

const ScreenHWSales = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Hardware Sales';
        container.appendChild(title);

        const items = Array.isArray(data.items) ? data.items : [];

        if (items.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No hardware available.';
            container.appendChild(empty);
            return;
        }

        const header = document.createElement('div');
        header.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;color:var(--dim);' +
            'border-bottom:1px solid var(--dim);font-weight:700;';
        header.innerHTML = '<span style="flex:2">ITEM</span>' +
            '<span style="flex:1">SPEC</span>' +
            '<span style="flex:1;text-align:right">PRICE</span>' +
            '<span style="flex:0 0 70px;text-align:center">ACTION</span>';
        container.appendChild(header);

        const listWrap = document.createElement('div');
        listWrap.style.maxHeight = '350px';
        listWrap.style.overflowY = 'auto';

        items.forEach(item => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;padding:5px 8px;border-bottom:1px solid rgba(0,255,255,0.1);' +
                'font-size:12px;align-items:center;';

            const nameSpan = document.createElement('span');
            nameSpan.style.cssText = 'flex:2;color:var(--highlight);';
            nameSpan.textContent = item.name || '---';

            const specSpan = document.createElement('span');
            specSpan.style.cssText = 'flex:1;color:var(--text);';
            specSpan.textContent = item.spec || item.description || '---';

            const priceSpan = document.createElement('span');
            priceSpan.style.cssText = 'flex:1;text-align:right;color:var(--warning);font-weight:600;';
            priceSpan.textContent = (item.price || 0).toLocaleString() + 'c';

            const btnWrap = document.createElement('span');
            btnWrap.style.cssText = 'flex:0 0 70px;text-align:center;';

            const buyBtn = document.createElement('button');
            buyBtn.className = 'terminal-btn';
            buyBtn.style.fontSize = '10px';
            buyBtn.textContent = 'BUY';
            buyBtn.addEventListener('click', () => {
                buyBtn.disabled = true;
                buyBtn.textContent = '...';
                GameSocket.screenAction('buy', { item_id: item.id, item_name: item.name });
            });
            btnWrap.appendChild(buyBtn);

            row.appendChild(nameSpan);
            row.appendChild(specSpan);
            row.appendChild(priceSpan);
            row.appendChild(btnWrap);
            listWrap.appendChild(row);
        });

        container.appendChild(listWrap);
    }
};
