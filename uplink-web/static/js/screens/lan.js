/* ============================================================
   UPLINK WEB - Screen Type 9: LAN View
   Displays a visual network topology with interactive nodes.
   Nodes can be hacked, accessed, or inspected depending on
   their current status.
   ============================================================ */

const ScreenLAN = {

    /** Node type to color mapping */
    _nodeColors: {
        router:   'var(--highlight)',   // cyan
        server:   'var(--primary)',     // green
        terminal: 'var(--warning)',     // amber
        auth:     'var(--danger)',      // red
        log:      'var(--secondary)'   // dim green
    },

    /** Node type display labels */
    _nodeLabels: {
        router:   'RTR',
        server:   'SRV',
        terminal: 'TRM',
        auth:     'AUTH',
        log:      'LOG'
    },

    /**
     * Render a LAN view screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.nodes - Network nodes [{id, type, name, x, y, status, connections}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Local Area Network';
        container.appendChild(title);

        const nodes = Array.isArray(data.nodes) ? data.nodes : [];

        if (nodes.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No network topology data available.';
            container.appendChild(empty);
            return;
        }

        // Legend
        const legend = document.createElement('div');
        legend.style.cssText = 'display:flex;gap:12px;padding:6px 8px;font-size:10px;' +
            'border-bottom:1px solid rgba(0, 255, 65, 0.15);flex-wrap:wrap;';

        Object.keys(this._nodeColors).forEach(type => {
            const item = document.createElement('span');
            item.style.display = 'flex';
            item.style.alignItems = 'center';
            item.style.gap = '4px';

            const dot = document.createElement('span');
            dot.style.cssText = 'display:inline-block;width:8px;height:8px;border-radius:50%;' +
                'background:' + this._nodeColors[type] + ';';

            const label = document.createElement('span');
            label.style.color = 'var(--dim)';
            label.textContent = type.charAt(0).toUpperCase() + type.slice(1);

            item.appendChild(dot);
            item.appendChild(label);
            legend.appendChild(item);
        });

        // Status legend
        const statuses = [
            { label: 'Locked', symbol: '[L]', color: 'var(--danger)' },
            { label: 'Unlocked', symbol: '[U]', color: 'var(--primary)' },
            { label: 'Compromised', symbol: '[C]', color: 'var(--warning)' }
        ];
        statuses.forEach(s => {
            const item = document.createElement('span');
            item.style.color = s.color;
            item.style.fontSize = '10px';
            item.textContent = s.symbol + ' ' + s.label;
            legend.appendChild(item);
        });

        container.appendChild(legend);

        // Network graph area
        const graph = document.createElement('div');
        graph.style.cssText = 'position:relative;width:100%;height:300px;background:var(--bg);' +
            'border:1px solid rgba(0, 255, 65, 0.1);overflow:hidden;';

        // Build a node lookup map for connection drawing
        const nodeMap = {};
        nodes.forEach(n => { nodeMap[n.id] = n; });

        // Draw connection lines using SVG overlay
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;';
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');

        // Compute bounds for normalization
        const bounds = this._computeBounds(nodes);

        // Draw lines for each connection
        const drawnPairs = new Set();
        nodes.forEach(node => {
            const conns = Array.isArray(node.connections) ? node.connections : [];
            conns.forEach(targetId => {
                const pairKey = [Math.min(node.id, targetId), Math.max(node.id, targetId)].join('-');
                if (drawnPairs.has(pairKey)) return;
                drawnPairs.add(pairKey);

                const target = nodeMap[targetId];
                if (!target) return;

                const from = this._normalizePosition(node, bounds);
                const to = this._normalizePosition(target, bounds);

                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', from.x + '%');
                line.setAttribute('y1', from.y + '%');
                line.setAttribute('x2', to.x + '%');
                line.setAttribute('y2', to.y + '%');
                line.setAttribute('stroke', 'rgba(0, 255, 65, 0.2)');
                line.setAttribute('stroke-width', '1');
                line.setAttribute('stroke-dasharray', '4,4');
                svg.appendChild(line);
            });
        });

        graph.appendChild(svg);

        // Draw nodes
        nodes.forEach(node => {
            const pos = this._normalizePosition(node, bounds);
            const color = this._nodeColors[node.type] || 'var(--primary)';

            const nodeEl = document.createElement('div');
            nodeEl.style.cssText = 'position:absolute;transform:translate(-50%,-50%);' +
                'cursor:pointer;text-align:center;z-index:1;';
            nodeEl.style.left = pos.x + '%';
            nodeEl.style.top = pos.y + '%';

            // Node circle
            const circle = document.createElement('div');
            const size = node.type === 'router' ? 32 : 26;
            circle.style.cssText = 'width:' + size + 'px;height:' + size + 'px;border-radius:50%;' +
                'border:2px solid ' + color + ';display:flex;align-items:center;justify-content:center;' +
                'font-size:8px;font-weight:700;color:' + color + ';margin:0 auto;' +
                'transition:background 0.2s,box-shadow 0.2s;';

            // Status-based styling
            if (node.status === 'compromised') {
                circle.style.background = 'rgba(255, 170, 0, 0.15)';
                circle.style.boxShadow = '0 0 8px rgba(255, 170, 0, 0.3)';
            } else if (node.status === 'unlocked') {
                circle.style.background = 'rgba(0, 255, 65, 0.1)';
            } else {
                circle.style.background = 'rgba(0, 0, 0, 0.5)';
            }

            circle.textContent = this._nodeLabels[node.type] || '?';

            // Node label
            const label = document.createElement('div');
            label.style.cssText = 'font-size:9px;color:var(--dim);white-space:nowrap;margin-top:2px;' +
                'max-width:80px;overflow:hidden;text-overflow:ellipsis;';
            label.textContent = escapeHtml(node.name || 'Node ' + node.id);

            // Status indicator
            const statusTag = document.createElement('div');
            statusTag.style.cssText = 'font-size:8px;margin-top:1px;';
            if (node.status === 'locked') {
                statusTag.style.color = 'var(--danger)';
                statusTag.textContent = '[LOCKED]';
            } else if (node.status === 'unlocked') {
                statusTag.style.color = 'var(--primary)';
                statusTag.textContent = '[OPEN]';
            } else if (node.status === 'compromised') {
                statusTag.style.color = 'var(--warning)';
                statusTag.textContent = '[PWNED]';
            }

            nodeEl.appendChild(circle);
            nodeEl.appendChild(label);
            nodeEl.appendChild(statusTag);

            // Hover effect
            nodeEl.addEventListener('mouseenter', () => {
                circle.style.boxShadow = '0 0 12px ' + color;
            });
            nodeEl.addEventListener('mouseleave', () => {
                if (node.status === 'compromised') {
                    circle.style.boxShadow = '0 0 8px rgba(255, 170, 0, 0.3)';
                } else {
                    circle.style.boxShadow = 'none';
                }
            });

            // Click handler
            nodeEl.addEventListener('click', (e) => {
                e.stopPropagation();
                this._showNodeMenu(graph, node, pos, data);
            });

            graph.appendChild(nodeEl);
        });

        container.appendChild(graph);
    },

    /**
     * Show a context menu for a LAN node.
     * @param {HTMLElement} graphArea
     * @param {Object} node
     * @param {Object} pos - Normalized {x, y} percentages
     * @param {Object} data - Full screen data
     */
    _showNodeMenu(graphArea, node, pos, data) {
        // Remove any existing menu
        const existing = graphArea.querySelector('.lan-node-menu');
        if (existing) existing.remove();

        const menu = document.createElement('div');
        menu.className = 'lan-node-menu';
        menu.style.cssText = 'position:absolute;z-index:10;background:var(--panel-bg);' +
            'border:1px solid var(--primary);padding:4px 0;min-width:140px;font-size:11px;';
        menu.style.left = pos.x + '%';
        menu.style.top = (pos.y + 5) + '%';

        // Node header
        const header = document.createElement('div');
        header.style.cssText = 'padding:4px 8px;color:var(--highlight);font-weight:700;' +
            'border-bottom:1px solid var(--dim);font-size:10px;';
        header.textContent = escapeHtml(node.name || 'Node ' + node.id) +
            ' (' + (node.type || '?') + ')';
        menu.appendChild(header);

        if (node.status === 'locked') {
            // Locked node: offer hacking tools
            this._addMenuItem(menu, 'LAN Force', () => {
                GameSocket.runTool('LAN_Force', 1, GameState.connection.targetIp, {
                    node_id: node.id
                });
                menu.remove();
            });

            this._addMenuItem(menu, 'LAN Spoof', () => {
                GameSocket.runTool('LAN_Spoof', 1, GameState.connection.targetIp, {
                    node_id: node.id
                });
                menu.remove();
            });
        } else {
            // Unlocked or compromised: show details and access option
            const detailRow = document.createElement('div');
            detailRow.style.cssText = 'padding:4px 8px;color:var(--dim);font-size:10px;';
            detailRow.textContent = 'Status: ' + (node.status || 'unknown');
            menu.appendChild(detailRow);

            this._addMenuItem(menu, 'Access Node', () => {
                GameSocket.screenAction('lan_action', {
                    node_id: node.id,
                    action: 'access'
                });
                menu.remove();
            });
        }

        // Close option
        this._addMenuItem(menu, 'Close', () => {
            menu.remove();
        });

        // Close menu when clicking outside
        const closeHandler = (e) => {
            if (!menu.contains(e.target)) {
                menu.remove();
                graphArea.removeEventListener('click', closeHandler);
            }
        };
        setTimeout(() => {
            graphArea.addEventListener('click', closeHandler);
        }, 0);

        graphArea.appendChild(menu);
    },

    /**
     * Add a clickable item to a context menu.
     * @param {HTMLElement} menu
     * @param {string} label
     * @param {Function} onClick
     */
    _addMenuItem(menu, label, onClick) {
        const item = document.createElement('div');
        item.style.cssText = 'padding:4px 8px;cursor:pointer;color:var(--primary);' +
            'transition:background 0.15s;';
        item.textContent = label;

        item.addEventListener('mouseenter', () => {
            item.style.background = 'rgba(0, 255, 65, 0.1)';
        });
        item.addEventListener('mouseleave', () => {
            item.style.background = 'transparent';
        });
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            onClick();
        });

        menu.appendChild(item);
    },

    /**
     * Compute bounding box from node coordinates.
     * @param {Array} nodes
     * @returns {Object} {minX, maxX, minY, maxY}
     */
    _computeBounds(nodes) {
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;

        nodes.forEach(n => {
            if (n.x < minX) minX = n.x;
            if (n.x > maxX) maxX = n.x;
            if (n.y < minY) minY = n.y;
            if (n.y > maxY) maxY = n.y;
        });

        // Add padding
        const padX = (maxX - minX) * 0.1 || 10;
        const padY = (maxY - minY) * 0.1 || 10;

        return {
            minX: minX - padX,
            maxX: maxX + padX,
            minY: minY - padY,
            maxY: maxY + padY
        };
    },

    /**
     * Normalize a node's position to percentage coordinates within bounds.
     * @param {Object} node
     * @param {Object} bounds
     * @returns {Object} {x, y} as percentages (0-100)
     */
    _normalizePosition(node, bounds) {
        const rangeX = bounds.maxX - bounds.minX || 1;
        const rangeY = bounds.maxY - bounds.minY || 1;

        return {
            x: ((node.x - bounds.minX) / rangeX) * 90 + 5,
            y: ((node.y - bounds.minY) / rangeY) * 85 + 7.5
        };
    }
};
