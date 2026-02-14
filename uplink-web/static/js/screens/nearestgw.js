/* ============================================================
   UPLINK WEB - Screen: Nearest Gateway Selection
   Displays nearby gateway locations for the player to choose
   for gateway relocation.
   ============================================================ */

const ScreenNearestGW = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Nearest Gateway Locations';
        container.appendChild(title);

        const locations = Array.isArray(data.locations) ? data.locations : [];

        if (locations.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No gateway locations available.';
            container.appendChild(empty);
            return;
        }

        const header = document.createElement('div');
        header.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;color:var(--dim);' +
            'border-bottom:1px solid var(--dim);font-weight:700;';
        header.innerHTML = '<span style="flex:2">LOCATION</span>' +
            '<span style="flex:1;text-align:right">DISTANCE</span>' +
            '<span style="flex:0 0 80px;text-align:center">ACTION</span>';
        container.appendChild(header);

        locations.forEach(loc => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;padding:5px 8px;border-bottom:1px solid rgba(0,255,255,0.1);' +
                'font-size:12px;align-items:center;';

            const nameSpan = document.createElement('span');
            nameSpan.style.cssText = 'flex:2;color:var(--highlight);';
            nameSpan.textContent = loc.name || loc.city || '---';

            const distSpan = document.createElement('span');
            distSpan.style.cssText = 'flex:1;text-align:right;color:var(--text);';
            distSpan.textContent = loc.distance ? loc.distance + ' km' : '---';

            const btnWrap = document.createElement('span');
            btnWrap.style.cssText = 'flex:0 0 80px;text-align:center;';

            const selectBtn = document.createElement('button');
            selectBtn.className = 'terminal-btn';
            selectBtn.style.fontSize = '10px';
            selectBtn.textContent = 'SELECT';
            selectBtn.addEventListener('click', () => {
                selectBtn.disabled = true;
                selectBtn.textContent = '...';
                GameSocket.screenAction('select_gateway', { location_id: loc.id });
            });
            btnWrap.appendChild(selectBtn);

            row.appendChild(nameSpan);
            row.appendChild(distSpan);
            row.appendChild(btnWrap);
            container.appendChild(row);
        });
    }
};
