const CheatSystem = {
    _buffer: '',
    _cheats: {
        'allinks': { name: 'All Links', desc: 'Reveal all IP addresses on map' },
        'allsoftware': { name: 'All Software', desc: 'Give all software tools' },
        'allhardware': { name: 'All Hardware', desc: 'Give all hardware upgrades' },
        'lotsofmoney': { name: 'Lots Of Money', desc: 'Add 10,000 credits' },
        'nextrating': { name: 'Next Rating', desc: 'Increase Uplink rating by 1' },
        'maxratings': { name: 'Max Ratings', desc: 'Set Uplink rating to TERMINAL' },
        'canceltrace': { name: 'Cancel Trace', desc: 'End current trace' },
        'showlan': { name: 'Show LAN', desc: 'Reveal all LAN systems' },
    },

    init() {
        document.addEventListener('keydown', (e) => {
            const tag = (e.target.tagName || '').toLowerCase();
            if (tag === 'input' || tag === 'textarea') return;

            this._buffer += e.key.toLowerCase();
            if (this._buffer.length > 20) {
                this._buffer = this._buffer.slice(-20);
            }

            for (const [code, info] of Object.entries(this._cheats)) {
                if (this._buffer.endsWith(code)) {
                    this._execute(code, info);
                    this._buffer = '';
                    break;
                }
            }
        });
    },

    _execute(code, info) {
        if (typeof App !== 'undefined' && App.showNotification) {
            App.showNotification('CHEAT: ' + info.name, 'warning');
        }

        if (typeof GameSocket === 'undefined' || !GameSocket.socket) return;

        GameSocket.socket.emit('cheat', {
            session_id: typeof GAME_SESSION_ID !== 'undefined' ? GAME_SESSION_ID : null,
            cheat_code: code,
        });
    }
};
