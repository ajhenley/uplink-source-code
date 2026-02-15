"""5Hz background game loop with trace advancement, tool ticking, and mission management."""

import threading
import time
from datetime import datetime, timezone

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
    from .tool_engine import tick_tools
    from .mission_engine import generate_missions, check_mission_expiry
    from .constants import ADMIN_REVIEW_INTERVAL

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

        # --- Tool advancement ---
        tool_events = tick_tools(gs.id, gs.speed_multiplier, ts)
        _push_tool_events(ts, tool_events)

        # --- Mission generation (every ~200 ticks) ---
        if gs.game_time_ticks % 200 < gs.speed_multiplier:
            from ..models import Mission
            from .constants import MISSION_AVAILABLE
            available_count = Mission.query.filter_by(
                game_session_id=gs.id, status=MISSION_AVAILABLE
            ).count()
            if available_count < 5:
                generate_missions(gs.id, count=3 - min(available_count, 2))

        # --- Mission expiry (every ~100 ticks) ---
        if gs.game_time_ticks % 100 < gs.speed_multiplier:
            check_mission_expiry(gs.id)

        # --- Autosave (every ~500 ticks) ---
        if gs.game_time_ticks % 500 < gs.speed_multiplier:
            gs.updated_at = datetime.now(timezone.utc)

        # --- Admin forensic review (every ~300 ticks) ---
        if gs.game_time_ticks % ADMIN_REVIEW_INTERVAL < gs.speed_multiplier:
            _admin_review(gs, ts)

        # --- Trace advancement ---
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

        # Bounce route slows trace by BOUNCE_DELAY_PER_HOP per hop
        from .constants import BOUNCE_DELAY_PER_HOP, MONITOR_TRACE_FACTOR, SEC_MONITOR
        from ..models import SecuritySystem
        bounce_route = conn.bounce_route
        bounce_factor = BOUNCE_DELAY_PER_HOP ** len(bounce_route) if bounce_route else 1.0
        effective_trace = computer.trace_speed * bounce_factor

        # Active monitor speeds up trace
        monitor = SecuritySystem.query.filter_by(
            computer_id=computer.id, security_type=SEC_MONITOR
        ).first()
        if monitor and monitor.is_active and not monitor.is_bypassed:
            effective_trace /= (1 + monitor.level * MONITOR_TRACE_FACTOR)
        # trace_speed is in seconds, 5 ticks per second
        increment = (100.0 / (effective_trace * 5)) * gs.speed_multiplier
        conn.trace_progress = min(conn.trace_progress + increment, 100.0)

        # Push WebSocket warnings at thresholds
        _check_trace_warnings(ts, conn, computer, gs)

    db.session.commit()


def _push_tool_events(ts, events):
    """Push tool progress/completion events via WebSocket."""
    from ..extensions import socketio
    from ..terminal.output import success, info, warning
    from .screen_renderer import render_screen
    from ..models import Computer

    if not events:
        return

    sid = ts.sid
    for rt, event_type, value in events:
        tool_name = rt.tool_type.replace("_", " ").title()

        if event_type == "completed":
            # Check for error in result (security blocks, encryption, etc.)
            err = rt.result.get("error") if rt.result else None

            # Build completion message
            if rt.tool_type == "PASSWORD_BREAKER":
                if err:
                    msg = warning(f"{tool_name} failed — {err}")
                else:
                    pw = rt.result.get("password", "???")
                    msg = success(f"{tool_name} complete — password: '{pw}'. Access granted.")
                    # Re-render the new screen for the player
                    if ts.is_connected:
                        comp = Computer.query.filter_by(
                            game_session_id=ts.game_session_id,
                            ip=ts.current_computer_ip,
                        ).first()
                        if comp:
                            screen = comp.get_screen(ts.current_screen_index)
                            if screen:
                                msg += "\n" + render_screen(comp, screen, ts)
            elif rt.tool_type == "FILE_COPIER":
                if err:
                    msg = warning(f"{tool_name} failed — {err}")
                else:
                    msg = success(f"{tool_name} complete — '{rt.target_param}' copied to gateway.")
            elif rt.tool_type == "FILE_DELETER":
                if err:
                    msg = warning(f"{tool_name} failed — {err}")
                else:
                    msg = success(f"{tool_name} complete — '{rt.target_param}' deleted.")
            elif rt.tool_type == "LOG_DELETER":
                count = rt.result.get("logs_wiped", 0)
                msg = success(f"{tool_name} complete — {count} log(s) wiped.")
            elif rt.tool_type == "PROXY_DISABLE":
                if err:
                    msg = warning(f"{tool_name} failed — {err}")
                else:
                    msg = success(f"{tool_name} complete — proxy bypassed.")
            elif rt.tool_type == "FIREWALL_DISABLE":
                if err:
                    msg = warning(f"{tool_name} failed — {err}")
                else:
                    msg = success(f"{tool_name} complete — firewall bypassed.")
            elif rt.tool_type == "MONITOR_BYPASS":
                if err:
                    msg = warning(f"{tool_name} failed — {err}")
                else:
                    msg = success(f"{tool_name} complete — monitor bypassed. Trace speed restored.")
            elif rt.tool_type == "DECRYPTER":
                if err:
                    msg = warning(f"{tool_name} failed — {err}")
                else:
                    msg = success(f"{tool_name} complete — '{rt.target_param}' decrypted.")
            else:
                msg = success(f"{tool_name} complete.")

            socketio.emit("output", {"text": "\n" + msg + "\n"}, to=sid)
            socketio.emit("prompt", {"text": ts.prompt}, to=sid)

        elif event_type == "milestone":
            msg = info(f"{tool_name}: {value}% complete...")
            socketio.emit("output", {"text": "\n" + msg + "\n"}, to=sid)
            socketio.emit("prompt", {"text": ts.prompt}, to=sid)


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


