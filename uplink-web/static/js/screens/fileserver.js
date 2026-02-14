/* ============================================================
   UPLINK WEB - Screen Type 3: File Server Screen
   Displays files on a connected computer with copy/delete
   actions that invoke hacking tools.
   ============================================================ */

const ScreenFileServer = {

    /**
     * Render a file server screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.files - File list [{id, name, size, encrypted, type}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'File Server';
        container.appendChild(title);

        const files = Array.isArray(data.files) ? data.files : [];

        if (files.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No files found on this system.';
            container.appendChild(empty);
            return;
        }

        // Table header
        const header = document.createElement('div');
        header.className = 'screen-file-row';
        header.style.borderBottom = '1px solid var(--primary)';
        header.style.fontWeight = '700';
        header.style.fontSize = '11px';
        header.style.color = 'var(--dim)';
        header.innerHTML = '<span style="flex:2">NAME</span>' +
            '<span style="flex:1;text-align:right">SIZE</span>' +
            '<span style="flex:1;text-align:center">TYPE</span>' +
            '<span style="flex:1;text-align:right">ACTIONS</span>';
        container.appendChild(header);

        // File rows
        files.forEach(file => {
            const row = document.createElement('div');
            row.className = 'screen-file-row';

            // File name with optional lock icon
            const nameCell = document.createElement('span');
            nameCell.style.flex = '2';
            nameCell.style.cursor = 'pointer';
            nameCell.className = 'screen-file-name';

            if (file.encrypted) {
                const lock = document.createElement('span');
                lock.style.color = 'var(--warning)';
                lock.style.marginRight = '4px';
                lock.textContent = '[LOCKED]';
                nameCell.appendChild(lock);
            }

            const nameText = document.createTextNode(escapeHtml(file.name || 'unknown'));
            nameCell.appendChild(nameText);

            nameCell.addEventListener('click', () => {
                this._showFileDetails(container, data, file);
            });

            // Size
            const sizeCell = document.createElement('span');
            sizeCell.className = 'screen-file-size';
            sizeCell.style.flex = '1';
            sizeCell.style.textAlign = 'right';
            sizeCell.textContent = this._formatSize(file.size);

            // Type
            const typeCell = document.createElement('span');
            typeCell.style.flex = '1';
            typeCell.style.textAlign = 'center';
            typeCell.style.color = 'var(--dim)';
            typeCell.style.fontSize = '11px';
            typeCell.textContent = escapeHtml(file.type || 'data');

            // Actions
            const actionsCell = document.createElement('span');
            actionsCell.style.flex = '1';
            actionsCell.style.textAlign = 'right';
            actionsCell.style.display = 'flex';
            actionsCell.style.gap = '6px';
            actionsCell.style.justifyContent = 'flex-end';

            const copyBtn = document.createElement('button');
            copyBtn.style.cssText = 'background:none;border:1px solid var(--highlight);color:var(--highlight);' +
                'font-family:inherit;font-size:10px;padding:2px 6px;cursor:pointer;';
            copyBtn.textContent = 'COPY';
            copyBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                GameSocket.runTool('File_Copier', 1, GameState.connection.targetIp, { file_id: file.id });
                copyBtn.textContent = '...';
                copyBtn.disabled = true;
            });

            const delBtn = document.createElement('button');
            delBtn.style.cssText = 'background:none;border:1px solid var(--danger);color:var(--danger);' +
                'font-family:inherit;font-size:10px;padding:2px 6px;cursor:pointer;';
            delBtn.textContent = 'DEL';
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                GameSocket.runTool('File_Deleter', 1, GameState.connection.targetIp, { file_id: file.id });
                delBtn.textContent = '...';
                delBtn.disabled = true;
            });

            actionsCell.appendChild(copyBtn);
            actionsCell.appendChild(delBtn);

            row.appendChild(nameCell);
            row.appendChild(sizeCell);
            row.appendChild(typeCell);
            row.appendChild(actionsCell);

            container.appendChild(row);
        });

        // File count summary
        const summary = document.createElement('div');
        summary.className = 'text-dim';
        summary.style.padding = '8px';
        summary.style.fontSize = '11px';
        summary.style.textAlign = 'right';
        const totalSize = files.reduce((sum, f) => sum + (f.size || 0), 0);
        summary.textContent = files.length + ' file(s) - ' + this._formatSize(totalSize) + ' total';
        container.appendChild(summary);
    },

    /**
     * Show detailed info for a single file.
     * @param {HTMLElement} container
     * @param {Object} data - Full screen data (for back navigation)
     * @param {Object} file - The file object
     */
    _showFileDetails(container, data, file) {
        container.innerHTML = '';

        // Back button
        const back = document.createElement('div');
        back.className = 'screen-menu-item';
        back.style.color = 'var(--dim)';
        back.textContent = '< Back to file list';
        back.addEventListener('click', () => this.render(container, data));
        container.appendChild(back);

        const details = document.createElement('div');
        details.style.padding = '12px 8px';

        const lines = [
            { label: 'Filename', value: file.name || 'unknown' },
            { label: 'Size', value: this._formatSize(file.size) },
            { label: 'Type', value: file.type || 'data' },
            { label: 'Encrypted', value: file.encrypted ? 'Yes' : 'No' },
            { label: 'File ID', value: String(file.id) }
        ];

        lines.forEach(line => {
            const row = document.createElement('div');
            row.style.marginBottom = '6px';

            const label = document.createElement('span');
            label.className = 'text-dim';
            label.textContent = line.label + ': ';

            const val = document.createElement('span');
            val.style.color = line.label === 'Encrypted' && file.encrypted
                ? 'var(--warning)' : 'var(--primary)';
            val.textContent = line.value;

            row.appendChild(label);
            row.appendChild(val);
            details.appendChild(row);
        });

        container.appendChild(details);
    },

    /**
     * Format file size in human-readable form.
     * @param {number} bytes
     * @returns {string}
     */
    _formatSize(bytes) {
        if (bytes === undefined || bytes === null) return '?';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }
};
