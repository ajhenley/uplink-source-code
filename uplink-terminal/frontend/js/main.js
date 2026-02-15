(function () {
    "use strict";

    // --- Terminal setup ---
    const term = new window.Terminal({
        cursorBlink: true,
        cursorStyle: "block",
        fontFamily: "'Courier New', 'Lucida Console', monospace",
        fontSize: 15,
        lineHeight: 1.2,
        theme: {
            background: "#0a0a0a",
            foreground: "#00ff41",
            cursor: "#00ff41",
            cursorAccent: "#0a0a0a",
            selectionBackground: "rgba(0, 255, 65, 0.25)",
            black: "#0a0a0a",
            green: "#00ff41",
            brightGreen: "#00ff41",
            red: "#ff3333",
            brightRed: "#ff5555",
            yellow: "#ffcc00",
            brightYellow: "#ffdd33",
            cyan: "#00cccc",
            brightCyan: "#33ffff",
            white: "#cccccc",
            brightWhite: "#ffffff",
        },
        scrollback: 5000,
        allowProposedApi: true,
    });

    const fitAddon = new window.FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(document.getElementById("terminal"));
    fitAddon.fit();

    window.addEventListener("resize", function () {
        fitAddon.fit();
    });

    // --- Line buffer ---
    let lineBuffer = "";
    let passwordMode = false;
    let currentPrompt = "> ";

    // --- Command history ---
    var cmdHistory = [];
    var historyIndex = -1;
    var historyMax = 50;

    // --- Audio beeps (Web Audio API) ---
    var audioCtx = null;
    function getAudioCtx() {
        if (!audioCtx) {
            try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }
            catch (e) { /* no audio support */ }
        }
        return audioCtx;
    }

    function beep(freq, duration) {
        var ctx = getAudioCtx();
        if (!ctx) return;
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = freq;
        gain.gain.value = 0.08;
        osc.start();
        osc.stop(ctx.currentTime + duration / 1000);
    }

    function writePrompt() {
        term.write(currentPrompt);
    }

    function clearLineBuffer() {
        // Erase the visible line buffer from the terminal
        if (!passwordMode) {
            for (var i = 0; i < lineBuffer.length; i++) {
                term.write("\b \b");
            }
        }
        lineBuffer = "";
    }

    term.onKey(function (ev) {
        const key = ev.key;
        const code = key.charCodeAt(0);

        // Detect arrow keys (escape sequences)
        if (key === "\x1b[A") {
            // Up arrow — previous history
            if (cmdHistory.length === 0) return;
            if (historyIndex < cmdHistory.length - 1) {
                historyIndex++;
            }
            clearLineBuffer();
            lineBuffer = cmdHistory[cmdHistory.length - 1 - historyIndex];
            if (!passwordMode) term.write(lineBuffer);
            return;
        }
        if (key === "\x1b[B") {
            // Down arrow — next history
            if (historyIndex <= 0) {
                historyIndex = -1;
                clearLineBuffer();
                return;
            }
            historyIndex--;
            clearLineBuffer();
            lineBuffer = cmdHistory[cmdHistory.length - 1 - historyIndex];
            if (!passwordMode) term.write(lineBuffer);
            return;
        }

        if (code === 13) {
            // Enter
            term.write("\r\n");
            if (lineBuffer.length > 0) {
                // Push to history
                if (!passwordMode) {
                    cmdHistory.push(lineBuffer);
                    if (cmdHistory.length > historyMax) {
                        cmdHistory.shift();
                    }
                }
                socket.emit("input", { text: lineBuffer });
            } else {
                socket.emit("input", { text: "" });
            }
            lineBuffer = "";
            historyIndex = -1;
        } else if (code === 127 || code === 8) {
            // Backspace
            if (lineBuffer.length > 0) {
                lineBuffer = lineBuffer.slice(0, -1);
                if (!passwordMode) {
                    term.write("\b \b");
                }
            }
        } else if (code >= 32) {
            // Printable character
            lineBuffer += key;
            if (!passwordMode) {
                term.write(key);
            }
        }
    });

    // Handle paste
    term.onData(function (data) {
        // onData fires for paste; onKey handles single keys
        // Only handle multi-char pastes here
        if (data.length > 1) {
            for (var i = 0; i < data.length; i++) {
                var ch = data[i];
                if (ch === "\r" || ch === "\n") continue;
                if (ch.charCodeAt(0) >= 32) {
                    lineBuffer += ch;
                    if (!passwordMode) {
                        term.write(ch);
                    }
                }
            }
        }
    });

    // --- WebSocket ---
    var socket = io({
        transports: ["websocket"],
        reconnection: true,
        reconnectionDelay: 3000,
        reconnectionAttempts: Infinity,
    });

    socket.on("connect", function () {
        // Server sends welcome banner on connect
    });

    socket.on("disconnect", function () {
        term.write("\r\n\x1b[91m[!] Connection lost. Reconnecting...\x1b[0m\r\n");
    });

    socket.on("output", function (data) {
        // Convert \n to \r\n for xterm
        var text = data.text.replace(/(?<!\r)\n/g, "\r\n");
        term.write(text);

        // Audio feedback on key events
        if (data.text.indexOf("TRACE") !== -1 && data.text.indexOf("%") !== -1) {
            beep(800, 200);   // alarm beep for trace warnings
        } else if (data.text.indexOf("GAME OVER") !== -1) {
            beep(200, 500);   // low tone for game over
        } else if (data.text.indexOf("[+]") !== -1) {
            beep(600, 80);    // success chirp
        } else if (data.text.indexOf("[!]") !== -1) {
            beep(150, 150);   // error buzz
        }
    });

    socket.on("prompt", function (data) {
        currentPrompt = data.text;
        writePrompt();
    });

    socket.on("password_prompt", function () {
        passwordMode = true;
    });

    socket.on("password_done", function () {
        passwordMode = false;
    });
})();
