/* ============================================================
   UPLINK WEB - Screen: User ID Entry
   Simple username-only input (like password but without
   password field). Sends the entered username as password.
   ============================================================ */

const ScreenUserID = {

    /**
     * Render a User ID entry screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {string} [data.prompt] - Prompt text displayed above the form
     * @param {string} [data.error] - Error message to display
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Enter User ID';
        container.appendChild(title);

        // Prompt text
        if (data.prompt) {
            const prompt = document.createElement('div');
            prompt.style.padding = '12px 8px 8px';
            prompt.style.color = 'var(--secondary)';
            prompt.textContent = data.prompt;
            container.appendChild(prompt);
        }

        // Error message
        if (data.error) {
            const error = document.createElement('div');
            error.style.padding = '8px';
            error.style.color = 'var(--danger)';
            error.style.fontSize = '12px';
            error.textContent = data.error;
            container.appendChild(error);
        }

        // Form
        const form = document.createElement('div');
        form.style.padding = '8px';
        form.style.display = 'flex';
        form.style.flexDirection = 'column';
        form.style.gap = '12px';

        // Username field
        const userLabel = document.createElement('label');
        userLabel.className = 'text-dim';
        userLabel.style.fontSize = '11px';
        userLabel.style.display = 'block';
        userLabel.textContent = 'USER ID:';

        const userInput = document.createElement('input');
        userInput.type = 'text';
        userInput.className = 'terminal-input';
        userInput.placeholder = 'Enter user ID';
        userInput.autocomplete = 'off';
        userInput.spellcheck = false;

        const userField = document.createElement('div');
        userField.appendChild(userLabel);
        userField.appendChild(userInput);
        form.appendChild(userField);

        // Submit button
        const btnWrap = document.createElement('div');
        btnWrap.style.textAlign = 'center';
        btnWrap.style.marginTop = '8px';

        const submitBtn = document.createElement('button');
        submitBtn.className = 'terminal-btn';
        submitBtn.textContent = 'SUBMIT';

        const doSubmit = () => {
            const username = userInput.value.trim();

            if (!username) {
                userInput.style.borderColor = 'var(--danger)';
                userInput.focus();
                return;
            }

            submitBtn.disabled = true;
            submitBtn.textContent = 'SUBMITTING...';

            GameSocket.screenAction('password_submit', {
                password: username
            });
        };

        submitBtn.addEventListener('click', doSubmit);

        // Allow Enter key to submit
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                doSubmit();
            }
        });

        // Reset border color on input
        userInput.addEventListener('input', () => {
            userInput.style.borderColor = 'var(--primary)';
        });

        btnWrap.appendChild(submitBtn);
        form.appendChild(btnWrap);

        container.appendChild(form);

        // Auto-focus the input field
        setTimeout(() => userInput.focus(), 50);
    },

    /**
     * Escape a string for safe HTML insertion.
     * @param {string} s
     * @returns {string}
     */
    _esc(s) {
        const div = document.createElement('div');
        div.textContent = s || '';
        return div.innerHTML;
    }
};
