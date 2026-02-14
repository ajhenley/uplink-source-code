/**
 * Mission browser panel.
 * Shows available missions from the Internal Services bulletin board.
 */
const MissionPanel = {
    panelBody: null,

    init() {
        this.panelBody = Panels.create('mission', 'INTERNAL SERVICES \u2014 MISSIONS', 500, 400);
        GameState.on('missions_updated', () => this.render());
        Panels.hide('mission');
    },

    /**
     * Toggle the mission panel visibility.
     */
    toggle() {
        Panels.toggle('mission');
        if (Panels.panels['mission'] && Panels.panels['mission'].isVisible) {
            this.render();
        }
    },

    /**
     * Render the list of available missions.
     */
    render() {
        if (!this.panelBody) return;
        const missions = GameState.availableMissions || [];

        if (missions.length === 0) {
            this.panelBody.innerHTML = '<div style="color:#006622;padding:20px;text-align:center;">No missions available</div>';
            return;
        }

        this.panelBody.innerHTML = '<div class="mission-list">'
            + missions.map(m => {
                const stars = '\u2605'.repeat(m.difficulty || 1);
                return '<div class="mission-item" data-id="' + m.id + '">'
                    + '<div class="mission-employer" style="color:#00ffff;">' + this.esc(m.employer_name) + '</div>'
                    + '<div class="mission-desc">' + this.esc(m.description) + '</div>'
                    + '<div class="mission-meta">'
                    + '<span>Payment: ' + (m.payment || 0).toLocaleString() + 'c</span>'
                    + '<span>Difficulty: ' + stars + '</span>'
                    + '</div>'
                    + '<button class="terminal-btn" style="font-size:10px;padding:2px 8px;margin-top:4px;" '
                    + 'onclick="MissionPanel.accept(' + m.id + ')">[ ACCEPT ]</button>'
                    + '</div>';
            }).join('')
            + '</div>';
    },

    /**
     * Accept a mission by ID.
     * @param {number} missionId
     */
    accept(missionId) {
        GameSocket.acceptMission(missionId);
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
