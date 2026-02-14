/* ============================================================
   UPLINK WEB - Screen Type 5: Access Log Viewer
   Displays system access logs with per-entry and bulk
   deletion via the Log_Deleter tool.
   ============================================================ */

const ScreenLog = {

    /**
     * Render an access log screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.logs - Log entries [{id, ip, action, timestamp}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Access Logs';
        container.appendChild(title);

        const logs = Array.isArray(data.logs) ? data.logs : [];

        // Toolbar: Delete All button
        if (logs.length > 0) {
            const toolbar = document.createElement('div');
            toolbar.style.padding = '6px 8px';
            toolbar.style.display = 'flex';
            toolbar.style.justifyContent = 'space-between';
            toolbar.style.alignItems = 'center';
            toolbar.style.borderBottom = '1px solid rgba(0, 255, 65, 0.15)';

            const countLabel = document.createElement('span');
            countLabel.className = 'text-dim';
            countLabel.style.fontSize = '11px';
            countLabel.textContent = logs.length + ' log entr' + (logs.length === 1 ? 'y' : 'ies');

            const deleteAllBtn = document.createElement('button');
            deleteAllBtn.style.cssText = 'background:none;border:1px solid var(--danger);color:var(--danger);' +
                'font-family:inherit;font-size:10px;padding:3px 8px;cursor:pointer;';
            deleteAllBtn.textContent = 'DELETE ALL LOGS';
            deleteAllBtn.addEventListener('click', () => {
                deleteAllBtn.disabled = true;
                deleteAllBtn.textContent = 'DELETING...';
                logs.forEach(log => {
                    GameSocket.runTool('Log_Deleter', 1, GameState.connection.targetIp, { log_id: log.id });
                });
            });

            toolbar.appendChild(countLabel);
            toolbar.appendChild(deleteAllBtn);
            container.appendChild(toolbar);
        }

        if (logs.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No access logs found.';
            container.appendChild(empty);
            return;
        }

        // Column header
        const header = document.createElement('div');
        header.className = 'screen-log-row';
        header.style.fontWeight = '700';
        header.style.color = 'var(--dim)';
        header.style.display = 'flex';
        header.style.justifyContent = 'space-between';
        header.style.borderBottom = '1px solid var(--dim)';
        header.innerHTML = '<span style="flex:1">TIMESTAMP</span>' +
            '<span style="flex:1">SOURCE IP</span>' +
            '<span style="flex:2">ACTION</span>' +
            '<span style="width:50px;text-align:right"></span>';
        container.appendChild(header);

        // Log entries
        const logList = document.createElement('div');

        logs.forEach(log => {
            const row = document.createElement('div');
            row.className = 'screen-log-row';
            row.style.display = 'flex';
            row.style.justifyContent = 'space-between';
            row.style.alignItems = 'center';

            // Timestamp
            const timeSpan = document.createElement('span');
            timeSpan.className = 'log-time';
            timeSpan.style.flex = '1';
            timeSpan.textContent = escapeHtml(log.timestamp || '--:--:--');

            // Source IP
            const ipSpan = document.createElement('span');
            ipSpan.style.flex = '1';
            ipSpan.style.color = 'var(--highlight)';
            ipSpan.style.fontSize = '11px';
            ipSpan.textContent = escapeHtml(log.ip || '0.0.0.0');

            // Action
            const actionSpan = document.createElement('span');
            actionSpan.style.flex = '2';
            actionSpan.style.color = 'var(--primary)';
            actionSpan.textContent = escapeHtml(log.action || '');

            // Delete button
            const delWrap = document.createElement('span');
            delWrap.style.width = '50px';
            delWrap.style.textAlign = 'right';

            const delBtn = document.createElement('button');
            delBtn.style.cssText = 'background:none;border:none;color:var(--danger);' +
                'font-family:inherit;font-size:10px;cursor:pointer;padding:0;';
            delBtn.textContent = '[DEL]';
            delBtn.addEventListener('click', () => {
                GameSocket.runTool('Log_Deleter', 1, GameState.connection.targetIp, { log_id: log.id });
                row.style.opacity = '0.3';
                delBtn.disabled = true;
            });

            delWrap.appendChild(delBtn);

            row.appendChild(timeSpan);
            row.appendChild(ipSpan);
            row.appendChild(actionSpan);
            row.appendChild(delWrap);

            logList.appendChild(row);
        });

        container.appendChild(logList);
    }
};
