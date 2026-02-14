/**
 * Bounce chain display and management.
 * Shows the current routing chain in the bottom bar and provides
 * connect/disconnect functionality.
 */
const BounceChain = {
    container: null,
    connectBtn: null,

    init() {
        this.container = document.getElementById('bounce-chain');
        this.connectBtn = document.getElementById('connect-btn');

        GameState.on('connection_updated', () => this.render());

        if (this.connectBtn) {
            this.connectBtn.addEventListener('click', () => {
                if (GameState.connection.isConnected) {
                    GameSocket.disconnectFrom();
                } else if (GameState.connection.bounceChain && GameState.connection.bounceChain.length > 0) {
                    GameSocket.connectTo();
                } else {
                    if (typeof App !== 'undefined' && App.showNotification) {
                        App.showNotification('Add nodes to bounce chain first', 'warning');
                    }
                }
            });
        }
    },

    /**
     * Render the bounce chain display and update the connect button state.
     */
    render() {
        if (!this.container) return;

        const chain = GameState.connection.bounceChain || [];
        const isConnected = GameState.connection.isConnected;

        if (chain.length === 0) {
            this.container.innerHTML = '<span style="color:#006622;font-size:11px;">Click map nodes to build route</span>';
        } else {
            const parts = chain.map(function(node) {
                const tracedClass = node.is_traced ? 'traced' : '';
                let removeBtn = '';
                if (!isConnected) {
                    removeBtn = '<span class="bounce-remove" onclick="BounceChain.remove(' + node.position + ')">\u00d7</span>';
                }
                return '<span class="bounce-node ' + tracedClass + '" data-pos="' + node.position + '">'
                    + node.ip + removeBtn + '</span>';
            });
            this.container.innerHTML = parts.join('<span style="color:#006622;">\u2192</span>');
        }

        // Update connect/disconnect button
        if (this.connectBtn) {
            if (isConnected) {
                this.connectBtn.textContent = '[ DISCONNECT ]';
                this.connectBtn.classList.add('connected');
            } else {
                this.connectBtn.textContent = '[ CONNECT ]';
                this.connectBtn.classList.remove('connected');
            }
        }
    },

    /**
     * Remove a node from the bounce chain by position.
     * @param {number} position
     */
    remove(position) {
        GameSocket.bounceRemove(position);
    }
};
