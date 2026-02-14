/**
 * SVG-based world map showing connection nodes as dots.
 * Click nodes to add them to the bounce chain.
 */
const WorldMap = {
    container: null,
    svg: null,
    nodes: [],   // DOM elements for map nodes
    lines: [],   // SVG line elements for connections

    init() {
        this.container = document.getElementById('world-map');
        if (!this.container) return;

        // Create SVG overlay for connection lines
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;';
        this.container.appendChild(this.svg);

        // Listen to GameState events
        GameState.on('map_updated', () => this.renderNodes());
        GameState.on('connection_updated', () => this.renderConnections());
        GameState.on('trace_updated', (data) => this.renderTrace(data));

        // Re-render on window resize to keep positions correct
        window.addEventListener('resize', () => {
            this.renderNodes();
            this.renderConnections();
        });
    },

    /**
     * Render location nodes on the map.
     */
    renderNodes() {
        // Clear old nodes
        this.nodes.forEach(n => n.remove());
        this.nodes = [];

        const locations = GameState.locations || [];
        const bounceIPs = (GameState.connection.bounceChain || []).map(n => n.ip);
        const targetIP = GameState.connection.targetIp;

        locations.forEach(loc => {
            const node = document.createElement('div');
            node.className = 'map-node';

            // Highlight bounce chain nodes
            if (bounceIPs.includes(loc.ip)) {
                node.classList.add('bounce');
            }
            // Highlight active connection target
            if (loc.ip === targetIP && GameState.connection.isConnected) {
                node.classList.add('active');
            }

            const x = this.scaleX(loc.x);
            const y = this.scaleY(loc.y);
            node.style.left = x + 'px';
            node.style.top = y + 'px';

            // Tooltip
            node.title = `${loc.name || 'Unknown'}\n${loc.ip}`;

            // Click to add to bounce chain
            node.addEventListener('click', (e) => {
                e.stopPropagation();
                GameSocket.bounceAdd(loc.ip);
            });

            this.container.appendChild(node);
            this.nodes.push(node);
        });
    },

    /**
     * Render connection lines between bounce chain nodes.
     */
    renderConnections() {
        // Clear old lines
        while (this.svg.firstChild) {
            this.svg.removeChild(this.svg.firstChild);
        }
        this.lines = [];

        const chain = GameState.connection.bounceChain || [];
        if (chain.length < 2) return;

        const isConnected = GameState.connection.isConnected;

        for (let i = 0; i < chain.length - 1; i++) {
            const from = this.getNodePosition(chain[i].ip);
            const to = this.getNodePosition(chain[i + 1].ip);
            if (!from || !to) continue;

            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', from.x);
            line.setAttribute('y1', from.y);
            line.setAttribute('x2', to.x);
            line.setAttribute('y2', to.y);
            line.setAttribute('stroke', isConnected ? '#00ffff' : '#006622');
            line.setAttribute('stroke-width', isConnected ? '2' : '1');
            line.setAttribute('stroke-dasharray', isConnected ? 'none' : '4,4');

            if (isConnected) {
                line.setAttribute('class', 'connection-line-active');
            }

            this.svg.appendChild(line);
            this.lines.push(line);
        }

        // Re-render nodes to update bounce/active classes
        this.renderNodes();
    },

    /**
     * Scale game coordinate X (0-594) to container pixel width.
     * @param {number} x
     * @returns {number}
     */
    scaleX(x) {
        return (x / 594) * this.container.clientWidth;
    },

    /**
     * Scale game coordinate Y (0-316) to container pixel height.
     * @param {number} y
     * @returns {number}
     */
    scaleY(y) {
        return (y / 316) * this.container.clientHeight;
    },

    /**
     * Get the pixel position of a node by IP address.
     * @param {string} ip
     * @returns {{ x: number, y: number } | null}
     */
    getNodePosition(ip) {
        const loc = (GameState.locations || []).find(l => l.ip === ip);
        if (!loc) return null;
        return { x: this.scaleX(loc.x), y: this.scaleY(loc.y) };
    },

    /**
     * Render trace progress visualization on the map.
     * Shows red animated dots progressing backward through the bounce chain
     * when the player has HUD_MapShowTrace software.
     */
    renderTrace() {
        // Remove old trace markers
        const container = document.getElementById('world-map');
        if (!container) return;
        container.querySelectorAll('.trace-marker').forEach(el => el.remove());

        const trace = GameState.connection || {};
        if (!trace.traceActive) return;

        // Check for MapShowTrace software
        const software = GameState.software || [];
        const hasMapTrace = software.some(s => s.name && s.name.includes('MapShowTrace'));
        if (!hasMapTrace) return;

        const chain = trace.bounceChain || [];
        if (chain.length === 0) return;

        const progress = trace.traceProgress || 0;
        const tracedCount = Math.ceil(progress * chain.length);

        // Color traced nodes red (from end backward)
        for (let i = 0; i < tracedCount && i < chain.length; i++) {
            const nodeIdx = chain.length - 1 - i;
            const ip = chain[nodeIdx].ip;
            const loc = (GameState.locations || []).find(l => l.ip === ip);
            if (!loc) continue;

            const x = this.scaleX(loc.x);
            const y = this.scaleY(loc.y);

            const marker = document.createElement('div');
            marker.className = 'trace-marker';
            marker.style.cssText = `position:absolute;left:${x-5}px;top:${y-5}px;width:10px;height:10px;border-radius:50%;background:var(--danger,#ff3333);box-shadow:0 0 8px var(--danger,#ff3333);animation:pulse-red 1s infinite;pointer-events:none;z-index:5;`;
            container.appendChild(marker);
        }
    }
};
