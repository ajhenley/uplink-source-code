/**
 * Bottom software toolbar showing owned tools.
 * Click a tool button to run it against the currently connected system.
 */
const Toolbar = {
    container: null,

    init() {
        this.container = document.getElementById('software-toolbar');
        GameState.on('player_updated', () => this.render());
        GameState.on('software_updated', () => this.render());
    },

    /**
     * Render the list of available software tools as buttons.
     */
    render() {
        if (!this.container) return;
        this.container.innerHTML = '';

        const software = GameState.software || [];
        software.forEach(sw => {
            const btn = document.createElement('button');
            btn.className = 'tool-btn';
            btn.textContent = sw.name + ' v' + sw.version;
            btn.title = sw.name;
            btn.addEventListener('click', () => this.activateTool(sw));
            this.container.appendChild(btn);
        });
    },

    /**
     * Activate a tool against the currently connected system.
     * @param {{ name: string, version: number }} sw
     */
    activateTool(sw) {
        if (!GameState.connection.isConnected) {
            if (typeof App !== 'undefined' && App.showNotification) {
                App.showNotification('Not connected to any system', 'warning');
            }
            return;
        }
        GameSocket.runTool(sw.name, sw.version, GameState.connection.targetIp, {});
    }
};
