/**
 * Top HUD bar showing player info, game time, balance, and speed controls.
 */
const HUD = {
    init() {
        GameState.on('player_updated', () => this.updatePlayer());
        GameState.on('time_updated', () => this.updateTime());
        GameState.on('speed_updated', () => this.updateSpeed());
        GameState.on('trace_updated', () => this.updateTrace());

        this.updatePlayer();
        this.updateTime();
        this.updateSpeed();
        this.updateTrace();
    },

    /**
     * Update player handle, rating, and balance display.
     */
    updatePlayer() {
        const p = GameState.player;
        if (!p) return;

        const handleEl = document.getElementById('agent-handle');
        const ratingEl = document.getElementById('uplink-rating');
        const balanceEl = document.getElementById('balance');

        if (handleEl) handleEl.textContent = 'AGENT: ' + (p.handle || '---');
        if (ratingEl) ratingEl.textContent = p.uplink_rating || 'Registered';
        if (balanceEl) balanceEl.textContent = (p.balance || 0).toLocaleString() + ' c';
    },

    /**
     * Update the game time display.
     */
    updateTime() {
        const timeEl = document.getElementById('game-datetime');
        if (timeEl && GameState.gameTime) {
            timeEl.textContent = GameState.gameTime.dateString || '';
        }
    },

    /**
     * Highlight the active speed button.
     */
    updateSpeed() {
        document.querySelectorAll('.speed-btn').forEach(btn => {
            const btnSpeed = parseInt(btn.dataset.speed);
            btn.classList.toggle('active', btnSpeed === GameState.speed);
        });
    },

    /**
     * Update the trace progress bar.
     */
    updateTrace() {
        const bar = document.getElementById('trace-bar');
        const fill = document.getElementById('trace-fill');
        if (!bar || !fill) return;

        const pctEl = document.getElementById('trace-pct');
        if (GameState.connection.traceActive) {
            bar.classList.remove('hidden');
            bar.classList.add('active');
            const pct = Math.min(100, Math.round(GameState.connection.traceProgress * 100));
            fill.style.width = pct + '%';
            if (pctEl) pctEl.textContent = pct + '%';
        } else {
            bar.classList.add('hidden');
            bar.classList.remove('active');
            fill.style.width = '0%';
            if (pctEl) pctEl.textContent = '0%';
        }
    }
};
