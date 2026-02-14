/* ============================================================
   UPLINK WEB - Main Application Controller
   Loaded last. Initializes all subsystems and wires them
   together.
   ============================================================ */

const App = {

    // ================================================================
    // Initialization
    // ================================================================

    init() {
        // GAME_SESSION_ID is expected to be set by the server-rendered
        // template as a global variable before this script loads.
        if (typeof GAME_SESSION_ID === 'undefined' || !GAME_SESSION_ID) {
            console.error('[App] GAME_SESSION_ID not defined. Cannot initialize.');
            return;
        }

        // 1. Initialize socket connection
        GameSocket.init(GAME_SESSION_ID);

        // 2. Fetch initial state via REST API
        this.loadInitialState();

        // 3. Initialize UI components (each module self-registers its
        //    listeners on GameState so it can react to changes).
        if (typeof HUD !== 'undefined')          HUD.init();
        if (typeof WorldMap !== 'undefined')      WorldMap.init();
        if (typeof BounceChain !== 'undefined')   BounceChain.init();
        if (typeof Toolbar !== 'undefined')       Toolbar.init();
        if (typeof TaskBar !== 'undefined')       TaskBar.init();
        if (typeof EmailPanel !== 'undefined')    EmailPanel.init();
        if (typeof MissionPanel !== 'undefined')  MissionPanel.init();
        if (typeof GatewayPanel !== 'undefined')  GatewayPanel.init();
        if (typeof FinancePanel !== 'undefined')  FinancePanel.init();
        if (typeof NewsPanel !== 'undefined')     NewsPanel.init();
        if (typeof IRCPanel !== 'undefined')      IRCPanel.init();
        if (typeof RemoteScreen !== 'undefined')  RemoteScreen.init();
        if (typeof GameOverScreen !== 'undefined') GameOverScreen.init();
        if (typeof ThemeManager !== 'undefined') ThemeManager.init();
        if (typeof CheatSystem !== 'undefined')  CheatSystem.init();
        if (typeof Tutorial !== 'undefined') Tutorial.init();

        // 4. Quick-access button handlers
        this.setupQuickAccess();

        // 5. Keyboard shortcuts
        this.setupKeyboard();

        console.log('[App] Initialized for session', GAME_SESSION_ID);
    },

    // ================================================================
    // Initial state load (REST)
    // ================================================================

    /**
     * Fetch the full session state snapshot from the server and populate
     * the GameState singleton.
     */
    async loadInitialState() {
        try {
            const resp = await fetch('/api/session/' + GAME_SESSION_ID + '/state');
            if (!resp.ok) {
                console.error('[App] Failed to load initial state:', resp.status);
                return;
            }

            const data = await resp.json();

            // Populate state
            if (data.player)     GameState.updatePlayer(data.player);
            if (data.gateway)    GameState.updateGateway(data.gateway);
            if (data.messages)   GameState.setMessages(data.messages);
            if (data.tasks)      GameState.updateTasks(data.tasks);
            if (data.locations)  GameState.setLocations(data.locations);
            if (data.connection) GameState.updateConnection(data.connection);
            if (data.software)   GameState.software = data.software;
            if (data.missions)   GameState.setMissions(data.missions.available, data.missions.active);
            if (typeof data.speed === 'number') GameState.setSpeed(data.speed);
            if (typeof data.ticks === 'number') GameState.updateGameTime(data.ticks);

        } catch (err) {
            console.error('[App] Error loading initial state:', err);
        }
    },

    // ================================================================
    // Quick-access buttons
    // ================================================================

    setupQuickAccess() {
        const bind = (id, handler) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('click', handler);
        };

        bind('btn-email',    () => { if (typeof EmailPanel !== 'undefined')    EmailPanel.toggle();   });
        bind('btn-missions', () => { if (typeof MissionPanel !== 'undefined')  MissionPanel.toggle(); });
        bind('btn-gateway',  () => { if (typeof GatewayPanel !== 'undefined')  GatewayPanel.toggle(); });
        bind('btn-finance',  () => { if (typeof FinancePanel !== 'undefined')  FinancePanel.toggle(); });
        bind('btn-irc',     () => { if (typeof IRCPanel !== 'undefined')      IRCPanel.toggle(); });
        bind('btn-news',    () => { if (typeof NewsPanel !== 'undefined')     NewsPanel.toggle(); });

        // Save button
        bind('save-btn', async () => {
            try {
                const resp = await fetch('/api/session/' + GAME_SESSION_ID + '/save', { method: 'POST' });
                if (resp.ok) {
                    App.showNotification('Game saved.', 'info');
                } else {
                    App.showNotification('Save failed.', 'error');
                }
            } catch (err) {
                App.showNotification('Save failed: ' + err.message, 'error');
            }
        });

        // Speed buttons (data-speed attribute on .speed-btn elements)
        document.querySelectorAll('.speed-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const speed = parseInt(btn.dataset.speed, 10);
                if (!isNaN(speed)) {
                    GameSocket.setSpeed(speed);
                    // Update active state
                    document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                }
            });
        });

        // Connect/disconnect toggle
        const connectBtn = document.getElementById('connect-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                if (GameState.connection.isConnected) {
                    GameSocket.disconnectFrom();
                } else {
                    GameSocket.connectTo();
                }
            });
        }

        // Listen for connection state changes to update the connect button
        GameState.on('connection_updated', (conn) => {
            if (!connectBtn) return;
            if (conn.isConnected) {
                connectBtn.textContent = 'Disconnect';
                connectBtn.classList.add('connected');
            } else {
                connectBtn.textContent = 'Connect';
                connectBtn.classList.remove('connected');
            }
        });
    },

    // ================================================================
    // Keyboard shortcuts
    // ================================================================

    setupKeyboard() {
        document.addEventListener('keydown', (e) => {
            // Don't capture when typing in an input or textarea
            const tag = (e.target.tagName || '').toLowerCase();
            if (tag === 'input' || tag === 'textarea') return;

            switch (e.key) {
                case 'Escape':
                    if (typeof Panels !== 'undefined') {
                        Panels.closeAll();
                    }
                    break;

                case '1':
                    GameSocket.setSpeed(0);
                    break;
                case '2':
                    GameSocket.setSpeed(1);
                    break;
                case '3':
                    GameSocket.setSpeed(3);
                    break;
                case '4':
                    GameSocket.setSpeed(8);
                    break;

                case 'e':
                    if (typeof EmailPanel !== 'undefined') EmailPanel.toggle();
                    break;
                case 'm':
                    if (typeof MissionPanel !== 'undefined') MissionPanel.toggle();
                    break;
                case 'g':
                    if (typeof GatewayPanel !== 'undefined') GatewayPanel.toggle();
                    break;
                case 'f':
                    if (typeof FinancePanel !== 'undefined') FinancePanel.toggle();
                    break;
                case 'n':
                    if (typeof NewsPanel !== 'undefined') NewsPanel.toggle();
                    break;
                case 'i':
                    if (typeof IRCPanel !== 'undefined') IRCPanel.toggle();
                    break;
                case 's':
                    document.getElementById('save-btn')?.click();
                    break;
                case 't':
                    if (typeof ThemeManager !== 'undefined') ThemeManager.toggle();
                    break;
                case 'h':
                    if (typeof Tutorial !== 'undefined') {
                        localStorage.removeItem('uplink-tutorial-done');
                        Tutorial.start();
                    }
                    break;
            }
        });
    },

    // ================================================================
    // Notifications
    // ================================================================

    /**
     * Display a temporary toast notification at the top-right of the screen.
     * @param {string} message - Text to display.
     * @param {string} type    - One of 'info', 'error', 'warning'.
     */
    showNotification(message, type) {
        type = type || 'info';

        const el = document.createElement('div');
        el.className = 'notification notification-' + type;
        el.textContent = message;
        document.body.appendChild(el);

        // Stack multiple notifications vertically
        const existing = document.querySelectorAll('.notification');
        const offset = (existing.length - 1) * 40;
        el.style.top = (50 + offset) + 'px';

        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (el.parentNode) {
                el.remove();
            }
        }, 3000);
    },
};

// ================================================================
// Bootstrap
// ================================================================

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
