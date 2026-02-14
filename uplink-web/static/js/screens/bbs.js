/* ============================================================
   UPLINK WEB - Screen Type 4: Bulletin Board System (BBS)
   Displays available missions from the Internal Services
   Machine or corporate bulletin boards.
   ============================================================ */

const ScreenBBS = {

    /**
     * Render a BBS / mission board screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Board title
     * @param {Array} data.missions - Mission list [{id, employer_name, description, payment, difficulty, min_rating}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Bulletin Board System';
        container.appendChild(title);

        const missions = Array.isArray(data.missions) ? data.missions : [];

        if (missions.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No missions currently available. Check back later.';
            container.appendChild(empty);
            return;
        }

        // Mission listing
        const list = document.createElement('div');
        list.style.marginTop = '4px';

        missions.forEach(mission => {
            const item = document.createElement('div');
            item.style.padding = '8px';
            item.style.borderBottom = '1px solid rgba(0, 255, 65, 0.1)';
            item.style.cursor = 'pointer';
            item.style.transition = 'background 0.15s';

            item.addEventListener('mouseenter', () => {
                item.style.background = 'rgba(0, 255, 65, 0.05)';
            });
            item.addEventListener('mouseleave', () => {
                item.style.background = 'transparent';
            });

            // Top row: employer + payment
            const topRow = document.createElement('div');
            topRow.style.display = 'flex';
            topRow.style.justifyContent = 'space-between';
            topRow.style.alignItems = 'center';
            topRow.style.marginBottom = '4px';

            const employer = document.createElement('span');
            employer.style.color = 'var(--highlight)';
            employer.style.fontSize = '12px';
            employer.style.fontWeight = '600';
            employer.textContent = escapeHtml(mission.employer_name || 'Anonymous');

            const payment = document.createElement('span');
            payment.style.color = 'var(--warning)';
            payment.style.fontWeight = '700';
            payment.textContent = (mission.payment || 0).toLocaleString() + 'c';

            topRow.appendChild(employer);
            topRow.appendChild(payment);
            item.appendChild(topRow);

            // Description
            const desc = document.createElement('div');
            desc.style.color = 'var(--primary)';
            desc.style.fontSize = '12px';
            desc.style.marginBottom = '6px';
            desc.textContent = escapeHtml(mission.description || 'No description provided.');
            item.appendChild(desc);

            // Bottom row: difficulty + rating
            const bottomRow = document.createElement('div');
            bottomRow.style.display = 'flex';
            bottomRow.style.justifyContent = 'space-between';
            bottomRow.style.alignItems = 'center';
            bottomRow.style.fontSize = '11px';

            const difficulty = document.createElement('span');
            difficulty.style.color = 'var(--dim)';
            difficulty.textContent = 'Difficulty: ' + this._renderDifficulty(mission.difficulty || 0);

            const rating = document.createElement('span');
            rating.style.color = 'var(--dim)';
            rating.textContent = mission.min_rating
                ? 'Min Rating: ' + escapeHtml(String(mission.min_rating))
                : '';

            bottomRow.appendChild(difficulty);
            bottomRow.appendChild(rating);
            item.appendChild(bottomRow);

            // Click to view details / accept
            item.addEventListener('click', () => {
                this._showMissionDetail(container, data, mission);
            });

            list.appendChild(item);
        });

        container.appendChild(list);
    },

    /**
     * Show detailed view for a single mission with accept option.
     * @param {HTMLElement} container
     * @param {Object} data - Full screen data (for back navigation)
     * @param {Object} mission - The mission object
     */
    _showMissionDetail(container, data, mission) {
        container.innerHTML = '';

        // Back button
        const back = document.createElement('div');
        back.className = 'screen-menu-item';
        back.style.color = 'var(--dim)';
        back.textContent = '< Back to mission board';
        back.addEventListener('click', () => this.render(container, data));
        container.appendChild(back);

        // Mission detail
        const detail = document.createElement('div');
        detail.style.padding = '12px 8px';

        const titleEl = document.createElement('div');
        titleEl.style.color = 'var(--highlight)';
        titleEl.style.fontSize = '14px';
        titleEl.style.fontWeight = '700';
        titleEl.style.marginBottom = '12px';
        titleEl.textContent = 'MISSION BRIEFING';
        detail.appendChild(titleEl);

        const fields = [
            { label: 'Employer', value: mission.employer_name || 'Anonymous', color: 'var(--highlight)' },
            { label: 'Description', value: mission.description || 'No description.', color: 'var(--primary)' },
            { label: 'Payment', value: (mission.payment || 0).toLocaleString() + 'c', color: 'var(--warning)' },
            { label: 'Difficulty', value: this._renderDifficulty(mission.difficulty || 0), color: 'var(--primary)' },
            { label: 'Min Rating', value: mission.min_rating ? String(mission.min_rating) : 'None', color: 'var(--dim)' }
        ];

        fields.forEach(field => {
            const row = document.createElement('div');
            row.style.marginBottom = '8px';

            const label = document.createElement('span');
            label.className = 'text-dim';
            label.textContent = field.label + ': ';

            const val = document.createElement('span');
            val.style.color = field.color;
            val.textContent = field.value;

            row.appendChild(label);
            row.appendChild(val);
            detail.appendChild(row);
        });

        // Accept button
        const btnWrap = document.createElement('div');
        btnWrap.style.textAlign = 'center';
        btnWrap.style.marginTop = '20px';

        const acceptBtn = document.createElement('button');
        acceptBtn.className = 'terminal-btn';
        acceptBtn.textContent = 'ACCEPT MISSION';
        acceptBtn.addEventListener('click', () => {
            GameSocket.acceptMission(mission.id);
            acceptBtn.disabled = true;
            acceptBtn.textContent = 'ACCEPTED';
            acceptBtn.style.borderColor = 'var(--dim)';
            acceptBtn.style.color = 'var(--dim)';
        });

        btnWrap.appendChild(acceptBtn);
        detail.appendChild(btnWrap);

        container.appendChild(detail);
    },

    /**
     * Render difficulty as a star rating string.
     * @param {number} level - Difficulty level (1-5)
     * @returns {string}
     */
    _renderDifficulty(level) {
        const max = 5;
        const filled = Math.min(Math.max(Math.round(level), 0), max);
        return '*'.repeat(filled) + '-'.repeat(max - filled);
    }
};
