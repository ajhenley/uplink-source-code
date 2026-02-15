"""5Hz background game loop with trace advancement."""

import threading
import time

from ..extensions import db
from ..ws.handlers import sessions
from ..terminal.session import SessionState


def start_game_loop(app):
    """Start the background game tick loop."""

    def loop():
        while True:
            time.sleep(0.2)  # 5Hz
            with app.app_context():
                tick()

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def tick():
    """Advance one game tick for all active in-game sessions."""
    from ..models import GameSession, Connection, Computer

    active_sessions = [
        ts for ts in sessions.values()
        if ts.state == SessionState.IN_GAME and ts.game_session_id
    ]

    if not active_sessions:
        return

    for ts in active_sessions:
        gs = db.session.get(GameSession, ts.game_session_id)
        if not gs or gs.speed_multiplier <= 0:
            continue

        # Advance game time
        gs.game_time_ticks += gs.speed_multiplier

        # Advance trace if active
        conn = Connection.query.filter_by(
            game_session_id=gs.id
        ).first()

        if not conn or not conn.is_active or not conn.trace_in_progress:
            continue

        computer = Computer.query.filter_by(
            game_session_id=gs.id, ip=conn.target_ip
        ).first()

        if not computer or computer.trace_speed <= 0:
            continue

        # increment = (100 / (trace_speed * 5)) * speed_multiplier
        # trace_speed is in seconds, 5 ticks per second
        increment = (100.0 / (computer.trace_speed * 5)) * gs.speed_multiplier
        conn.trace_progress = min(conn.trace_progress + increment, 100.0)

        # Push WebSocket warnings at thresholds
        _check_trace_warnings(ts, conn, computer, gs)

    db.session.commit()


def _check_trace_warnings(ts, conn, computer, gs):
    """Send trace warnings and execute trace actions at 100%."""
    from flask_socketio import emit
    from ..extensions import socketio
    from ..terminal.output import warning, error, bright_red

    progress = conn.trace_progress
    sid = ts.sid

    # Warning at 50%
    if 49.5 < progress <= 52.0:
        socketio.emit("output", {
            "text": "\n" + warning("Trace at 50% — consider disconnecting.") + "\n"
        }, to=sid)
        socketio.emit("prompt", {"text": ts.prompt}, to=sid)

    # Warning at 75%
    elif 74.5 < progress <= 77.0:
        socketio.emit("output", {
            "text": "\n" + warning("TRACE AT 75% — DISCONNECT IMMEDIATELY!") + "\n"
        }, to=sid)
        socketio.emit("prompt", {"text": ts.prompt}, to=sid)

    # Trace complete at 100%
    elif progress >= 100.0:
        _execute_trace_action(ts, conn, computer, gs)


def _execute_trace_action(ts, conn, computer, gs):
    """Execute the trace action when trace reaches 100%."""
    from ..extensions import socketio
    from ..terminal.output import error, bright_red, warning

    actions = computer.trace_action.split(",") if computer.trace_action else ["DISCONNECT"]
    sid = ts.sid

    messages = ["\n" + error("TRACE COMPLETE — Security has located you!")]

    for action in actions:
        action = action.strip().upper()
        if action == "DISCONNECT":
            messages.append(warning("Connection terminated by remote system."))
        elif action == "FINE":
            fine_amount = 500
            gs.balance = max(0, gs.balance - fine_amount)
            messages.append(warning(f"You have been fined {fine_amount} credits."))
        elif action == "ARREST":
            messages.append(error("Criminal record updated."))

    # Disconnect
    conn.is_active = False
    conn.trace_in_progress = False
    conn.trace_progress = 0.0
    conn.target_ip = None
    ts.disconnect()

    messages.append("")
    socketio.emit("output", {"text": "\n".join(messages) + "\n"}, to=sid)
    socketio.emit("prompt", {"text": ts.prompt}, to=sid)
