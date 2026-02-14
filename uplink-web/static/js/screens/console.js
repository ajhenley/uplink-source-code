/* ============================================================
   UPLINK WEB - Screen Type 6: Admin Console
   Interactive command-line interface for admin-level
   computer access. Supports command history navigation.
   ============================================================ */

const ScreenConsole = {

    /** @type {string[]} Command history buffer */
    _history: [],

    /** @type {number} Current position in the history buffer (-1 = new input) */
    _historyIndex: -1,

    /** @type {string} Saved input when navigating history */
    _savedInput: '',

    /**
     * Render an admin console screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Console title
     * @param {string} data.output - Command output history text
     * @param {string} data.prompt - Prompt string (e.g., "admin>")
     */
    render(container, data) {
        container.innerHTML = '';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.height = '100%';

        // Title bar
        const titleBar = document.createElement('div');
        titleBar.className = 'screen-section-title';
        titleBar.textContent = data.title || 'Admin Console';
        container.appendChild(titleBar);

        // Output area
        const outputArea = document.createElement('div');
        outputArea.style.cssText = 'flex:1;overflow-y:auto;padding:8px;background:var(--bg);' +
            'font-size:12px;line-height:1.5;';

        const outputPre = document.createElement('pre');
        outputPre.style.cssText = 'margin:0;white-space:pre-wrap;word-wrap:break-word;' +
            'color:var(--primary);font-family:inherit;';
        outputPre.textContent = data.output || '';

        outputArea.appendChild(outputPre);
        container.appendChild(outputArea);

        // Scroll to bottom
        setTimeout(() => {
            outputArea.scrollTop = outputArea.scrollHeight;
        }, 10);

        // Input row
        const inputRow = document.createElement('div');
        inputRow.style.cssText = 'display:flex;align-items:center;padding:4px 8px;' +
            'border-top:1px solid var(--dim);background:var(--input-bg);flex-shrink:0;';

        // Prompt label
        const promptLabel = document.createElement('span');
        promptLabel.style.cssText = 'color:var(--highlight);margin-right:6px;white-space:nowrap;font-size:12px;';
        promptLabel.textContent = data.prompt || '>';

        // Command input
        const cmdInput = document.createElement('input');
        cmdInput.type = 'text';
        cmdInput.className = 'terminal-input';
        cmdInput.style.cssText += 'border:none;padding:4px 0;background:transparent;flex:1;';
        cmdInput.placeholder = 'Type a command...';
        cmdInput.autocomplete = 'off';
        cmdInput.spellcheck = false;

        const self = this;

        cmdInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const command = cmdInput.value.trim();
                if (!command) return;

                // Add to history
                self._history.push(command);
                self._historyIndex = -1;
                self._savedInput = '';

                // Append to local output display
                const line = (data.prompt || '>') + ' ' + command + '\n';
                outputPre.textContent += line;
                outputArea.scrollTop = outputArea.scrollHeight;

                // Send command to server
                GameSocket.screenAction('command', { command: command });

                cmdInput.value = '';
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (self._history.length === 0) return;

                if (self._historyIndex === -1) {
                    self._savedInput = cmdInput.value;
                    self._historyIndex = self._history.length - 1;
                } else if (self._historyIndex > 0) {
                    self._historyIndex--;
                }

                cmdInput.value = self._history[self._historyIndex] || '';
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (self._historyIndex === -1) return;

                if (self._historyIndex < self._history.length - 1) {
                    self._historyIndex++;
                    cmdInput.value = self._history[self._historyIndex] || '';
                } else {
                    self._historyIndex = -1;
                    cmdInput.value = self._savedInput;
                }
            }
        });

        inputRow.appendChild(promptLabel);
        inputRow.appendChild(cmdInput);
        container.appendChild(inputRow);

        // Auto-focus the input
        setTimeout(() => cmdInput.focus(), 50);
    }
};