def _admin_review(gs, ts):
    """Periodic admin review of access logs on traced computers.

    Finds suspicious, visible logs on computers with trace_speed > 0,
    applies fines and criminal record increments based on severity,
    sends warning emails, and marks logs invisible to prevent double-punishment.
    """
    from ..models import Computer, AccessLog, Email
    from .constants import (
        FINE_LOW, FINE_MEDIUM, FINE_HIGH,
        CRIMINAL_THRESHOLD_GAMEOVER, get_criminal_level_name,
    )
    from ..extensions import socketio
    from ..terminal.output import warning, error

    # Only review computers with active tracing
    computers = Computer.query.filter(
        Computer.game_session_id == gs.id,
        Computer.trace_speed > 0,
    ).all()

    for comp in computers:
        # Find visible suspicious logs
        suspicious_logs = AccessLog.query.filter_by(
            computer_id=comp.id,
            is_visible=True,
            suspicious=True,
        ).all()

        if not suspicious_logs:
            continue

        # Determine severity from trace_action
        trace_action = comp.trace_action or ""
        if "ARREST" in trace_action.upper():
            fine = FINE_HIGH
            gs.criminal_record += 1
            severity = "HIGH"
        elif "FINE" in trace_action.upper():
            fine = FINE_MEDIUM
            severity = "MEDIUM"
        else:
            fine = FINE_LOW
            severity = "LOW"

        # Apply fine
        if fine > 0:
            gs.balance = max(0, gs.balance - fine)

        # Mark logs as invisible (prevents double-punishment)
        for log in suspicious_logs:
            log.is_visible = False

        # Build and send email
        log_count = len(suspicious_logs)
        if severity == "HIGH":
            subject = "SECURITY ALERT: Criminal Activity Detected"
            body = (
                f"Unauthorized access detected on {comp.name} ({comp.ip}).\n\n"
                f"{log_count} suspicious log entr{'y' if log_count == 1 else 'ies'} found.\n"
                f"A fine of {fine} credits has been applied.\n"
                f"Your criminal record has been updated.\n\n"
                f"Further offenses will result in arrest."
            )
        elif severity == "MEDIUM":
            subject = "Security Notice: Unauthorized Access"
            body = (
                f"Suspicious activity detected on {comp.name} ({comp.ip}).\n\n"
                f"{log_count} suspicious log entr{'y' if log_count == 1 else 'ies'} found.\n"
                f"A fine of {fine} credits has been applied.\n\n"
                f"You are advised to cease illegal activities."
            )
        else:
            subject = "Security Warning"
            body = (
                f"Unusual activity detected on {comp.name} ({comp.ip}).\n\n"
                f"{log_count} suspicious log entr{'y' if log_count == 1 else 'ies'} found.\n\n"
                f"This is a formal warning. No fine has been applied."
            )

        db.session.add(Email(
            game_session_id=gs.id,
            subject=subject,
            body=body,
            from_addr=f"{comp.name} Security",
            to_addr="agent",
            game_tick_sent=gs.game_time_ticks,
        ))

        # Push WebSocket notification
        sid = ts.sid
        if fine > 0:
            msg = warning(f"Admin review: fined {fine}c for suspicious activity on {comp.name}.")
        else:
            msg = warning(f"Admin review: warning issued for suspicious activity on {comp.name}.")
        socketio.emit("output", {"text": "\n" + msg + "\n"}, to=sid)
        socketio.emit("prompt", {"text": ts.prompt}, to=sid)

    # Check for arrest threshold
    if gs.criminal_record >= CRIMINAL_THRESHOLD_GAMEOVER:
        _execute_arrest(gs, ts)


def _execute_arrest(gs, ts):
    """Game over via arrest: send email, force disconnect, deactivate session."""
    from ..models import Connection, Email
    from ..extensions import socketio
    from ..terminal.output import error, bright_red

    sid = ts.sid

    # Send arrest email
    db.session.add(Email(
        game_session_id=gs.id,
        subject="ARRESTED: Your Uplink account has been terminated",
        body=(
            "Your criminal activities have been traced back to you.\n\n"
            "Federal agents have arrested you at your home.\n"
            "Your Uplink account has been permanently deactivated.\n\n"
            "Game Over."
        ),
        from_addr="Federal Investigation Bureau",
        to_addr="agent",
        game_tick_sent=gs.game_time_ticks,
    ))

    # Force disconnect if connected
    conn = Connection.query.filter_by(game_session_id=gs.id).first()
    if conn and conn.is_active:
        conn.is_active = False
        conn.trace_in_progress = False
        conn.trace_progress = 0.0
        conn.target_ip = None

    # Deactivate session
    gs.is_active = False

    # Emit game over banner
    banner = (
        "\n" +
        bright_red("=" * 56) + "\n" +
        bright_red("  GAME OVER") + "\n" +
        bright_red("  You have been arrested.") + "\n" +
        bright_red(f"  Criminal Record: {gs.criminal_record} offense(s)") + "\n" +
        bright_red("=" * 56) + "\n"
    )
    socketio.emit("output", {"text": banner}, to=sid)

    # Return player to session manager
    ts.disconnect()
    ts.leave_game()
    socketio.emit("prompt", {"text": ts.prompt}, to=sid)
