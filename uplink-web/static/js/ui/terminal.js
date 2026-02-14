/**
 * Command input terminal.
 * Provides a command line input with history (up/down arrow) support.
 * Commands are sent as screen actions to the connected remote system.
 */
const Terminal = {
    history: [],
    historyIndex: -1,

    /**
     * Initialize the terminal inside the given container element.
     * @param {HTMLElement} containerEl - The element to append the input to
     */
    init(containerEl) {
        if (!containerEl) return;

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'terminal-input terminal-cmd';
        input.placeholder = '>';
        containerEl.appendChild(input);

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const cmd = input.value.trim();
                if (cmd) {
                    this.execute(cmd);
                    this.history.push(cmd);
                    this.historyIndex = this.history.length;
                }
                input.value = '';
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (this.historyIndex > 0) {
                    this.historyIndex--;
                    input.value = this.history[this.historyIndex];
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (this.historyIndex < this.history.length - 1) {
                    this.historyIndex++;
                    input.value = this.history[this.historyIndex];
                } else {
                    this.historyIndex = this.history.length;
                    input.value = '';
                }
            }
        });
    },

    /**
     * Execute a command by sending it as a screen action.
     * @param {string} cmd - The command string
     */
    execute(cmd) {
        if (GameState.connection.isConnected) {
            GameSocket.screenAction('command', { command: cmd });
        }
    }
};
