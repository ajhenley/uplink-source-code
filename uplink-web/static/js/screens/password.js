/* ============================================================
   UPLINK WEB - Screen Type 2: Password Entry Screen
   Shows a username/password login form for computer access.
   ============================================================ */

const ScreenPassword = {

    /**
     * Render a password entry screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title (e.g., "Authentication Required")
     * @param {string} data.prompt - Prompt text displayed above the form
     * @param {string} [data.error] - Error message to display (e.g., "Invalid credentials")
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Authentication Required';
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
        userLabel.textContent = 'USERNAME:';

        const userInput = document.createElement('input');
        userInput.type = 'text';
        userInput.className = 'terminal-input';
        userInput.placeholder = 'Enter username';
        userInput.autocomplete = 'off';
        userInput.spellcheck = false;

        const userField = document.createElement('div');
        userField.appendChild(userLabel);
        userField.appendChild(userInput);
        form.appendChild(userField);

        // Password field
        const passLabel = document.createElement('label');
        passLabel.className = 'text-dim';
        passLabel.style.fontSize = '11px';
        passLabel.style.display = 'block';
        passLabel.textContent = 'PASSWORD:';

        const passInput = document.createElement('input');
        passInput.type = 'password';
        passInput.className = 'terminal-input';
        passInput.placeholder = 'Enter password';
        passInput.autocomplete = 'off';

        const passField = document.createElement('div');
        passField.appendChild(passLabel);
        passField.appendChild(passInput);
        form.appendChild(passField);

        // Submit button
        const btnWrap = document.createElement('div');
        btnWrap.style.textAlign = 'center';
        btnWrap.style.marginTop = '8px';

        const submitBtn = document.createElement('button');
        submitBtn.className = 'terminal-btn';
        submitBtn.textContent = 'LOGIN';

        const doLogin = () => {
            const username = userInput.value.trim();
            const password = passInput.value;

            if (!username) {
                userInput.style.borderColor = 'var(--danger)';
                userInput.focus();
                return;
            }

            submitBtn.disabled = true;
            submitBtn.textContent = 'AUTHENTICATING...';

            GameSocket.screenAction('login', {
                username: username,
                password: password
            });
        };

        submitBtn.addEventListener('click', doLogin);

        // Allow Enter key to submit from either input
        const onKeyDown = (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                doLogin();
            }
        };
        userInput.addEventListener('keydown', onKeyDown);
        passInput.addEventListener('keydown', onKeyDown);

        // Reset border color on input
        userInput.addEventListener('input', () => {
            userInput.style.borderColor = 'var(--primary)';
        });

        btnWrap.appendChild(submitBtn);
        form.appendChild(btnWrap);

        container.appendChild(form);

        // Auto-focus the username field
        setTimeout(() => userInput.focus(), 50);
    }
};
