/**
 * Panel management system for draggable/closeable floating panels.
 * All game UI panels (email, missions, gateway, etc.) are created through this system.
 */
const Panels = {
    panels: {},   // id -> { element, isVisible }
    zCounter: 100,

    // Drag state
    _dragPanel: null,
    _dragOffsetX: 0,
    _dragOffsetY: 0,
    _boundOnDrag: null,
    _boundEndDrag: null,

    /**
     * Create a new draggable panel.
     * @param {string} id - Unique panel identifier
     * @param {string} title - Title shown in the panel header
     * @param {number} width - Panel width in pixels
     * @param {number} height - Panel height in pixels
     * @param {string} [content] - Optional initial HTML content for the body
     * @returns {HTMLElement} The panel body element for content injection
     */
    create(id, title, width, height, content) {
        // Remove existing panel with same id if present
        if (this.panels[id]) {
            this.panels[id].element.remove();
            delete this.panels[id];
        }

        const panel = document.createElement('div');
        panel.className = 'panel';
        panel.id = `panel-${id}`;
        panel.style.width = width + 'px';
        panel.style.height = height + 'px';
        panel.style.zIndex = ++this.zCounter;
        panel.style.position = 'absolute';
        panel.style.left = '50px';
        panel.style.top = '50px';

        // Header
        const header = document.createElement('div');
        header.className = 'panel-header';

        const titleEl = document.createElement('span');
        titleEl.className = 'panel-title';
        titleEl.textContent = title;

        const closeBtn = document.createElement('span');
        closeBtn.className = 'panel-close';
        closeBtn.textContent = '[X]';
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.hide(id);
        });

        header.appendChild(titleEl);
        header.appendChild(closeBtn);

        // Dragging from header
        header.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this.bringToFront(id);
            this._startDrag(e, panel);
        });

        // Body
        const body = document.createElement('div');
        body.className = 'panel-body';
        if (content) {
            body.innerHTML = content;
        }

        panel.appendChild(header);
        panel.appendChild(body);

        // Bring to front on any click within the panel
        panel.addEventListener('mousedown', () => {
            this.bringToFront(id);
        });

        // Append to panels container
        const container = document.getElementById('panels-container');
        if (container) {
            container.appendChild(panel);
        } else {
            document.body.appendChild(panel);
        }

        this.panels[id] = { element: panel, isVisible: true };
        return body;
    },

    /**
     * Show a panel and bring it to the front.
     * @param {string} id
     */
    show(id) {
        const entry = this.panels[id];
        if (!entry) return;
        entry.element.style.display = 'block';
        entry.isVisible = true;
        this.bringToFront(id);
    },

    /**
     * Hide a panel.
     * @param {string} id
     */
    hide(id) {
        const entry = this.panels[id];
        if (!entry) return;
        entry.element.style.display = 'none';
        entry.isVisible = false;
    },

    /**
     * Toggle a panel's visibility.
     * @param {string} id
     */
    toggle(id) {
        const entry = this.panels[id];
        if (!entry) return;
        if (entry.isVisible) {
            this.hide(id);
        } else {
            this.show(id);
        }
    },

    /**
     * Bring a panel to the front of the z-order.
     * @param {string} id
     */
    bringToFront(id) {
        const entry = this.panels[id];
        if (!entry) return;
        entry.element.style.zIndex = ++this.zCounter;
    },

    /**
     * Hide all panels.
     */
    closeAll() {
        for (const id in this.panels) {
            this.hide(id);
        }
    },

    // --- Drag implementation ---

    _startDrag(e, panelEl) {
        this._dragPanel = panelEl;
        const rect = panelEl.getBoundingClientRect();
        this._dragOffsetX = e.clientX - rect.left;
        this._dragOffsetY = e.clientY - rect.top;

        this._boundOnDrag = this._onDrag.bind(this);
        this._boundEndDrag = this._endDrag.bind(this);

        document.addEventListener('mousemove', this._boundOnDrag);
        document.addEventListener('mouseup', this._boundEndDrag);
    },

    _onDrag(e) {
        if (!this._dragPanel) return;
        const x = e.clientX - this._dragOffsetX;
        const y = e.clientY - this._dragOffsetY;
        this._dragPanel.style.left = x + 'px';
        this._dragPanel.style.top = y + 'px';
    },

    _endDrag() {
        if (this._boundOnDrag) {
            document.removeEventListener('mousemove', this._boundOnDrag);
        }
        if (this._boundEndDrag) {
            document.removeEventListener('mouseup', this._boundEndDrag);
        }
        this._dragPanel = null;
        this._boundOnDrag = null;
        this._boundEndDrag = null;
    }
};
