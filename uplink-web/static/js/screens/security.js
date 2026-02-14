/* ============================================================
   UPLINK WEB - Screen: Security Screen
   Displays security system status for a computer, showing
   active security measures and their states.
   ============================================================ */

const ScreenSecurity = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Security Systems';
        container.appendChild(title);

        const systems = Array.isArray(data.systems) ? data.systems : [];

        if (systems.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No security systems configured.';
            container.appendChild(empty);
            return;
        }

        const header = document.createElement('div');
        header.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;color:var(--dim);' +
            'border-bottom:1px solid var(--dim);font-weight:700;';
        header.innerHTML = '<span style="flex:2">SYSTEM</span>' +
            '<span style="flex:1;text-align:center">LEVEL</span>' +
            '<span style="flex:1;text-align:right">STATUS</span>';
        container.appendChild(header);

        systems.forEach(sys => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;padding:5px 8px;border-bottom:1px solid rgba(0,255,255,0.1);' +
                'font-size:12px;align-items:center;';

            const nameSpan = document.createElement('span');
            nameSpan.style.cssText = 'flex:2;color:var(--highlight);';
            nameSpan.textContent = sys.name || '---';

            const levelSpan = document.createElement('span');
            levelSpan.style.cssText = 'flex:1;text-align:center;color:var(--text);';
            levelSpan.textContent = sys.level != null ? String(sys.level) : '---';

            const statusSpan = document.createElement('span');
            statusSpan.style.cssText = 'flex:1;text-align:right;font-weight:600;';
            if (sys.enabled || sys.active) {
                statusSpan.style.color = '#00ff41';
                statusSpan.textContent = 'ACTIVE';
            } else {
                statusSpan.style.color = 'var(--danger)';
                statusSpan.textContent = 'DISABLED';
            }

            row.appendChild(nameSpan);
            row.appendChild(levelSpan);
            row.appendChild(statusSpan);
            container.appendChild(row);
        });

        // Alert status
        if (data.alert_level) {
            const alert = document.createElement('div');
            alert.style.cssText = 'padding:8px;margin-top:8px;border-top:1px solid var(--danger);' +
                'color:var(--danger);font-weight:700;text-align:center;';
            alert.textContent = 'ALERT LEVEL: ' + data.alert_level;
            container.appendChild(alert);
        }
    }
};
