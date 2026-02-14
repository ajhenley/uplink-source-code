/* ============================================================
   UPLINK WEB - Client-Side Game State
   Singleton that holds all game state and fires custom events
   when state changes occur.
   ============================================================ */

const GameState = {

    // ---- Player ----
    player: {
        handle: '',
        balance: 0,
        uplink_rating: 0,
        neuromancer_rating: 0,
    },

    // ---- Gateway ----
    gateway: {
        name: '',
        cpu_speed: 60,
        modem_speed: 1,
        memory_size: 24,
    },

    // ---- Connection ----
    connection: {
        bounceChain: [],       // [{position, ip, name}]
        isConnected: false,
        targetIp: null,
        traceProgress: 0,
        traceActive: false,
    },

    // ---- Current remote screen ----
    currentScreen: null,       // {screen_type, ...data}

    // ---- Running tasks ----
    tasks: [],                 // [{id, tool_name, target_ip, progress, ticks_remaining}]

    // ---- Messages ----
    messages: [],
    unreadCount: 0,

    // ---- Missions ----
    availableMissions: [],
    activeMissions: [],

    // ---- Game time ----
    gameTime: {
        ticks: 0,
        dateString: '',
    },
    speed: 1,

    // ---- Map ----
    locations: [],             // [{ip, x, y, name}]

    // ---- Software owned ----
    software: [],              // [{name, version}]

    // ================================================================
    // Event system
    // ================================================================

    _listeners: {},

    /**
     * Register a callback for a named event.
     * @param {string} event
     * @param {Function} callback
     */
    on(event, callback) {
        if (!this._listeners[event]) {
            this._listeners[event] = [];
        }
        this._listeners[event].push(callback);
    },

    /**
     * Remove a previously registered callback.
     * @param {string} event
     * @param {Function} callback
     */
    off(event, callback) {
        const list = this._listeners[event];
        if (!list) return;
        const idx = list.indexOf(callback);
        if (idx !== -1) {
            list.splice(idx, 1);
        }
    },

    /**
     * Fire an event, calling all registered listeners with the supplied data.
     * @param {string} event
     * @param {*} data
     */
    emit(event, data) {
        const list = this._listeners[event];
        if (!list) return;
        for (let i = 0; i < list.length; i++) {
            try {
                list[i](data);
            } catch (err) {
                console.error(`[GameState] Error in listener for "${event}":`, err);
            }
        }
    },

    // ================================================================
    // Update methods (each merges data and emits an event)
    // ================================================================

    /**
     * Merge partial data into player and notify listeners.
     * @param {Object} data
     */
    updatePlayer(data) {
        if (!data) return;
        Object.assign(this.player, data);
        this.emit('player_updated', this.player);
    },

    /**
     * Merge partial data into gateway and notify listeners.
     * @param {Object} data
     */
    updateGateway(data) {
        if (!data) return;
        Object.assign(this.gateway, data);
        this.emit('gateway_updated', this.gateway);
    },

    /**
     * Merge partial data into connection and notify listeners.
     * @param {Object} data
     */
    updateConnection(data) {
        if (!data) return;
        Object.assign(this.connection, data);
        this.emit('connection_updated', this.connection);
    },

    /**
     * Replace the current remote screen and notify listeners.
     * @param {Object|null} screen
     */
    setScreen(screen) {
        this.currentScreen = screen;
        this.emit('screen_updated', this.currentScreen);
    },

    /**
     * Update or add tasks by matching on id. Existing tasks are updated
     * in place; new tasks are appended.
     * @param {Array} tasks
     */
    updateTasks(tasks) {
        if (!Array.isArray(tasks)) return;
        for (const incoming of tasks) {
            const existing = this.tasks.find(t => t.id === incoming.id);
            if (existing) {
                Object.assign(existing, incoming);
            } else {
                this.tasks.push(Object.assign({}, incoming));
            }
        }
        this.emit('tasks_updated', this.tasks);
    },

    /**
     * Remove a task by id and notify listeners.
     * @param {string|number} taskId
     */
    removeTask(taskId) {
        this.tasks = this.tasks.filter(t => t.id !== taskId);
        this.emit('tasks_updated', this.tasks);
    },

    /**
     * Prepend a message to the list, increment unread count, and notify.
     * @param {Object} msg
     */
    addMessage(msg) {
        if (!msg) return;
        this.messages.unshift(msg);
        this.unreadCount++;
        this.emit('messages_updated', { messages: this.messages, unreadCount: this.unreadCount });
    },

    /**
     * Replace the full messages array, recount unread, and notify.
     * @param {Array} msgs
     */
    setMessages(msgs) {
        this.messages = Array.isArray(msgs) ? msgs : [];
        this.unreadCount = this.messages.filter(m => !m.read).length;
        this.emit('messages_updated', { messages: this.messages, unreadCount: this.unreadCount });
    },

    /**
     * Set available and active mission lists and notify.
     * @param {Array} available
     * @param {Array} active
     */
    setMissions(available, active) {
        this.availableMissions = Array.isArray(available) ? available : this.availableMissions;
        this.activeMissions = Array.isArray(active) ? active : this.activeMissions;
        this.emit('missions_updated', {
            available: this.availableMissions,
            active: this.activeMissions,
        });
    },

    /**
     * Update the game tick counter, compute the human-readable date string,
     * and notify listeners.
     *
     * The in-game epoch is 2010-03-24. Each tick represents 10 real seconds
     * of in-game time.
     *
     * @param {number} ticks
     */
    updateGameTime(ticks) {
        this.gameTime.ticks = ticks;

        // Compute date: epoch + ticks * 10 seconds
        const epoch = new Date(2010, 2, 24); // March is month index 2
        const elapsed = ticks * 10 * 1000;   // milliseconds
        const current = new Date(epoch.getTime() + elapsed);

        const year  = current.getFullYear();
        const month = String(current.getMonth() + 1).padStart(2, '0');
        const day   = String(current.getDate()).padStart(2, '0');
        const hours = String(current.getHours()).padStart(2, '0');
        const mins  = String(current.getMinutes()).padStart(2, '0');
        const secs  = String(current.getSeconds()).padStart(2, '0');

        this.gameTime.dateString = `${year}-${month}-${day} ${hours}:${mins}:${secs}`;
        this.emit('time_updated', this.gameTime);
    },

    /**
     * Set the locations array (map nodes) and notify.
     * @param {Array} locs
     */
    setLocations(locs) {
        this.locations = Array.isArray(locs) ? locs : [];
        this.emit('map_updated', this.locations);
    },

    /**
     * Set the game speed multiplier and notify.
     * @param {number} speed  0=paused, 1=normal, 3=fast, 8=megafast
     */
    setSpeed(speed) {
        this.speed = speed;
        this.emit('speed_updated', this.speed);
    },

    /**
     * Set the bounce chain nodes and notify via the connection event.
     * @param {Array} nodes  [{position, ip, name}]
     */
    setBounceChain(nodes) {
        this.connection.bounceChain = Array.isArray(nodes) ? nodes : [];
        this.emit('connection_updated', this.connection);
    },

    /**
     * Update trace progress and active flag, then notify.
     * @param {number} progress  0-100
     * @param {boolean} active
     */
    setTrace(progress, active) {
        this.connection.traceProgress = progress;
        this.connection.traceActive = active;
        this.emit('trace_updated', {
            progress: this.connection.traceProgress,
            active: this.connection.traceActive,
        });
    },

    // ================================================================
    // Reset
    // ================================================================

    /**
     * Reset all state back to defaults. Does NOT clear listeners.
     */
    reset() {
        this.player = { handle: '', balance: 0, uplink_rating: 0, neuromancer_rating: 0 };
        this.gateway = { name: '', cpu_speed: 60, modem_speed: 1, memory_size: 24 };
        this.connection = {
            bounceChain: [],
            isConnected: false,
            targetIp: null,
            traceProgress: 0,
            traceActive: false,
        };
        this.currentScreen = null;
        this.tasks = [];
        this.messages = [];
        this.unreadCount = 0;
        this.availableMissions = [];
        this.activeMissions = [];
        this.gameTime = { ticks: 0, dateString: '' };
        this.speed = 1;
        this.locations = [];
        this.software = [];
    },
};
