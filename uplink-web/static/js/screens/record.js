/* ============================================================
   UPLINK WEB - Screen: Record Viewer
   Generic record display (used for person records, database
   entries, etc.) with labeled fields.
   ============================================================ */

const ScreenRecord = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Record';
        container.appendChild(title);

        const fields = Array.isArray(data.fields) ? data.fields :
            (data.record ? Object.entries(data.record).map(([k, v]) => ({ label: k, value: v })) : []);

        if (fields.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No record data available.';
            container.appendChild(empty);
            return;
        }

        const block = document.createElement('div');
        block.style.padding = '12px 8px';

        fields.forEach(field => {
            const row = document.createElement('div');
            row.style.cssText = 'margin-bottom:8px;display:flex;gap:8px;';

            const label = document.createElement('span');
            label.className = 'text-dim';
            label.style.cssText = 'font-size:11px;min-width:140px;text-transform:uppercase;';
            label.textContent = (field.label || 'FIELD') + ':';

            const value = document.createElement('span');
            value.style.color = 'var(--primary)';
            const div = document.createElement('div');
            div.textContent = String(field.value != null ? field.value : '---');
            value.textContent = div.textContent;

            row.appendChild(label);
            row.appendChild(value);
            block.appendChild(row);
        });

        container.appendChild(block);

        // Edit button if editable
        if (data.editable) {
            const editBtn = document.createElement('button');
            editBtn.className = 'terminal-btn';
            editBtn.style.margin = '8px';
            editBtn.textContent = 'EDIT RECORD';
            editBtn.addEventListener('click', () => {
                editBtn.disabled = true;
                GameSocket.screenAction('edit_record', { record_id: data.record_id });
            });
            container.appendChild(editBtn);
        }
    }
};
