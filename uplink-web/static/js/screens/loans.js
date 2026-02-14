/* ============================================================
   UPLINK WEB - Screen: Loan Management
   Shows current loans on player accounts, loan tier info,
   and a form for taking out new loans.
   ============================================================ */

const ScreenLoans = {

    /**
     * Render a loan management screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.accounts - [{id, account_number, balance, loan}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Loan Management';
        container.appendChild(title);

        const accounts = Array.isArray(data.accounts) ? data.accounts : [];

        // Current loans section
        const loansTitle = document.createElement('div');
        loansTitle.className = 'screen-section-title';
        loansTitle.textContent = 'Current Loans';
        container.appendChild(loansTitle);

        if (accounts.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '8px';
            empty.textContent = 'No accounts available.';
            container.appendChild(empty);
        } else {
            const acctHeader = document.createElement('div');
            acctHeader.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;color:var(--dim);' +
                'border-bottom:1px solid var(--dim);font-weight:700;';
            acctHeader.innerHTML = '<span style="flex:2">ACCOUNT #</span>' +
                '<span style="flex:1;text-align:right">BALANCE</span>' +
                '<span style="flex:1;text-align:right">LOAN</span>';
            container.appendChild(acctHeader);

            accounts.forEach(acct => {
                const row = document.createElement('div');
                row.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;' +
                    'border-bottom:1px solid rgba(0,102,34,0.1);';

                const numSpan = document.createElement('span');
                numSpan.style.cssText = 'flex:2;color:var(--primary);letter-spacing:1px;';
                numSpan.textContent = this._esc(acct.account_number || '---');

                const balSpan = document.createElement('span');
                balSpan.style.cssText = 'flex:1;text-align:right;color:var(--warning);font-weight:600;';
                balSpan.textContent = (acct.balance || 0).toLocaleString() + 'c';

                const loanSpan = document.createElement('span');
                loanSpan.style.cssText = 'flex:1;text-align:right;color:var(--danger);';
                loanSpan.textContent = acct.loan ? acct.loan.toLocaleString() + 'c' : '0c';

                row.appendChild(numSpan);
                row.appendChild(balSpan);
                row.appendChild(loanSpan);
                container.appendChild(row);
            });
        }

        // Loan tiers info
        this._renderLoanTiers(container);

        // Take loan form
        this._renderLoanForm(container, accounts);
    },

    /**
     * Render loan tier information table.
     * @param {HTMLElement} container
     */
    _renderLoanTiers(container) {
        const section = document.createElement('div');
        section.style.cssText = 'padding:8px;margin-top:8px;border-top:1px solid rgba(0,255,65,0.15);';

        const sectionTitle = document.createElement('div');
        sectionTitle.className = 'screen-section-title';
        sectionTitle.textContent = 'Available Loan Tiers';
        section.appendChild(sectionTitle);

        const tiers = [
            { name: 'Small',  max: 3000,  rate: '20%' },
            { name: 'Medium', max: 7000,  rate: '40%' },
            { name: 'Large',  max: 10000, rate: '70%' }
        ];

        const tierHeader = document.createElement('div');
        tierHeader.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;color:var(--dim);' +
            'border-bottom:1px solid var(--dim);font-weight:700;';
        tierHeader.innerHTML = '<span style="flex:1">TIER</span>' +
            '<span style="flex:1;text-align:right">MAX AMOUNT</span>' +
            '<span style="flex:1;text-align:right">INTEREST</span>';
        section.appendChild(tierHeader);

        tiers.forEach(tier => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;padding:4px 8px;font-size:11px;' +
                'border-bottom:1px solid rgba(0,102,34,0.1);';

            const nameSpan = document.createElement('span');
            nameSpan.style.cssText = 'flex:1;color:var(--highlight);';
            nameSpan.textContent = tier.name;

            const maxSpan = document.createElement('span');
            maxSpan.style.cssText = 'flex:1;text-align:right;color:var(--warning);';
            maxSpan.textContent = tier.max.toLocaleString() + 'c';

            const rateSpan = document.createElement('span');
            rateSpan.style.cssText = 'flex:1;text-align:right;color:var(--danger);';
            rateSpan.textContent = tier.rate;

            row.appendChild(nameSpan);
            row.appendChild(maxSpan);
            row.appendChild(rateSpan);
            section.appendChild(row);
        });

        container.appendChild(section);
    },

    /**
     * Render the take loan form.
     * @param {HTMLElement} container
     * @param {Array} accounts
     */
    _renderLoanForm(container, accounts) {
        const section = document.createElement('div');
        section.style.cssText = 'padding:8px;margin-top:8px;border-top:1px solid rgba(0,255,65,0.15);';

        const sectionTitle = document.createElement('div');
        sectionTitle.className = 'screen-section-title';
        sectionTitle.textContent = 'Take Loan';
        section.appendChild(sectionTitle);

        if (accounts.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '8px';
            empty.textContent = 'No accounts available for loans.';
            section.appendChild(empty);
            container.appendChild(section);
            return;
        }

        const form = document.createElement('div');
        form.style.cssText = 'padding:8px 0;display:flex;flex-direction:column;gap:10px;';

        // Account select
        const acctLabel = document.createElement('label');
        acctLabel.className = 'text-dim';
        acctLabel.style.cssText = 'font-size:11px;display:block;';
        acctLabel.textContent = 'DEPOSIT TO ACCOUNT:';

        const acctSelect = document.createElement('select');
        acctSelect.className = 'terminal-input';
        accounts.forEach(acct => {
            const opt = document.createElement('option');
            opt.value = acct.id;
            opt.textContent = acct.account_number + ' (loan: ' + (acct.loan || 0).toLocaleString() + 'c)';
            acctSelect.appendChild(opt);
        });

        const acctField = document.createElement('div');
        acctField.appendChild(acctLabel);
        acctField.appendChild(acctSelect);
        form.appendChild(acctField);

        // Amount field
        const amountLabel = document.createElement('label');
        amountLabel.className = 'text-dim';
        amountLabel.style.cssText = 'font-size:11px;display:block;';
        amountLabel.textContent = 'LOAN AMOUNT:';

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

        const loanBtn = document.createElement('button');
        loanBtn.className = 'terminal-btn';
        loanBtn.textContent = 'TAKE LOAN';

        loanBtn.addEventListener('click', () => {
            const bankAccountId = acctSelect.value;
            const amount = parseInt(amountInput.value, 10);

            if (!amount || amount <= 0) {
                errorMsg.textContent = 'Enter a valid loan amount.';
                errorMsg.style.display = 'block';
                amountInput.focus();
                return;
            }

            errorMsg.style.display = 'none';
            loanBtn.disabled = true;
            loanBtn.textContent = 'PROCESSING...';

            GameSocket.screenAction('take_loan', {
                bank_account_id: bankAccountId,
                amount: amount
            });
        });

        btnWrap.appendChild(loanBtn);
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
