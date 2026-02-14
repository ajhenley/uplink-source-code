/* ============================================================
   UPLINK WEB - Flask-SocketIO Client Wrapper
   Manages the WebSocket connection, automatic reconnection,
   heartbeat, and routes all server messages into GameState.
   ============================================================ */

const GameSocket = {

    /** @type {SocketIO.Socket|null} */
    socket: null,

    /** @type {string|null} */
    sessionId: null,

    /** @type {boolean} */
    connected: false,

    /** @type {number|null} */
    _heartbeatInterval: null,

    /** @type {number} */
    _lastHeartbeat: 0,

    // ================================================================
    // Initialization
    // ================================================================

    /**
     * Initialize the socket connection and bind all event handlers.
     * @param {string} sessionId - The current game session identifier.
     */
    init(sessionId) {
        this.sessionId = sessionId;

        // Connect to the same origin that served the page.
        // Flask-SocketIO defaults to the /socket.io path.
        this.socket = io(window.location.origin, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: Infinity,
        });

        this._setupHandlers();
        this._startHeartbeat();
    },

    // ================================================================
    // Server -> Client event handlers
    // ================================================================

    _setupHandlers() {
        const s = this.socket;

        // -- Connection lifecycle --

        s.on('connect', () => {
            console.log('[Socket] Connected');
            this.connected = true;

            // Join the session room so the server knows who we are.
            s.emit('join', {
                session_id: this.sessionId,
                user_id: typeof USER_ID !== 'undefined' ? USER_ID : null,
            });
        });

        s.on('disconnect', (reason) => {
            console.warn('[Socket] Disconnected:', reason);
            this.connected = false;
        });

        s.on('connect_error', (err) => {
            console.error('[Socket] Connection error:', err.message);
        });

        // -- Heartbeat --

        s.on('heartbeat_ack', () => {
            this._lastHeartbeat = Date.now();
        });

        // -- Bounce chain --

        s.on('bounce_chain_updated', (data) => {
            GameState.setBounceChain(data.bounce_chain || data.nodes || []);
        });

        // -- Connection to remote computer --

        s.on('connected', (data) => {
            GameState.updateConnection({
                isConnected: true,
                targetIp: data.target_ip,
            });
            if (data.screen) {
                GameState.setScreen(data.screen);
            }
        });

        s.on('disconnected', () => {
            GameState.updateConnection({
                isConnected: false,
                targetIp: null,
            });
            GameState.setScreen(null);
        });

        // -- Remote screen --

        s.on('screen_update', (data) => {
            GameState.setScreen(data.screen);
        });

        // -- Tasks --

        s.on('task_update', (data) => {
            if (Array.isArray(data.tasks)) {
                GameState.updateTasks(data.tasks);
            }
        });

        s.on('task_complete', (data) => {
            GameState.removeTask(data.task_id);
        });

        // -- Trace --

        s.on('trace_update', (data) => {
            GameState.setTrace(data.progress, data.active);
        });

        s.on('trace_complete', (data) => {
            // Trace reached 100% -- the player has been caught.
            console.warn('[Socket] Trace complete -- game over scenario');
            GameState.setTrace(100, false);

            // The server will also send a 'game_over' event, but we can
            // begin visual feedback immediately.
            if (typeof App !== 'undefined' && App.showNotification) {
                App.showNotification('Trace complete! You have been detected.', 'error');
            }
        });

        // -- Player updates --

        s.on('balance_changed', (data) => {
            GameState.updatePlayer({ balance: data.balance });
        });

        s.on('rating_changed', (data) => {
            GameState.updatePlayer({
                uplink_rating: data.uplink_rating,
                neuromancer_rating: data.neuromancer_rating,
            });
        });

        // -- Messages --

        s.on('message_received', (data) => {
            GameState.addMessage(data.message);
        });

        // -- Speed --

        s.on('speed_changed', (data) => {
            GameState.setSpeed(data.speed);
        });

        // -- Game over --

        s.on('game_over', (data) => {
            console.warn('[Socket] Game over:', data.reason);
            if (typeof App !== 'undefined' && App.showNotification) {
                App.showNotification('GAME OVER: ' + (data.reason || 'Unknown'), 'error');
            }
            // Emit a state event so the UI layer can react (show overlay, etc.)
            GameState.emit('game_over', data);
        });

        // -- Game time --

        s.on('game_time', (data) => {
            GameState.updateGameTime(data.ticks);
        });

        // -- Gateway updates (hardware/software purchases) --

        s.on('gateway_updated', (data) => {
            GameState.updateGateway(data);
        });

        s.on('software_purchased', (data) => {
            GameState.emit('gateway_updated', data);
        });

        s.on('hardware_purchased', (data) => {
            GameState.emit('gateway_updated', data);
        });

        // -- Stock updates --

        s.on('stock_update', (data) => {
            GameState.emit('stock_update', data);
        });

        // -- LAN updates --

        s.on('lan_update', (data) => {
            GameState.emit('lan_update', data);
        });

        // -- Plot updates --

        s.on('plot_update', (data) => {
            GameState.emit('plot_update', data);
        });

        // -- News updates --

        s.on('news_update', (data) => {
            GameState.emit('news_update', data);
        });

        // -- Message read acknowledgment --

        s.on('message_read', (data) => {
            const msg = GameState.messages.find(m => m.id === data.message_id);
            if (msg) msg.is_read = true;
            GameState.unreadCount = data.unread_count;
            GameState.emit('messages_updated', {
                messages: GameState.messages,
                unreadCount: GameState.unreadCount,
            });
        });

        // -- Mission events --

        s.on('mission_accepted', (data) => {
            GameState.emit('missions_updated', data);
        });

        s.on('mission_completed', (data) => {
            GameState.emit('missions_updated', data);
        });

        // -- Joined (initial state from WS) --

        s.on('joined', (data) => {
            console.log('[Socket] Joined session', data.session_id);
            if (data.player) GameState.updatePlayer(data.player);
            if (data.bounce_chain) GameState.setBounceChain(data.bounce_chain);
            if (data.connection) GameState.updateConnection(data.connection);
            if (typeof data.game_time_ticks === 'number') {
                GameState.updateGameTime(data.game_time_ticks);
            }
        });

        // -- Generic error --

        s.on('error', (data) => {
            const msg = (typeof data === 'string') ? data : (data.message || 'Unknown error');
            console.error('[Socket] Server error:', msg);
            if (typeof App !== 'undefined' && App.showNotification) {
                App.showNotification(msg, 'error');
            }
        });
    },

    // ================================================================
    // Client -> Server emit methods
    // ================================================================

    /**
     * Add an IP to the bounce chain.
     * @param {string} ip
     */
    bounceAdd(ip) {
        this.socket.emit('bounce_add', { session_id: this.sessionId, ip: ip });
    },

    /**
     * Remove a node from the bounce chain by position index.
     * @param {number} position
     */
    bounceRemove(position) {
        this.socket.emit('bounce_remove', { session_id: this.sessionId, position: position });
    },

    /**
     * Initiate connection through the current bounce chain.
     */
    connectTo() {
        this.socket.emit('connect_to', { session_id: this.sessionId });
    },

    /**
     * Disconnect from the currently connected computer.
     */
    disconnectFrom() {
        this.socket.emit('disconnect_from', { session_id: this.sessionId });
    },

    /**
     * Perform a screen action on the remote computer.
     * @param {string} action  - action identifier (e.g., 'view_file', 'delete_log')
     * @param {Object} data    - additional payload for the action
     */
    screenAction(action, data) {
        this.socket.emit('screen_action', Object.assign(
            { session_id: this.sessionId, action: action },
            data || {}
        ));
    },

    /**
     * Run a hacking tool against a target.
     * @param {string} toolName
     * @param {number} toolVersion
     * @param {string} targetIp
     * @param {Object} targetData  - tool-specific payload
     */
    runTool(toolName, toolVersion, targetIp, targetData) {
        this.socket.emit('run_tool', {
            session_id: this.sessionId,
            tool_name: toolName,
            tool_version: toolVersion,
            target_ip: targetIp,
            target_data: targetData || {},
        });
    },

    /**
     * Cancel a running task.
     * @param {string|number} taskId
     */
    stopTool(taskId) {
        this.socket.emit('stop_tool', { session_id: this.sessionId, task_id: taskId });
    },

    /**
     * Set the game speed multiplier.
     * @param {number} speed  0=paused, 1=normal, 3=fast, 8=megafast
     */
    setSpeed(speed) {
        this.socket.emit('set_speed', { session_id: this.sessionId, speed: speed });
    },

    /**
     * Accept a mission from the BBS.
     * @param {string|number} missionId
     */
    acceptMission(missionId) {
        this.socket.emit('accept_mission', { session_id: this.sessionId, mission_id: missionId });
    },

    /**
     * Mark a mission as completed (submit for review).
     * @param {string|number} missionId
     */
    completeMission(missionId) {
        this.socket.emit('complete_mission', { session_id: this.sessionId, mission_id: missionId });
    },

    /**
     * Buy stock shares.
     */
    buyStock(companyName, shares) {
        this.socket.emit('buy_stock', { session_id: this.sessionId, company_name: companyName, shares: shares || 1 });
    },

    /**
     * Sell stock shares.
     */
    sellStock(companyName, shares) {
        this.socket.emit('sell_stock', { session_id: this.sessionId, company_name: companyName, shares: shares || 1 });
    },

    /**
     * Take out a loan.
     */
    takeLoan(amount) {
        this.socket.emit('take_loan', { session_id: this.sessionId, amount: amount });
    },

    /**
     * Repay a loan.
     */
    repayLoan(loanId, amount) {
        this.socket.emit('repay_loan', { session_id: this.sessionId, loan_id: loanId, amount: amount });
    },

    /**
     * Perform a LAN hacking action.
     */
    lanAction(action, data) {
        this.socket.emit('lan_action', { session_id: this.sessionId, action: action, data: data || {} });
    },

    /**
     * Choose a side in the plot (arunmor or arc).
     */
    chooseSide(side) {
        this.socket.emit('choose_side', { session_id: this.sessionId, side: side });
    },

    /**
     * Mark a message as read.
     */
    markRead(messageId) {
        this.socket.emit('mark_read', { session_id: this.sessionId, message_id: messageId });
    },

    // ================================================================
    // Heartbeat
    // ================================================================

    /**
     * Start a periodic heartbeat so the server knows we are still alive.
     * Interval: 30 seconds.
     */
    _startHeartbeat() {
        if (this._heartbeatInterval) {
            clearInterval(this._heartbeatInterval);
        }

        this._heartbeatInterval = setInterval(() => {
            if (this.connected && this.socket) {
                this.socket.emit('heartbeat', { session_id: this.sessionId });
            }
        }, 30000);
    },

    // ================================================================
    // Cleanup
    // ================================================================

    /**
     * Disconnect and clean up resources.
     */
    destroy() {
        if (this._heartbeatInterval) {
            clearInterval(this._heartbeatInterval);
            this._heartbeatInterval = null;
        }
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.connected = false;
        this.sessionId = null;
    },
};
