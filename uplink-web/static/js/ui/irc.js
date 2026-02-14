/**
 * IRC chat panel simulating in-game IRC channels.
 * Displays NPC chat activity and plot-relevant messages.
 * Channels mirror the original Uplink IRC experience.
 */
const IRCPanel = {
    panelBody: null,
    currentChannel: '#general',
    messages: {},       // channel -> [{nick, text, color, timestamp}]
    nickColors: {},     // nick -> color (cached)
    npcTimer: null,
    isVisible: false,

    // Available channels
    channels: ['#general', '#hacking', '#uplink', '#finance', '#darknet'],

    // NPC nicks per channel
    npcNicks: {
        '#general':  ['neuromancer', 'AcidBurn', 'ZeroCool', 'PhreakOut', 'BitFlip', 'NullPtr'],
        '#hacking':  ['rootkit', 'xpl0it', 'Gh0st', 'shellshock', 'StackSmash', 'L0pht'],
        '#uplink':   ['UplinkAdmin', 'AgentX', 'Spiral', 'DeepThought', 'ReVeL', 'Trace_'],
        '#finance':  ['WallSt_', 'CreditFlow', 'BankRun', 'MarginCall', 'DarkPool', 'ShortSell'],
        '#darknet':  ['Anon42', 'Shadow_', 'VoidWalker', 'BlackICE', 'SilkThread', 'DeadDrop'],
    },

    // NPC message templates per channel
    npcMessages: {
        '#general': [
            'anyone know how to bypass proxy v3?',
            'just got traced lol',
            'new mission on the BBS, 5000c for a file steal',
            'be careful with that academic database, trace is fast',
            'uplink just approved my agent application',
            'anyone else having gateway lag today?',
            'if you can\'t afford a password breaker, don\'t take the mission',
            'my modem is too slow for Arunmor',
            'just upgraded to 150MHz, feels good',
            'remember to delete your logs',
            'i forgot to bounce and got caught...',
            'InterNIC is crawling today',
            'has anyone hacked a LAN before? tips?',
            'what\'s the best first upgrade?',
            'proxy_bypass v5 is worth every credit',
            'social engineering doesn\'t work in this business',
        ],
        '#hacking': [
            'dictionary hack still works on most bank accounts',
            'the trace on Global Criminal Database is brutal',
            'use at least 4 bounces for anything serious',
            'monitor bypass v4 is essential for high-security systems',
            'anyone got a decrypter v4? mine keeps failing',
            'firewall disable takes forever on ARC systems',
            'always copy before you delete, learned that the hard way',
            'proxy v5 + firewall disable v3 = unstoppable combo',
            'log_deleter is the most important tool you own',
            'HUD_ConnectionAnalysis shows you the trace in real time',
            'voice analyser saved my life on that last mission',
            'LAN hacking is a whole different game',
            'IP_Probe everything before you connect',
            'don\'t forget to disconnect before the trace finishes',
            'the password screen on that bank is brute-forceable',
        ],
        '#uplink': [
            'new agents: start with file copy missions, easy money',
            'Uplink Internal Services has the best pay',
            'the rating system is broken, I\'ve been Intermediate forever',
            'Arunmor is hiring agents for something big',
            'ARC-net sounds like trouble',
            'anyone else get a weird email from internal?',
            'Uplink Corporation: Trust is our currency',
            'my rating went up after that bank hack',
            'there\'s a rumor about some kind of bioweapon research',
            'don\'t trust everything the news feed says',
            'someone hacked Uplink Test Machine yesterday, what\'s the point?',
            'check your mission deadlines, I lost a bonus because of it',
        ],
        '#finance': [
            'buy low sell high, that\'s all there is to it',
            'OCP stock tanked after the security breach',
            'transferring between accounts isn\'t hard once you crack the login',
            'anyone know a good bank with low security?',
            'Uplink International Bank has decent interest rates',
            'watch the stock ticker, there are patterns',
            'I made 20,000c on one stock trade last week',
            'don\'t forget to launder your money through multiple accounts',
            'the credit rating system is unforgiving',
            'always keep enough to pay for a gateway replacement',
        ],
        '#darknet': [
            'some things are better left undiscovered',
            'ARC is watching',
            'Revelation is just a fairy tale... right?',
            'who else got that strange encrypted email?',
            'the plot thickens...',
            'don\'t look into Andromeda Research Corporation too deeply',
            'some agents have gone missing lately',
            'there\'s more to this world than hacking bank accounts',
            'faith is a deadly weapon',
            'the internet is not as permanent as you think',
            'I\'ve heard rumors of a virus that destroys entire systems',
            'watch your back out there',
        ],
    },

    // Plot-relevant messages triggered by plot_update events
    plotMessages: {
        act1: [
            { channel: '#uplink',  nick: 'UplinkAdmin', text: 'Attention agents: we have reports of unusual network activity.' },
            { channel: '#darknet', nick: 'Anon42',      text: 'something big is happening at Andromeda Research Corporation.' },
        ],
        act2: [
            { channel: '#hacking', nick: 'xpl0it',      text: 'has anyone else noticed the ARC-net spreading?' },
            { channel: '#darknet', nick: 'Shadow_',      text: 'Revelation is real. I\'ve seen the code.' },
            { channel: '#general', nick: 'PhreakOut',    text: 'whole systems going offline... this is not normal' },
        ],
        act3: [
            { channel: '#uplink',  nick: 'Spiral',       text: 'Arunmor needs agents urgently. This is critical.' },
            { channel: '#darknet', nick: 'VoidWalker',   text: 'Faith or Revelation. Choose wisely.' },
            { channel: '#general', nick: 'neuromancer',  text: 'the internet is dying. I\'m not joking.' },
        ],
        act4: [
            { channel: '#uplink',  nick: 'UplinkAdmin', text: 'CRITICAL ALERT: Internet infrastructure under attack.' },
            { channel: '#darknet', nick: 'BlackICE',    text: 'it\'s too late to stop it now...' },
            { channel: '#hacking', nick: 'Gh0st',       text: 'every system I connect to is corrupted. what is happening??' },
        ],
    },

    // Color palette for nick coloring
    _nickPalette: [
        '#00ff41', '#00ffff', '#ffaa00', '#ff6666', '#66ff66',
        '#6699ff', '#ff66ff', '#ffff66', '#66ffcc', '#ff9966',
        '#cc99ff', '#99ffcc', '#ff6699', '#99ccff', '#ccff66',
    ],

    // ================================================================
    // Initialization
    // ================================================================

    init() {
        this.panelBody = Panels.create('irc', 'IRC CLIENT', 450, 350);
        this._initChannels();
        this._buildUI();
        this.render();

        // Listen for plot advancement
        GameState.on('plot_update', (data) => this._onPlotUpdate(data));

        Panels.hide('irc');
        this.isVisible = false;
    },

    // ================================================================
    // Toggle
    // ================================================================

    toggle() {
        Panels.toggle('irc');
        const entry = Panels.panels['irc'];
        if (entry && entry.isVisible) {
            this.isVisible = true;
            this._startNPCChat();
            this.render();
        } else {
            this.isVisible = false;
            this._stopNPCChat();
        }
    },

    // ================================================================
    // Channel Management
    // ================================================================

    _initChannels() {
        for (let i = 0; i < this.channels.length; i++) {
            this.messages[this.channels[i]] = [];
        }

        // Seed each channel with a join message
        for (let i = 0; i < this.channels.length; i++) {
            var ch = this.channels[i];
            this.messages[ch].push({
                nick: '*',
                text: 'Welcome to ' + ch + '. Type /help for commands.',
                color: 'var(--dim)',
                timestamp: this._timestamp(),
                isSystem: true,
            });
        }
    },

    switchChannel(channel) {
        if (this.channels.indexOf(channel) === -1) return;
        this.currentChannel = channel;
        this.render();
        this._scrollToBottom();
    },

    // ================================================================
    // UI Building
    // ================================================================

    _buildUI() {
        if (!this.panelBody) return;

        this.panelBody.style.padding = '0';
        this.panelBody.style.display = 'flex';
        this.panelBody.style.flexDirection = 'row';
        this.panelBody.style.overflow = 'hidden';

        // Channel sidebar
        var sidebar = document.createElement('div');
        sidebar.id = 'irc-sidebar';
        sidebar.style.cssText = 'width:110px;min-width:110px;border-right:1px solid var(--border);'
            + 'overflow-y:auto;background:rgba(0,0,0,0.3);flex-shrink:0;';

        // Sidebar header
        var sideHead = document.createElement('div');
        sideHead.style.cssText = 'padding:6px 8px;font-size:10px;color:var(--dim);'
            + 'text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border);';
        sideHead.textContent = 'Channels';
        sidebar.appendChild(sideHead);

        // Channel buttons
        for (var i = 0; i < this.channels.length; i++) {
            var ch = this.channels[i];
            var btn = document.createElement('div');
            btn.className = 'irc-channel-btn';
            btn.dataset.channel = ch;
            btn.textContent = ch;
            btn.style.cssText = 'padding:5px 8px;font-size:11px;cursor:pointer;'
                + 'color:var(--dim);transition:background 0.15s,color 0.15s;'
                + 'border-bottom:1px solid rgba(0,102,34,0.15);';
            btn.addEventListener('click', this._onChannelClick.bind(this));
            sidebar.appendChild(btn);
        }

        // Main content area (messages + input)
        var mainArea = document.createElement('div');
        mainArea.style.cssText = 'flex:1;display:flex;flex-direction:column;min-width:0;';

        // Channel title bar
        var titleBar = document.createElement('div');
        titleBar.id = 'irc-title-bar';
        titleBar.style.cssText = 'padding:5px 10px;font-size:11px;color:var(--cyan);'
            + 'border-bottom:1px solid var(--border);background:rgba(0,255,255,0.03);flex-shrink:0;';
        titleBar.textContent = this.currentChannel;
        mainArea.appendChild(titleBar);

        // Message log
        var log = document.createElement('div');
        log.id = 'irc-log';
        log.style.cssText = 'flex:1;overflow-y:auto;padding:6px 8px;font-size:11px;'
            + 'line-height:1.5;background:transparent;';
        mainArea.appendChild(log);

        // Input area
        var inputRow = document.createElement('div');
        inputRow.style.cssText = 'display:flex;flex-direction:row;border-top:1px solid var(--border);'
            + 'flex-shrink:0;';

        var prompt = document.createElement('span');
        prompt.style.cssText = 'padding:6px 4px 6px 8px;color:var(--dim);font-size:12px;'
            + 'line-height:28px;flex-shrink:0;';
        prompt.textContent = '>';

        var input = document.createElement('input');
        input.id = 'irc-input';
        input.type = 'text';
        input.placeholder = 'Type a message...';
        input.autocomplete = 'off';
        input.style.cssText = 'flex:1;background:var(--input-bg);border:none;color:var(--primary);'
            + 'font-family:inherit;font-size:12px;padding:6px 8px;outline:none;';
        input.addEventListener('keydown', this._onInputKeydown.bind(this));

        inputRow.appendChild(prompt);
        inputRow.appendChild(input);
        mainArea.appendChild(inputRow);

        this.panelBody.appendChild(sidebar);
        this.panelBody.appendChild(mainArea);
    },

    // ================================================================
    // Rendering
    // ================================================================

    render() {
        if (!this.panelBody) return;

        // Update channel button active states
        var buttons = this.panelBody.querySelectorAll('.irc-channel-btn');
        for (var i = 0; i < buttons.length; i++) {
            var btn = buttons[i];
            if (btn.dataset.channel === this.currentChannel) {
                btn.style.color = 'var(--primary)';
                btn.style.background = 'rgba(0,255,65,0.08)';
            } else {
                btn.style.color = 'var(--dim)';
                btn.style.background = 'transparent';
            }
        }

        // Update title bar
        var titleBar = document.getElementById('irc-title-bar');
        if (titleBar) {
            var chanMsgs = this.messages[this.currentChannel] || [];
            titleBar.textContent = this.currentChannel + '  (' + chanMsgs.length + ' messages)';
        }

        // Render messages
        var log = document.getElementById('irc-log');
        if (!log) return;

        var msgs = this.messages[this.currentChannel] || [];
        var html = '';

        for (var i = 0; i < msgs.length; i++) {
            var m = msgs[i];
            if (m.isSystem) {
                html += '<div style="color:var(--dim);font-style:italic;">'
                    + '<span style="color:var(--dim);margin-right:6px;">' + this.esc(m.timestamp) + '</span>'
                    + this.esc(m.text)
                    + '</div>';
            } else {
                var nickColor = m.color || this._getNickColor(m.nick);
                html += '<div>'
                    + '<span style="color:var(--dim);margin-right:6px;">' + this.esc(m.timestamp) + '</span>'
                    + '<span style="color:' + nickColor + ';font-weight:bold;">[' + this.esc(m.nick) + ']</span> '
                    + '<span style="color:var(--text);">' + this.esc(m.text) + '</span>'
                    + '</div>';
            }
        }

        log.innerHTML = html;
        this._scrollToBottom();
    },

    _scrollToBottom() {
        var log = document.getElementById('irc-log');
        if (log) {
            log.scrollTop = log.scrollHeight;
        }
    },

    // ================================================================
    // Event Handlers
    // ================================================================

    _onChannelClick(e) {
        var channel = e.currentTarget.dataset.channel;
        if (channel) {
            this.switchChannel(channel);
        }
    },

    _onInputKeydown(e) {
        if (e.key !== 'Enter') return;

        var input = document.getElementById('irc-input');
        if (!input) return;

        var text = input.value.trim();
        if (!text) return;

        input.value = '';

        // Handle client-side commands
        if (text.charAt(0) === '/') {
            this._handleCommand(text);
            return;
        }

        // Add player message
        var playerNick = (GameState.player && GameState.player.handle) ? GameState.player.handle : 'Agent';
        this._addMessage(this.currentChannel, playerNick, text, 'var(--primary)');
    },

    _handleCommand(text) {
        var parts = text.split(' ');
        var cmd = parts[0].toLowerCase();

        switch (cmd) {
            case '/help':
                this._addSystemMessage(this.currentChannel,
                    'Commands: /help, /join <channel>, /nick, /clear, /list');
                break;

            case '/join':
                var target = parts[1];
                if (target && this.channels.indexOf(target) !== -1) {
                    this.switchChannel(target);
                    this._addSystemMessage(target, 'Now talking in ' + target);
                } else {
                    this._addSystemMessage(this.currentChannel,
                        'Unknown channel. Available: ' + this.channels.join(', '));
                }
                break;

            case '/nick':
                this._addSystemMessage(this.currentChannel,
                    'Your agent handle is fixed by Uplink Corporation.');
                break;

            case '/clear':
                this.messages[this.currentChannel] = [];
                this._addSystemMessage(this.currentChannel, 'Channel log cleared.');
                this.render();
                break;

            case '/list':
                this._addSystemMessage(this.currentChannel,
                    'Available channels: ' + this.channels.join(', '));
                break;

            default:
                this._addSystemMessage(this.currentChannel,
                    'Unknown command: ' + this.esc(cmd) + '. Type /help for a list.');
                break;
        }
    },

    // ================================================================
    // NPC Chat Simulation
    // ================================================================

    _startNPCChat() {
        if (this.npcTimer) return;

        // Add an NPC message every 4-12 seconds
        var self = this;
        var tick = function () {
            self._generateNPCMessage();
            var delay = 4000 + Math.floor(Math.random() * 8000);
            self.npcTimer = setTimeout(tick, delay);
        };
        var initialDelay = 2000 + Math.floor(Math.random() * 3000);
        this.npcTimer = setTimeout(tick, initialDelay);
    },

    _stopNPCChat() {
        if (this.npcTimer) {
            clearTimeout(this.npcTimer);
            this.npcTimer = null;
        }
    },

    _generateNPCMessage() {
        // Pick a random channel (weighted toward current channel)
        var channel;
        if (Math.random() < 0.6) {
            channel = this.currentChannel;
        } else {
            channel = this.channels[Math.floor(Math.random() * this.channels.length)];
        }

        // Pick a random NPC nick for that channel
        var nicks = this.npcNicks[channel] || this.npcNicks['#general'];
        var nick = nicks[Math.floor(Math.random() * nicks.length)];

        // Pick a random message template for that channel
        var templates = this.npcMessages[channel] || this.npcMessages['#general'];
        var text = templates[Math.floor(Math.random() * templates.length)];

        this._addMessage(channel, nick, text);

        // Only re-render if the message is in the currently viewed channel
        if (channel === this.currentChannel) {
            this.render();
        }
    },

    // ================================================================
    // Plot Event Handler
    // ================================================================

    _onPlotUpdate(data) {
        if (!data || !data.act) return;

        var actKey = 'act' + data.act;
        var plotMsgs = this.plotMessages[actKey];
        if (!plotMsgs) return;

        // Add all plot messages for this act
        for (var i = 0; i < plotMsgs.length; i++) {
            var pm = plotMsgs[i];
            this._addMessage(pm.channel, pm.nick, pm.text);
        }

        // If the panel is visible and any plot message is in the current channel, re-render
        if (this.isVisible) {
            this.render();
        }
    },

    // ================================================================
    // Message Helpers
    // ================================================================

    _addMessage(channel, nick, text, color) {
        if (!this.messages[channel]) {
            this.messages[channel] = [];
        }

        this.messages[channel].push({
            nick: nick,
            text: text,
            color: color || this._getNickColor(nick),
            timestamp: this._timestamp(),
            isSystem: false,
        });

        // Cap message history per channel at 200 messages
        if (this.messages[channel].length > 200) {
            this.messages[channel] = this.messages[channel].slice(-200);
        }
    },

    _addSystemMessage(channel, text) {
        if (!this.messages[channel]) {
            this.messages[channel] = [];
        }

        this.messages[channel].push({
            nick: '*',
            text: text,
            color: 'var(--dim)',
            timestamp: this._timestamp(),
            isSystem: true,
        });

        this.render();
    },

    // ================================================================
    // Utilities
    // ================================================================

    /**
     * Get a consistent color for a given nick.
     * @param {string} nick
     * @returns {string} CSS color value
     */
    _getNickColor(nick) {
        if (this.nickColors[nick]) {
            return this.nickColors[nick];
        }

        // Simple hash to pick a color deterministically
        var hash = 0;
        for (var i = 0; i < nick.length; i++) {
            hash = ((hash << 5) - hash) + nick.charCodeAt(i);
            hash = hash & hash; // Convert to 32bit integer
        }
        var idx = Math.abs(hash) % this._nickPalette.length;
        this.nickColors[nick] = this._nickPalette[idx];
        return this.nickColors[nick];
    },

    /**
     * Generate a timestamp string from the current game time.
     * @returns {string}
     */
    _timestamp() {
        if (GameState.gameTime && GameState.gameTime.dateString) {
            // Extract just the time portion (HH:MM:SS)
            var parts = GameState.gameTime.dateString.split(' ');
            if (parts.length >= 2) {
                return parts[1];
            }
        }
        // Fallback: use real clock
        var now = new Date();
        var h = String(now.getHours()).padStart(2, '0');
        var m = String(now.getMinutes()).padStart(2, '0');
        var s = String(now.getSeconds()).padStart(2, '0');
        return h + ':' + m + ':' + s;
    },

    /**
     * Escape HTML to prevent XSS.
     * @param {string} str
     * @returns {string}
     */
    esc(str) {
        var d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },
};
