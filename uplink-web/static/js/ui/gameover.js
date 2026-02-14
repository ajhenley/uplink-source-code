const GameOverScreen = {
    _visible: false,

    init() {
        GameState.on('game_over', (data) => this.show(data));
    },

    show(data) {
        if (this._visible) return;
        this._visible = true;

        const reason = data.reason || 'unknown';
        const titles = {
            'traced': 'TRACED AND IDENTIFIED',
            'arrested': 'ARRESTED BY FEDERAL AGENTS',
            'shot_by_feds': 'SHOT BY FEDERAL AGENTS',
            'gateway_seized': 'GATEWAY SEIZED',
            'caught_money_transfer': 'CAUGHT: UNAUTHORIZED MONEY TRANSFER',
            'revelation_uncontrolled': 'THE INTERNET HAS BEEN DESTROYED',
            'disavowed': 'DISAVOWED BY UPLINK CORPORATION',
        };

        const descriptions = {
            'traced': 'Your connection was traced back to your gateway. Federal agents have identified you as the perpetrator.',
            'arrested': 'Federal agents have arrived at your physical location. You have been placed under arrest.',
            'shot_by_feds': 'You failed to comply with the arrest warrant. An armed tactical team was dispatched. You did not survive.',
            'gateway_seized': 'Federal agents have seized your gateway computer and all evidence stored on it.',
            'caught_money_transfer': 'You failed to cover your tracks within the 2-minute window. The bank traced the unauthorized transfer back to you.',
            'revelation_uncontrolled': 'The Revelation virus has spread beyond control. The entire Internet infrastructure has been destroyed.',
            'disavowed': 'Uplink Corporation has terminated your agent contract due to excessive criminal activity.',
        };

        const overlay = document.createElement('div');
        overlay.id = 'game-over-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.92);z-index:10000;display:flex;align-items:center;justify-content:center;';

        const player = GameState.player || {};

        overlay.innerHTML = `
            <div style="text-align:center;max-width:600px;padding:40px;border:1px solid var(--danger);background:var(--bg,#0a0a0a);">
                <div style="color:var(--danger);font-size:24px;font-weight:bold;margin-bottom:20px;text-shadow:0 0 10px rgba(255,51,51,0.5);">
                    GAME OVER
                </div>
                <div style="color:var(--warning,#ffaa00);font-size:18px;margin-bottom:16px;">
                    ${this._esc(titles[reason] || reason.toUpperCase())}
                </div>
                <div style="color:var(--text,#c0c0c0);margin-bottom:30px;line-height:1.6;">
                    ${this._esc(descriptions[reason] || 'Your career as an Uplink agent has come to an end.')}
                </div>
                <div style="border-top:1px solid var(--border,rgba(0,255,65,0.3));padding-top:20px;margin-top:20px;">
                    <div style="color:var(--dim,#006622);font-size:14px;margin-bottom:12px;">AGENT OBITUARY</div>
                    <table style="width:100%;color:var(--text,#c0c0c0);font-size:13px;text-align:left;">
                        <tr><td style="padding:4px 8px;">Agent Handle:</td><td style="padding:4px 8px;color:var(--primary,#00ff41);">${this._esc(player.handle || '---')}</td></tr>
                        <tr><td style="padding:4px 8px;">Final Balance:</td><td style="padding:4px 8px;color:var(--highlight,#00ffff);">${(player.balance || 0).toLocaleString()}c</td></tr>
                        <tr><td style="padding:4px 8px;">Uplink Rating:</td><td style="padding:4px 8px;">${player.uplink_rating || 0}</td></tr>
                        <tr><td style="padding:4px 8px;">Neuromancer Rating:</td><td style="padding:4px 8px;">${player.neuromancer_rating || 0}</td></tr>
                        <tr><td style="padding:4px 8px;">Cause of Death:</td><td style="padding:4px 8px;color:var(--danger);">${this._esc(titles[reason] || reason)}</td></tr>
                    </table>
                </div>
                <div style="margin-top:30px;">
                    <button class="terminal-btn" onclick="window.location.href='/game/sessions'" style="margin-right:10px;">
                        [ RETURN TO SESSIONS ]
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
    },

    _esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
