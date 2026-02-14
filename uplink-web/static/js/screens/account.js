/* ============================================================
   UPLINK WEB - Screen: Bank Account Management
   Shows accounts list with balances, loan info, and a
   transfer form for moving funds between accounts.
   ============================================================ */

const ScreenAccount = {

    /**
     * Render a bank account management screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.accounts - [{id, owner, balance, account_number, loan}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Account Management';
        container.appendChild(title);

        const accounts = Array.isArray(data.accounts) ? data.accounts : [];

        if (accounts.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No accounts found.';
            container.appendChild(empty);
            return;
        }

        // Account listing
        const listHeader = document.createElement('div');
        listHeader.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;color:var(--dim);' +
            'border-bottom:1px solid var(--dim);font-weight:700;';
        listHeader.innerHTML = '<span style="flex:2">OWNER</span>' +
            '<span style="flex:2">ACCOUNT #</span>' +
            '<span style="flex:1;text-align:right">BALANCE</span>' +
            '<span style="flex:1;text-align:right">LOAN</span>';
        container.appendChild(listHeader);

        accounts.forEach(acct => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;padding:6px 8px;font-size:11px;' +
                'border-bottom:1px solid rgba(0,102,34,0.1);';

            const ownerSpan = document.createElement('span');
            ownerSpan.style.cssText = 'flex:2;color:var(--highlight);';
            ownerSpan.textContent = this._esc(acct.owner || '---');

            const numSpan = document.createElement('span');
            numSpan.style.cssText = 'flex:2;color:var(--primary);letter-spacing:1px;';
            numSpan.textContent = this._esc(acct.account_number || '---');

            const balSpan = document.createElement('span');
            balSpan.style.cssText = 'flex:1;text-align:right;color:var(--warning);font-weight:600;';
            balSpan.textContent = (acct.balance || 0).toLocaleString() + 'c';

            const loanSpan = document.createElement('span');
            loanSpan.style.cssText = 'flex:1;text-align:right;color:var(--danger);';
            loanSpan.textContent = acct.loan ? acct.loan.toLocaleString() + 'c' : '0c';

            row.appendChild(ownerSpan);
            row.appendChild(numSpan);
            row.appendChild(balSpan);
            row.appendChild(loanSpan);
            container.appendChild(row);
        });

        // Transfer form
        this._renderTransferForm(container, accounts);
    },

    /**
     * Render the transfer form with account selection.
     * @param {HTMLElement} container
     * @param {Array} accounts
     */
    _renderTransferForm(container, accounts) {
        const section = document.createElement('div');
        section.style.padding = '8px';
        section.style.marginTop = '8px';
        section.style.borderTop = '1px solid rgba(0, 255, 65, 0.15)';

        const sectionTitle = document.createElement('div');
        sectionTitle.className = 'screen-section-title';
        sectionTitle.textContent = 'Transfer Funds';
        section.appendChild(sectionTitle);

        const form = document.createElement('div');
        form.style.cssText = 'padding:8px 0;display:flex;flex-direction:column;gap:10px;';

        // From account select
        const fromLabel = document.createElement('label');
        fromLabel.className = 'text-dim';
        fromLabel.style.cssText = 'font-size:11px;display:block;';
        fromLabel.textContent = 'FROM ACCOUNT:';

        const fromSelect = document.createElement('select');
        fromSelect.className = 'terminal-input';
        accounts.forEach(acct => {
            const opt = document.createElement('option');
            opt.value = acct.id;
            opt.textContent = acct.account_number + ' (' + (acct.balance || 0).toLocaleString() + 'c)';
            fromSelect.appendChild(opt);
        });

        const fromField = document.createElement('div');
        fromField.appendChild(fromLabel);
        fromField.appendChild(fromSelect);
        form.appendChild(fromField);

        // Target account text input
        const targetLabel = document.createElement('label');
        targetLabel.className = 'text-dim';
        targetLabel.style.cssText = 'font-size:11px;display:block;';
        targetLabel.textContent = 'TARGET ACCOUNT:';

        const targetInput = document.createElement('input');
        targetInput.type = 'text';
        targetInput.className = 'terminal-input';
        targetInput.placeholder = 'Account number';
        targetInput.autocomplete = 'off';
        targetInput.spellcheck = false;

        const targetField = document.createElement('div');
        targetField.appendChild(targetLabel);
        targetField.appendChild(targetInput);
        form.appendChild(targetField);

        // Amount field
        const amountLabel = document.createElement('label');
        amountLabel.className = 'text-dim';
        amountLabel.style.cssText = 'font-size:11px;display:block;';
        amountLabel.textContent = 'AMOUNT:';

        const amountInput = document.createElement('input');
        amountInput.type = 'number';
        amountInput.className = 'terminal-input';
        amountInput.placeholder = '0';
        amountInput.min = '1';
        amountInput.autocomplete = 'off';

        const amountField = document.createElement('div');
        amountField.appendChild(amountLabel);
        amountField.appendChild(amountInput);
        form.appendChild(amountField);

        // Error display
        const errorMsg = document.createElement('div');
        errorMsg.style.cssText = 'color:var(--danger);font-size:11px;display:none;';
        form.appendChild(errorMsg);

        // Submit button
        const btnWrap = document.createElement('div');
        btnWrap.style.textAlign = 'center';

        const transferBtn = document.createElement('button');
        transferBtn.className = 'terminal-btn';
        transferBtn.textContent = 'TRANSFER';

        transferBtn.addEventListener('click', () => {
            const fromId = fromSelect.value;
            const targetAccount = targetInput.value.trim();
            const amount = parseInt(amountInput.value, 10);

            if (!targetAccount) {
                errorMsg.textContent = 'Enter a target account number.';
                errorMsg.style.display = 'block';
                targetInput.focus();
                return;
            }
            if (!amount || amount <= 0) {
                errorMsg.textContent = 'Enter a valid transfer amount.';
                errorMsg.style.display = 'block';
                amountInput.focus();
                return;
            }

            errorMsg.style.display = 'none';
            transferBtn.disabled = true;
            transferBtn.textContent = 'TRANSFERRING...';

            GameSocket.screenAction('transfer', {
                from_account: fromId,
                target_account: targetAccount,
                amount: amount
            });
        });

        btnWrap.appendChild(transferBtn);
        form.appendChild(btnWrap);
        section.appendChild(form);
        container.appendChild(section);
    },

    _esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
