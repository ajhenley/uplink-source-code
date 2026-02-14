/* ============================================================
   UPLINK WEB - Screen Type 7: Bank Account Screen
   Displays account info, transaction statements, and an
   optional money transfer form.
   ============================================================ */

const ScreenBank = {

    /**
     * Render a bank account screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Bank name
     * @param {number} data.balance - Current account balance
     * @param {string} data.account_number - Account number
     * @param {Array} data.statements - Transaction history [{date, description, amount}]
     * @param {boolean} data.can_transfer - Whether transfers are allowed
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Bank Account';
        container.appendChild(title);

        // Account info section
        const info = document.createElement('div');
        info.style.padding = '12px 8px';
        info.style.borderBottom = '1px solid rgba(0, 255, 65, 0.15)';

        const acctRow = document.createElement('div');
        acctRow.style.marginBottom = '6px';
        const acctLabel = document.createElement('span');
        acctLabel.className = 'text-dim';
        acctLabel.textContent = 'Account: ';
        const acctVal = document.createElement('span');
        acctVal.style.color = 'var(--highlight)';
        acctVal.style.letterSpacing = '1px';
        acctVal.textContent = escapeHtml(data.account_number || '---');
        acctRow.appendChild(acctLabel);
        acctRow.appendChild(acctVal);
        info.appendChild(acctRow);

        const balRow = document.createElement('div');
        const balLabel = document.createElement('span');
        balLabel.className = 'text-dim';
        balLabel.textContent = 'Balance: ';
        const balVal = document.createElement('span');
        balVal.style.color = 'var(--warning)';
        balVal.style.fontWeight = '700';
        balVal.style.fontSize = '16px';
        balVal.textContent = (data.balance || 0).toLocaleString() + 'c';
        balRow.appendChild(balLabel);
        balRow.appendChild(balVal);
        info.appendChild(balRow);

        container.appendChild(info);

        // Statements
        const stmtTitle = document.createElement('div');
        stmtTitle.className = 'screen-section-title';
        stmtTitle.textContent = 'Recent Statements';
        container.appendChild(stmtTitle);

        const statements = Array.isArray(data.statements) ? data.statements : [];

        if (statements.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '8px';
            empty.textContent = 'No recent transactions.';
            container.appendChild(empty);
        } else {
            // Statement header
            const stmtHeader = document.createElement('div');
            stmtHeader.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;color:var(--dim);' +
                'border-bottom:1px solid var(--dim);font-weight:700;';
            stmtHeader.innerHTML = '<span style="flex:1">DATE</span>' +
                '<span style="flex:2">DESCRIPTION</span>' +
                '<span style="flex:1;text-align:right">AMOUNT</span>';
            container.appendChild(stmtHeader);

            statements.forEach(stmt => {
                const row = document.createElement('div');
                row.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;' +
                    'border-bottom:1px solid rgba(0, 102, 34, 0.1);';

                const dateSpan = document.createElement('span');
                dateSpan.style.flex = '1';
                dateSpan.style.color = 'var(--dim)';
                dateSpan.textContent = escapeHtml(stmt.date || '---');

                const descSpan = document.createElement('span');
                descSpan.style.flex = '2';
                descSpan.style.color = 'var(--primary)';
                descSpan.textContent = escapeHtml(stmt.description || '');

                const amountSpan = document.createElement('span');
                amountSpan.style.flex = '1';
                amountSpan.style.textAlign = 'right';
                amountSpan.style.fontWeight = '600';
                const amount = stmt.amount || 0;
                amountSpan.style.color = amount >= 0 ? 'var(--primary)' : 'var(--danger)';
                amountSpan.textContent = (amount >= 0 ? '+' : '') + amount.toLocaleString() + 'c';

                row.appendChild(dateSpan);
                row.appendChild(descSpan);
                row.appendChild(amountSpan);
                container.appendChild(row);
            });
        }

        // Transfer form (if allowed)
        if (data.can_transfer) {
            this._renderTransferForm(container);
        }
    },

    /**
     * Render the money transfer form.
     * @param {HTMLElement} container
     */
    _renderTransferForm(container) {
        const section = document.createElement('div');
        section.style.padding = '8px';
        section.style.marginTop = '8px';
        section.style.borderTop = '1px solid rgba(0, 255, 65, 0.15)';

        const sectionTitle = document.createElement('div');
        sectionTitle.className = 'screen-section-title';
        sectionTitle.textContent = 'Transfer Funds';
        section.appendChild(sectionTitle);

        const form = document.createElement('div');
        form.style.padding = '8px 0';
        form.style.display = 'flex';
        form.style.flexDirection = 'column';
        form.style.gap = '10px';

        // Target account field
        const targetLabel = document.createElement('label');
        targetLabel.className = 'text-dim';
        targetLabel.style.fontSize = '11px';
        targetLabel.style.display = 'block';
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
        amountLabel.style.fontSize = '11px';
        amountLabel.style.display = 'block';
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
        errorMsg.style.color = 'var(--danger)';
        errorMsg.style.fontSize = '11px';
        errorMsg.style.display = 'none';
        form.appendChild(errorMsg);

        // Submit button
        const btnWrap = document.createElement('div');
        btnWrap.style.textAlign = 'center';

        const transferBtn = document.createElement('button');
        transferBtn.className = 'terminal-btn';
        transferBtn.textContent = 'TRANSFER';

        transferBtn.addEventListener('click', () => {
            const targetAccount = targetInput.value.trim();
            const amount = parseInt(amountInput.value, 10);

            // Validation
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
                target_account: targetAccount,
                amount: amount
            });
        });

        btnWrap.appendChild(transferBtn);
        form.appendChild(btnWrap);
        section.appendChild(form);

        container.appendChild(section);
    }
};
