/* ============================================================
   UPLINK WEB - Screen: News
   News articles on a remote news server. Displays articles
   with headline, body, category, and timestamp.
   ============================================================ */

const ScreenNews = {

    /** Category color map */
    _categoryColors: {
        plot:     'var(--danger)',
        crime:    'var(--warning)',
        business: 'var(--highlight)',
        tech:     '#00ff88',
        default:  'var(--dim)'
    },

    /**
     * Render a news screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.articles - [{headline, body, category, timestamp}]
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'News Server';
        container.appendChild(title);

        const articles = Array.isArray(data.articles) ? data.articles : [];

        if (articles.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = 'No news articles available.';
            container.appendChild(empty);
            return;
        }

        // Scrollable article list
        const listWrap = document.createElement('div');
        listWrap.style.maxHeight = '400px';
        listWrap.style.overflowY = 'auto';
        listWrap.style.marginTop = '8px';

        articles.forEach((article, index) => {
            const card = document.createElement('div');
            card.style.padding = '10px 8px';
            card.style.borderBottom = '1px solid var(--dim)';

            // Header row: category badge + timestamp
            const headerRow = document.createElement('div');
            headerRow.style.display = 'flex';
            headerRow.style.justifyContent = 'space-between';
            headerRow.style.alignItems = 'center';
            headerRow.style.marginBottom = '4px';

            // Category badge
            const catKey = (article.category || 'default').toLowerCase();
            const catColor = this._categoryColors[catKey] || this._categoryColors['default'];

            const badge = document.createElement('span');
            badge.style.cssText = 'font-size:10px;padding:1px 6px;border:1px solid ' + catColor +
                ';color:' + catColor + ';text-transform:uppercase;letter-spacing:1px;';
            badge.textContent = this._esc(article.category || 'general');

            // Timestamp
            const timestamp = document.createElement('span');
            timestamp.className = 'text-dim';
            timestamp.style.fontSize = '10px';
            timestamp.textContent = this._esc(article.timestamp || '');

            headerRow.appendChild(badge);
            headerRow.appendChild(timestamp);
            card.appendChild(headerRow);

            // Headline
            const headline = document.createElement('div');
            headline.style.color = 'var(--primary)';
            headline.style.fontWeight = '700';
            headline.style.marginBottom = '4px';
            headline.textContent = this._esc(article.headline || 'Untitled');
            card.appendChild(headline);

            // Body
            if (article.body) {
                const body = document.createElement('div');
                body.style.color = 'var(--text)';
                body.style.fontSize = '12px';
                body.style.lineHeight = '1.5';
                body.textContent = this._esc(article.body);
                card.appendChild(body);
            }

            listWrap.appendChild(card);
        });

        container.appendChild(listWrap);

        // Article count
        const summary = document.createElement('div');
        summary.className = 'text-dim';
        summary.style.padding = '8px';
        summary.style.fontSize = '11px';
        summary.style.textAlign = 'right';
        summary.textContent = articles.length + ' article(s)';
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
