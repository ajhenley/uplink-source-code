/* ============================================================
   UPLINK WEB - Screen: Academic Records Database
   Searchable academic records. Same search pattern as
   criminal records but displays academic information.
   ============================================================ */

const ScreenAcademic = {

    /**
     * Render an academic records screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {Array} data.records - [{name, age, ...}]
     * @param {string} [data.search_query] - Current search query
     * @param {string} [data.error] - Error message
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Academic Records Database';
        container.appendChild(title);

        // Search bar
        const searchBar = document.createElement('div');
        searchBar.style.padding = '8px';
        searchBar.style.display = 'flex';
        searchBar.style.gap = '8px';
        searchBar.style.alignItems = 'center';

        const searchLabel = document.createElement('span');
        searchLabel.className = 'text-dim';
        searchLabel.style.fontSize = '11px';
        searchLabel.textContent = 'SEARCH:';

        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'terminal-input';
        searchInput.placeholder = 'Enter name to search';
        searchInput.autocomplete = 'off';
        searchInput.spellcheck = false;
        searchInput.style.flex = '1';
        if (data.search_query) {
            searchInput.value = data.search_query;
        }

        const searchBtn = document.createElement('button');
        searchBtn.className = 'terminal-btn';
        searchBtn.textContent = 'SEARCH';

        const doSearch = () => {
            const name = searchInput.value.trim();
            if (!name) {
                searchInput.style.borderColor = 'var(--danger)';
                searchInput.focus();
                return;
            }
            searchBtn.disabled = true;
            searchBtn.textContent = 'SEARCHING...';
            GameSocket.screenAction('search', { name: name });
        };

        searchBtn.addEventListener('click', doSearch);
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                doSearch();
            }
        });
        searchInput.addEventListener('input', () => {
            searchInput.style.borderColor = 'var(--primary)';
        });

        searchBar.appendChild(searchLabel);
        searchBar.appendChild(searchInput);
        searchBar.appendChild(searchBtn);
        container.appendChild(searchBar);

        // Error message
        if (data.error) {
            const error = document.createElement('div');
            error.style.padding = '8px';
            error.style.color = 'var(--danger)';
            error.style.fontSize = '12px';
            error.textContent = data.error;
            container.appendChild(error);
        }

        // Records
        const records = Array.isArray(data.records) ? data.records :
            (Array.isArray(data.search_results) ? data.search_results : []);

        if (records.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-dim';
            empty.style.padding = '12px 8px';
            empty.textContent = data.search_query
                ? 'No records found for "' + data.search_query + '".'
                : 'Enter a name to search the database.';
            container.appendChild(empty);
            setTimeout(() => searchInput.focus(), 50);
            return;
        }

        // Table header
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;padding:6px 8px;border-bottom:1px solid var(--primary);' +
            'font-weight:700;font-size:11px;color:var(--dim);';
        header.innerHTML = '<span style="flex:2">NAME</span>' +
            '<span style="flex:1;text-align:center">AGE</span>';
        container.appendChild(header);

        // Scrollable results
        const listWrap = document.createElement('div');
        listWrap.style.maxHeight = '300px';
        listWrap.style.overflowY = 'auto';

        records.forEach(record => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;padding:5px 8px;border-bottom:1px solid rgba(0,255,255,0.1);' +
                'font-size:12px;color:var(--text);';

            const nameSpan = document.createElement('span');
            nameSpan.style.flex = '2';
            nameSpan.textContent = this._esc(record.name || 'Unknown');

            const ageSpan = document.createElement('span');
            ageSpan.style.flex = '1';
            ageSpan.style.textAlign = 'center';
            ageSpan.textContent = record.age != null ? String(record.age) : '---';

            row.appendChild(nameSpan);
            row.appendChild(ageSpan);

            listWrap.appendChild(row);
        });

        container.appendChild(listWrap);

        // Summary
        const summary = document.createElement('div');
        summary.className = 'text-dim';
        summary.style.padding = '8px';
        summary.style.fontSize = '11px';
        summary.style.textAlign = 'right';
        summary.textContent = records.length + ' record(s) found';
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
