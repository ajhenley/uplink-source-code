/**
 * News panel displaying in-game news articles from the Uplink news server.
 * Articles are categorized (plot, crime, business, tech) and loaded via REST API.
 */
const NewsPanel = {
    panelBody: null,
    articles: [],

    /**
     * Category badge color mapping using terminal theme CSS variables.
     */
    categoryColors: {
        plot:     'var(--danger)',
        crime:    'var(--warning)',
        business: 'var(--cyan)',
        tech:     'var(--primary)',
    },

    init() {
        this.panelBody = Panels.create('news', 'NEWS SERVER', 500, 400);
        GameState.on('news_update', (data) => this.onNewsUpdate(data));
        Panels.hide('news');
    },

    /**
     * Toggle the news panel visibility. Loads articles when opening.
     */
    toggle() {
        Panels.toggle('news');
        if (Panels.panels['news'] && Panels.panels['news'].isVisible) {
            this.loadNews();
        }
    },

    /**
     * Load news articles from the backend REST API.
     */
    async loadNews() {
        try {
            const resp = await fetch('/api/session/' + GAME_SESSION_ID + '/news');
            if (resp.ok) {
                const data = await resp.json();
                this.articles = Array.isArray(data.articles) ? data.articles : [];
            }
        } catch (e) { /* ignore network errors */ }
        this.render();
    },

    /**
     * Handle a real-time news_update event from GameState.
     * Prepends the new article and re-renders if the panel is visible.
     * @param {Object} data - The news article object
     */
    onNewsUpdate(data) {
        if (!data) return;
        // Avoid duplicates by checking id
        if (data.id && this.articles.some(a => a.id === data.id)) return;
        this.articles.unshift(data);
        if (Panels.panels['news'] && Panels.panels['news'].isVisible) {
            this.render();
        }
    },

    /**
     * Render all news articles into the panel body.
     */
    render() {
        if (!this.panelBody) return;

        if (this.articles.length === 0) {
            this.panelBody.innerHTML = '<div style="color:var(--dim);padding:20px;text-align:center;">No news articles available</div>';
            return;
        }

        let html = '<div class="news-list" style="max-height:360px;overflow-y:auto;padding:8px;">';

        for (let i = 0; i < this.articles.length; i++) {
            const a = this.articles[i];
            const category = (a.category || 'general').toLowerCase();
            const badgeColor = this.categoryColors[category] || 'var(--dim)';
            const timestamp = a.timestamp || '';

            html += '<div class="news-article" style="border-bottom:1px solid var(--border);padding:10px 4px;'
                + (i === 0 ? '' : '') + '">'
                + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
                + '<span style="'
                    + 'display:inline-block;'
                    + 'padding:1px 6px;'
                    + 'font-size:10px;'
                    + 'font-weight:bold;'
                    + 'text-transform:uppercase;'
                    + 'border:1px solid ' + badgeColor + ';'
                    + 'color:' + badgeColor + ';'
                    + 'border-radius:2px;'
                    + '">' + this.esc(category) + '</span>'
                + '<span style="color:var(--dim);font-size:10px;">' + this.esc(timestamp) + '</span>'
                + '</div>'
                + '<div style="color:var(--cyan);font-weight:bold;margin-bottom:4px;font-size:13px;">'
                + this.esc(a.headline || 'Untitled') + '</div>'
                + '<div style="color:var(--text);font-size:12px;line-height:1.4;">'
                + this.esc(a.body || '').replace(/\n/g, '<br>') + '</div>'
                + '</div>';
        }

        html += '</div>';
        this.panelBody.innerHTML = html;

        // Auto-scroll to the top (newest articles are first)
        const listEl = this.panelBody.querySelector('.news-list');
        if (listEl) {
            listEl.scrollTop = 0;
        }
    },

    /**
     * Escape HTML to prevent XSS.
     * @param {string} str
     * @returns {string}
     */
    esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }
};
