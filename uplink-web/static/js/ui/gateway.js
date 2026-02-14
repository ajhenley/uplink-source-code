/**
 * Gateway hardware/software management panel with store access.
 */
const GatewayPanel = {
    panelBody: null,
    activeTab: 'info',
    hwCatalog: null,
    swCatalog: null,

    init() {
        this.panelBody = Panels.create('gateway', 'GATEWAY', 480, 420);
        GameState.on('gateway_updated', () => {
            if (this.activeTab === 'info') this.render();
        });
        Panels.hide('gateway');
    },

    toggle() {
        Panels.toggle('gateway');
        if (Panels.panels['gateway'] && Panels.panels['gateway'].isVisible) {
            this.render();
        }
    },

    render() {
        if (!this.panelBody) return;

        let html = '<div class="finance-tabs">'
            + '<button class="tab-btn' + (this.activeTab === 'info' ? ' active' : '') + '" onclick="GatewayPanel.showTab(\'info\')">Status</button>'
            + '<button class="tab-btn' + (this.activeTab === 'hw_store' ? ' active' : '') + '" onclick="GatewayPanel.showTab(\'hw_store\')">Hardware</button>'
            + '<button class="tab-btn' + (this.activeTab === 'sw_store' ? ' active' : '') + '" onclick="GatewayPanel.showTab(\'sw_store\')">Software</button>'
            + '</div>';

        if (this.activeTab === 'info') {
            html += this.renderInfo();
        } else if (this.activeTab === 'hw_store') {
            html += this.renderHWStore();
        } else if (this.activeTab === 'sw_store') {
            html += this.renderSWStore();
        }

        this.panelBody.innerHTML = html;
    },

    renderInfo() {
        const g = GameState.gateway || {};
        const software = GameState.software || [];

        let softwareHtml = '';
        if (software.length === 0) {
            softwareHtml = '<div style="color:var(--dim);">No software installed</div>';
        } else {
            softwareHtml = software.map(s =>
                '<div style="padding:2px 0;color:var(--text);">' + this.esc(s.name) + '</div>'
            ).join('');
        }

        return '<div style="padding:12px;">'
            + '<h3 style="color:var(--cyan);margin:0 0 10px;">' + this.esc(g.name || 'Gateway') + '</h3>'
            + '<div style="margin:4px 0;color:var(--text);">CPU: <span style="color:var(--cyan);">' + (g.cpu_speed || 0) + ' MHz</span></div>'
            + '<div style="margin:4px 0;color:var(--text);">Modem: <span style="color:var(--cyan);">' + (g.modem_speed || 0) + ' GHz</span></div>'
            + '<div style="margin:4px 0;color:var(--text);">Memory: <span style="color:var(--cyan);">' + (g.memory_size || 0) + ' Gqs</span></div>'
            + '<div style="margin:4px 0;color:var(--text);">Self-Destruct: <span style="color:' + (g.has_self_destruct ? 'var(--primary)' : 'var(--dim)') + ';">' + (g.has_self_destruct ? 'INSTALLED' : 'Not installed') + '</span></div>'
            + '<div style="margin:4px 0;color:var(--text);">Motion Sensor: <span style="color:' + (g.has_motion_sensor ? 'var(--primary)' : 'var(--dim)') + ';">' + (g.has_motion_sensor ? 'INSTALLED' : 'Not installed') + '</span></div>'
            + '<hr style="border-color:var(--border);margin:10px 0;">'
            + '<div style="color:var(--dim);font-size:11px;margin-bottom:6px;">INSTALLED SOFTWARE</div>'
            + '<div style="max-height:120px;overflow-y:auto;">' + softwareHtml + '</div>'
            + '</div>';
    },

    renderHWStore() {
        if (!this.hwCatalog) {
            return '<div style="color:var(--dim);padding:20px;text-align:center;">Loading hardware catalog...</div>';
        }

        let html = '<div style="padding:8px;max-height:320px;overflow-y:auto;">';
        for (const item of this.hwCatalog) {
            html += '<div style="border-bottom:1px solid var(--border);padding:8px 4px;">'
                + '<div style="color:var(--cyan);">' + this.esc(item.name) + '</div>'
                + '<div style="color:var(--dim);font-size:11px;">' + this.esc(item.description || '') + '</div>'
                + '<div style="margin-top:4px;">'
                + '<span style="color:var(--warning);">' + (item.price || 0).toLocaleString() + 'c</span> '
                + '<button class="terminal-btn terminal-btn-small" onclick="GatewayPanel.buyHW(\'' + item.type + '\',' + (item.level || 1) + ')">[BUY]</button>'
                + '</div></div>';
        }
        html += '</div>';
        return html;
    },

    renderSWStore() {
        if (!this.swCatalog) {
            return '<div style="color:var(--dim);padding:20px;text-align:center;">Loading software catalog...</div>';
        }

        let html = '<div style="padding:8px;max-height:320px;overflow-y:auto;">';
        for (const item of this.swCatalog) {
            html += '<div style="border-bottom:1px solid var(--border);padding:8px 4px;">'
                + '<div style="color:var(--cyan);">' + this.esc(item.name) + ' v' + (item.version || 1) + '</div>'
                + '<div style="margin-top:4px;">'
                + '<span style="color:var(--warning);">' + (item.price || 0).toLocaleString() + 'c</span> '
                + '<button class="terminal-btn terminal-btn-small" onclick="GatewayPanel.buySW(\'' + item.tool_name + '\',' + (item.version || 1) + ')">[BUY]</button>'
                + '</div></div>';
        }
        html += '</div>';
        return html;
    },

    async showTab(tab) {
        this.activeTab = tab;
        if (tab === 'hw_store' && !this.hwCatalog) {
            try {
                const resp = await fetch('/api/session/' + GAME_SESSION_ID + '/store/hardware');
                if (resp.ok) { this.hwCatalog = (await resp.json()).catalog; }
            } catch (e) { /* ignore */ }
        }
        if (tab === 'sw_store' && !this.swCatalog) {
            try {
                const resp = await fetch('/api/session/' + GAME_SESSION_ID + '/store/software');
                if (resp.ok) { this.swCatalog = (await resp.json()).catalog; }
            } catch (e) { /* ignore */ }
        }
        this.render();
    },

    buyHW(type, level) {
        GameSocket.socket.emit('buy_hardware', {
            session_id: GAME_SESSION_ID,
            hardware_type: type,
            level: level,
        });
    },

    buySW(toolName, version) {
        GameSocket.socket.emit('buy_software', {
            session_id: GAME_SESSION_ID,
            tool_name: toolName,
            version: version,
        });
    },

    esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }
};
