/* ============================================================
   UPLINK WEB - Screen: Agent Rankings
   Displays agent rankings sorted by rating. Highlights the
   player's own row in cyan.
   ============================================================ */

const ScreenRanking = {

    /**
     * Render a rankings screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.rankings - [{name, rating, is_player}]
     * @param {string} [data.player_name] - Name of the current player for highlighting
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Agent Rankings';
        container.appendChild(title);

        const rankings = Array.isArray(data.rankings) ? data.rankings : [];

        if (rankings.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No ranking data available.';
            container.appendChild(empty);
            return;
        }

        // Sort by rating descending
        const sorted = rankings.slice().sort((a, b) => (b.rating || 0) - (a.rating || 0));

        // Table header
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;padding:6px 8px;border-bottom:1px solid var(--primary);' +
            'font-weight:700;font-size:11px;color:var(--dim);';
        header.innerHTML = '<span style="flex:0 0 60px">RANK</span>' +
            '<span style="flex:2">AGENT NAME</span>' +
            '<span style="flex:1;text-align:right">RATING</span>';
        container.appendChild(header);

        // Scrollable list
        const listWrap = document.createElement('div');
        listWrap.style.maxHeight = '350px';
        listWrap.style.overflowY = 'auto';

        sorted.forEach((agent, index) => {
            const isPlayer = agent.is_player ||
                (data.player_name && agent.name === data.player_name);

            const row = document.createElement('div');
            row.style.cssText = 'display:flex;padding:5px 8px;border-bottom:1px solid rgba(0,255,255,0.1);' +
                'font-size:12px;';

            if (isPlayer) {
                row.style.color = 'var(--highlight)';
                row.style.backgroundColor = 'rgba(0,255,255,0.05)';
            } else {
                row.style.color = 'var(--text)';
            }

            // Rank
            const rankSpan = document.createElement('span');
            rankSpan.style.flex = '0 0 60px';
            rankSpan.textContent = String(index + 1);

            // Agent name
            const nameSpan = document.createElement('span');
            nameSpan.style.flex = '2';
            nameSpan.textContent = this._esc(agent.name || 'Unknown');

            // Rating
            const ratingSpan = document.createElement('span');
            ratingSpan.style.flex = '1';
            ratingSpan.style.textAlign = 'right';
            ratingSpan.textContent = String(agent.rating || 0);

            row.appendChild(rankSpan);
            row.appendChild(nameSpan);
            row.appendChild(ratingSpan);

            listWrap.appendChild(row);
        });

        container.appendChild(listWrap);

        // Summary
        const summary = document.createElement('div');
        summary.className = 'text-dim';
        summary.style.padding = '8px';
        summary.style.fontSize = '11px';
        summary.style.textAlign = 'right';
        summary.textContent = sorted.length + ' agent(s) ranked';
        container.appendChild(summary);
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
