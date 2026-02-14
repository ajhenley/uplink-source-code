/* ============================================================
   UPLINK WEB - Screen: Contact Screen
   Displays a person's contact information with optional
   action buttons.
   ============================================================ */

const ScreenContact = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Contact Information';
        container.appendChild(title);

        const contact = data.contact || data;

        const fields = [
            { label: 'NAME', value: contact.name },
            { label: 'AGE', value: contact.age },
            { label: 'ADDRESS', value: contact.address },
            { label: 'PHONE', value: contact.phone },
            { label: 'STATUS', value: contact.status }
        ].filter(f => f.value != null && f.value !== '');

        if (fields.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No contact data available.';
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
            label.style.cssText = 'font-size:11px;min-width:100px;text-transform:uppercase;';
            label.textContent = field.label + ':';

            const value = document.createElement('span');
            value.style.color = 'var(--primary)';
            value.textContent = String(field.value);

            row.appendChild(label);
            row.appendChild(value);
            block.appendChild(row);
        });

        container.appendChild(block);
    }
};
