/* ============================================================
   UPLINK WEB - Screen: Change Gateway
   Confirms gateway relocation with cost and transit time.
   ============================================================ */

const ScreenChangeGW = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Change Gateway Location';
        container.appendChild(title);

        const block = document.createElement('div');
        block.style.padding = '12px 8px';

        // Current location
        if (data.current_location) {
            const curLabel = document.createElement('div');
            curLabel.className = 'text-dim';
            curLabel.style.cssText = 'font-size:11px;margin-bottom:4px;';
            curLabel.textContent = 'CURRENT LOCATION:';
            block.appendChild(curLabel);

            const curValue = document.createElement('div');
            curValue.style.cssText = 'color:var(--primary);margin-bottom:12px;';
            curValue.textContent = data.current_location;
            block.appendChild(curValue);
        }

        // New location
        if (data.new_location) {
            const newLabel = document.createElement('div');
            newLabel.className = 'text-dim';
            newLabel.style.cssText = 'font-size:11px;margin-bottom:4px;';
            newLabel.textContent = 'NEW LOCATION:';
            block.appendChild(newLabel);

            const newValue = document.createElement('div');
            newValue.style.cssText = 'color:var(--highlight);margin-bottom:12px;';
            newValue.textContent = data.new_location;
            block.appendChild(newValue);
        }

        // Cost
        if (data.cost != null) {
            const costLabel = document.createElement('div');
            costLabel.className = 'text-dim';
            costLabel.style.cssText = 'font-size:11px;margin-bottom:4px;';
            costLabel.textContent = 'RELOCATION COST:';
            block.appendChild(costLabel);

            const costValue = document.createElement('div');
            costValue.style.cssText = 'color:var(--warning);font-weight:600;margin-bottom:12px;';
            costValue.textContent = data.cost.toLocaleString() + 'c';
            block.appendChild(costValue);
        }

        container.appendChild(block);

        // Confirm / Cancel buttons
        const btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:12px;padding:8px;justify-content:center;';

        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'terminal-btn';
        confirmBtn.textContent = 'CONFIRM RELOCATION';
        confirmBtn.addEventListener('click', () => {
            confirmBtn.disabled = true;
            confirmBtn.textContent = 'RELOCATING...';
            GameSocket.screenAction('confirm_change_gw', { location_id: data.location_id });
        });

        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'terminal-btn';
        cancelBtn.style.color = 'var(--dim)';
        cancelBtn.textContent = 'CANCEL';
        cancelBtn.addEventListener('click', () => {
            GameSocket.screenAction('back', {});
        });

        btnRow.appendChild(confirmBtn);
        btnRow.appendChild(cancelBtn);
        container.appendChild(btnRow);
    }
};
