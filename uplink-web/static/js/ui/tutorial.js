const Tutorial = {
    _step: 0,
    _active: false,
    _overlay: null,

    steps: [
        {
            title: "Welcome to Uplink",
            text: "You are now a registered Uplink Agent — a freelance computer hacker.\n\nThis tutorial will guide you through the basics of your new career.",
            highlight: null,
        },
        {
            title: "The World Map",
            text: "The world map shows all known computer systems as dots.\n\nClick on any dot to add it to your bounce chain — the route your connection will take.",
            highlight: "#world-map",
        },
        {
            title: "Bounce Chain",
            text: "Your bounce chain is shown at the bottom of the screen.\n\nEach node in the chain adds delay before a trace can reach you. More nodes = more safety.",
            highlight: "#bounce-chain",
        },
        {
            title: "Connecting",
            text: "Add the Uplink Test Machine to your bounce chain, then click [ CONNECT ].\n\nThe last node in your chain is the system you'll connect to.",
            highlight: "#connect-btn",
        },
        {
            title: "Remote Screens",
            text: "When connected, you'll see the remote computer's interface.\n\nMost systems require a password. Use the Password Breaker tool from the toolbar to crack it.",
            highlight: "#software-toolbar",
        },
        {
            title: "The Toolbar",
            text: "Your hacking tools appear in the bottom toolbar.\n\nClick a tool to activate it against the connected system. Watch the task bar for progress.",
            highlight: "#task-bar",
        },
        {
            title: "Covering Your Tracks",
            text: "IMPORTANT: Always delete your access logs before disconnecting!\n\nUse the Log Deleter tool on the target's log screen. Getting traced means game over.",
            highlight: null,
        },
        {
            title: "Missions",
            text: "Click 'Missions' to browse available jobs on the Uplink BBS.\n\nComplete missions to earn credits and increase your rating. Higher ratings unlock harder, better-paying jobs.",
            highlight: "#btn-missions",
        },
        {
            title: "Your Gateway",
            text: "Click 'Gateway / Hardware' to view your computer specs.\n\nUpgrade your CPU for faster hacking, your modem for faster connections, and buy new software tools.",
            highlight: "#btn-gateway",
        },
        {
            title: "Tutorial Complete",
            text: "You're ready to begin your career as an Uplink Agent.\n\nRemember:\n• Always use a bounce chain\n• Always delete your logs\n• Don't get traced\n\nGood luck, Agent.",
            highlight: null,
        },
    ],

    init() {
        // Check if tutorial has been completed
        const completed = localStorage.getItem('uplink-tutorial-done');
        if (completed) return;

        // Start tutorial after a short delay
        setTimeout(() => this.start(), 2000);
    },

    start() {
        this._active = true;
        this._step = 0;
        this._showStep();
    },

    _showStep() {
        if (this._step >= this.steps.length) {
            this._finish();
            return;
        }

        this._removeOverlay();

        const step = this.steps[this._step];

        const overlay = document.createElement('div');
        overlay.id = 'tutorial-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.7);z-index:9000;display:flex;align-items:center;justify-content:center;';

        // Highlight target element if specified
        if (step.highlight) {
            const target = document.querySelector(step.highlight);
            if (target) {
                target.style.position = target.style.position || 'relative';
                target.style.zIndex = '9001';
                target.style.boxShadow = '0 0 0 3px var(--primary, #00ff41), 0 0 20px var(--primary, #00ff41)';
                target.classList.add('tutorial-highlight');
            }
        }

        const isLast = this._step >= this.steps.length - 1;
        const isFirst = this._step === 0;

        overlay.innerHTML = `
            <div style="max-width:500px;padding:30px;border:1px solid var(--primary,#00ff41);background:var(--bg,#0a0a0a);box-shadow:0 0 20px rgba(0,255,65,0.2);">
                <div style="color:var(--primary,#00ff41);font-size:16px;font-weight:bold;margin-bottom:12px;">
                    ${this._esc(step.title)}
                </div>
                <div style="color:var(--text,#c0c0c0);line-height:1.6;white-space:pre-line;margin-bottom:20px;">
                    ${this._esc(step.text)}
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:var(--dim,#006622);font-size:12px;">Step ${this._step + 1} / ${this.steps.length}</span>
                    <div>
                        ${!isFirst ? '<button class="terminal-btn" onclick="Tutorial.prev()" style="margin-right:8px;">[ BACK ]</button>' : ''}
                        <button class="terminal-btn" onclick="Tutorial.skip()" style="margin-right:8px;color:var(--dim);">[ SKIP ]</button>
                        <button class="terminal-btn" onclick="Tutorial.next()">[ ${isLast ? 'FINISH' : 'NEXT'} ]</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        this._overlay = overlay;
    },

    next() {
        this._clearHighlight();
        this._step++;
        this._showStep();
    },

    prev() {
        this._clearHighlight();
        if (this._step > 0) this._step--;
        this._showStep();
    },

    skip() {
        this._finish();
    },

    _finish() {
        this._active = false;
        this._clearHighlight();
        this._removeOverlay();
        localStorage.setItem('uplink-tutorial-done', 'true');
        if (typeof App !== 'undefined' && App.showNotification) {
            App.showNotification('Tutorial complete. Press H for help.', 'info');
        }
    },

    _removeOverlay() {
        const existing = document.getElementById('tutorial-overlay');
        if (existing) existing.remove();
    },

    _clearHighlight() {
        document.querySelectorAll('.tutorial-highlight').forEach(el => {
            el.style.zIndex = '';
            el.style.boxShadow = '';
            el.classList.remove('tutorial-highlight');
        });
    },

    _esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
