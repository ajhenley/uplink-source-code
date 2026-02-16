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
    from .constants import ADMIN_REVIEW_INTERVAL, NEWS_GENERATION_INTERVAL, PLOT_START_TICK, NPC_MISSION_INTERVAL

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

        # --- Random news generation (every ~800 ticks) ---
        if gs.game_time_ticks % NEWS_GENERATION_INTERVAL < gs.speed_multiplier:
            from .news_engine import generate_random_news
            generate_random_news(gs.id, gs.game_time_ticks)

        # --- NPC agent missions (every ~400 ticks) ---
        if gs.game_time_ticks % NPC_MISSION_INTERVAL < gs.speed_multiplier:
            _tick_npc_agents(gs)

        # --- Plot advancement ---
        if gs.game_time_ticks >= PLOT_START_TICK:
            from .plot_engine import tick_plot
            tick_plot(gs)

        # --- Admin forensic review (every ~300 ticks) ---
        if gs.game_time_ticks % ADMIN_REVIEW_INTERVAL < gs.speed_multiplier:
            _admin_review(gs, ts)

        # --- SysAdmin tick (LAN) ---
        if ts.is_in_lan and ts.sysadmin_state > 0:
            from .constants import SYSADMIN_TICK_INTERVAL
            if gs.game_time_ticks % SYSADMIN_TICK_INTERVAL < gs.speed_multiplier:
                _tick_sysadmin(gs, ts)

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
                elif rt.result and rt.result.get("uploaded"):
                    fname = rt.result["uploaded"]
                    to_ip = rt.result.get("to_ip", "remote")
                    msg = success(f"{tool_name} complete — '{fname}' uploaded to {to_ip}.")
                else:
                    fname = rt.result.get("copied", rt.target_param) if rt.result else rt.target_param
                    msg = success(f"{tool_name} complete — '{fname}' copied to gateway.")
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
            elif rt.tool_type == "BYPASSER":
                if err:
                    msg = warning(f"{tool_name} failed — {err}")
                else:
                    bypassed_type = rt.result.get("bypassed", "security") if rt.result else "security"
                    msg = success(f"{tool_name} complete — {bypassed_type} bypassed.")
            elif rt.tool_type == "IP_PROBE":
                discovered = rt.result.get("discovered", []) if rt.result else []
                if discovered:
                    names = ", ".join(d["name"] for d in discovered)
                    msg = success(f"{tool_name} complete — discovered: {names}. Added to links.")
                else:
                    msg = success(f"{tool_name} complete — no new systems discovered.")
            elif rt.tool_type == "LOG_MODIFIER":
                count = rt.result.get("logs_modified", 0) if rt.result else 0
                msg = success(f"{tool_name} complete — {count} log(s) modified to look innocent.")
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
    from ..models import Computer, AccessLog, Email, SecuritySystem, ComputerScreen
    from .constants import (
        FINE_LOW, FINE_MEDIUM, FINE_HIGH,
        CRIMINAL_THRESHOLD_GAMEOVER, get_criminal_level_name,
        SECURITY_MAX_LEVEL, SEC_MONITOR, SEC_PROXY,
        PASSWORD_POOL, PASSWORD_ROTATION_POOL,
        RETALIATION_TRACE_BOOST, RETALIATION_TRACE_MIN,
        RETALIATION_COUNTER_CHANCE, RETALIATION_COUNTER_FINE,
    )
    from ..extensions import socketio
    from ..terminal.output import warning, error

    sid = ts.sid

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

        # --- Reactive security hardening ---
        existing_security = SecuritySystem.query.filter_by(computer_id=comp.id).all()
        if existing_security:
            # Increment all existing security levels by 1 (capped)
            for sec in existing_security:
                if sec.level < SECURITY_MAX_LEVEL:
                    sec.level += 1
                # Reset bypassed state (admins restore security)
                sec.is_bypassed = False
        else:
            # No security existed — add a level-1 monitor
            db.session.add(SecuritySystem(
                computer_id=comp.id, security_type=SEC_MONITOR, level=1
            ))

        # Medium+ severity: add proxy if none exists
        if severity in ("MEDIUM", "HIGH"):
            has_proxy = any(s.security_type == SEC_PROXY for s in existing_security)
            if not has_proxy:
                db.session.add(SecuritySystem(
                    computer_id=comp.id, security_type=SEC_PROXY, level=1
                ))

        # --- Password rotation ---
        import random as _rng
        all_passwords = PASSWORD_POOL + PASSWORD_ROTATION_POOL
        candidates = [p for p in all_passwords if p != comp.admin_password]
        if candidates:
            new_pw = _rng.choice(candidates)
            comp.admin_password = new_pw
            # Sync the PASSWORD screen
            pw_screen = ComputerScreen.query.filter_by(
                computer_id=comp.id, screen_type="PASSWORD"
            ).first()
            if pw_screen:
                pw_screen.password = new_pw

        # --- Company retaliation ---
        # Boost trace speed (cumulative — faster trace on repeated breaches)
        if comp.trace_speed > 0:
            comp.trace_speed = max(
                RETALIATION_TRACE_MIN,
                int(comp.trace_speed * (1 - RETALIATION_TRACE_BOOST))
            )

        # HIGH severity counter-attack
        if severity == "HIGH" and _rng.random() < RETALIATION_COUNTER_CHANCE:
            gs.balance = max(0, gs.balance - RETALIATION_COUNTER_FINE)
            # Counter-attack email
            db.session.add(Email(
                game_session_id=gs.id,
                subject=f"THREAT: {comp.company_name} Retaliation",
                body=(
                    f"{comp.company_name} has launched a counter-attack.\n\n"
                    f"Our forensics team traced the breach to your gateway.\n"
                    f"A fine of {RETALIATION_COUNTER_FINE} credits has been deducted.\n\n"
                    f"Further intrusions will be met with escalating force.\n"
                    f"Consider this your final warning."
                ),
                from_addr=f"{comp.company_name} Security",
                to_addr="agent",
                game_tick_sent=gs.game_time_ticks,
            ))
            # Counter-attack news
            from .news_engine import generate_news_article as _gen_counter_news
            _gen_counter_news(
                gs.id,
                f"{comp.company_name} launches counter-attack on hacker",
                (
                    f"{comp.company_name} security division has retaliated against\n"
                    f"a hacker responsible for recent breaches. Company sources\n"
                    f"confirm financial penalties were imposed on the attacker."
                ),
                f"{comp.company_name} Security",
                gs.game_time_ticks,
            )
            # Push WebSocket warning
            counter_msg = warning(
                f"COUNTER-ATTACK: {comp.company_name} fined you {RETALIATION_COUNTER_FINE}c!"
            )
            socketio.emit("output", {"text": "\n" + counter_msg + "\n"}, to=sid)
            socketio.emit("prompt", {"text": ts.prompt}, to=sid)

        # Generate breach news article
        from .news_engine import generate_news_article
        generate_news_article(
            gs.id,
            f"Security breach reported at {comp.company_name}",
            (
                f"Security breach reported at {comp.company_name}.\n\n"
                f"Administrators at {comp.name} discovered evidence of\n"
                f"unauthorized access. Security systems have been upgraded\n"
                f"and all access credentials have been reset."
            ),
            f"{comp.company_name} Security",
            gs.game_time_ticks,
        )

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
    """Game over via arrest: seize gateway, send email, force disconnect, deactivate session."""
    from ..models import Connection, Email, Computer, Software, Hardware, DataFile
    from ..extensions import socketio
    from ..terminal.output import error, bright_red

    sid = ts.sid

    # --- Gateway seizure ---
    seized_sw = 0
    seized_hw = 0
    seized_credits = gs.balance

    # Delete all software
    sw_rows = Software.query.filter_by(game_session_id=gs.id).all()
    seized_sw = len(sw_rows)
    for sw in sw_rows:
        db.session.delete(sw)

    # Delete all hardware
    hw_rows = Hardware.query.filter_by(game_session_id=gs.id).all()
    seized_hw = len(hw_rows)
    for hw in hw_rows:
        db.session.delete(hw)

    # Delete all data files on gateway
    gw = Computer.query.filter_by(
        game_session_id=gs.id, ip=gs.gateway_ip
    ).first()
    seized_files = 0
    if gw:
        gw_files = DataFile.query.filter_by(computer_id=gw.id).all()
        seized_files = len(gw_files)
        for f in gw_files:
            db.session.delete(f)

    # Zero balance
    gs.balance = 0

    # Send arrest email
    db.session.add(Email(
        game_session_id=gs.id,
        subject="ARRESTED: Your Uplink account has been terminated",
        body=(
            "Your criminal activities have been traced back to you.\n\n"
            "Federal agents have arrested you at your home.\n"
            "Your gateway has been seized as evidence.\n"
            f"  - {seized_sw} software tool(s) confiscated\n"
            f"  - {seized_hw} hardware component(s) confiscated\n"
            f"  - {seized_files} file(s) deleted from gateway\n"
            f"  - {seized_credits:,} credits frozen\n\n"
            "Your Uplink account has been permanently deactivated.\n\n"
            "Game Over."
        ),
        from_addr="Federal Investigation Bureau",
        to_addr="agent",
        game_tick_sent=gs.game_time_ticks,
    ))

    # Generate arrest news article
    from .news_engine import generate_news_article
    generate_news_article(
        gs.id,
        "Uplink agent arrested by federal authorities",
        (
            "An Uplink-registered agent has been arrested following\n"
            "an extensive investigation into computer crimes.\n"
            "Federal agents seized the suspect's gateway equipment\n"
            "and all digital assets. The agent faces multiple charges."
        ),
        "Federal Investigation Bureau",
        gs.game_time_ticks,
    )

    # Force disconnect if connected
    conn = Connection.query.filter_by(game_session_id=gs.id).first()
    if conn and conn.is_active:
        conn.is_active = False
        conn.trace_in_progress = False
        conn.trace_progress = 0.0
        conn.target_ip = None

    # Deactivate session
    gs.is_active = False

    # Emit game over banner with seizure details
    banner = (
        "\n" +
        bright_red("=" * 56) + "\n" +
        bright_red("  GAME OVER") + "\n" +
        bright_red("  You have been arrested.") + "\n" +
        bright_red(f"  Criminal Record: {gs.criminal_record} offense(s)") + "\n" +
        bright_red("") + "\n" +
        bright_red("  GATEWAY SEIZED:") + "\n" +
        bright_red(f"    Software confiscated:  {seized_sw}") + "\n" +
        bright_red(f"    Hardware confiscated:  {seized_hw}") + "\n" +
        bright_red(f"    Files deleted:         {seized_files}") + "\n" +
        bright_red(f"    Credits frozen:        {seized_credits:,}c") + "\n" +
        bright_red("=" * 56) + "\n"
    )
    socketio.emit("output", {"text": banner}, to=sid)

    # Return player to session manager
    ts.disconnect()
    ts.leave_game()
    socketio.emit("prompt", {"text": ts.prompt}, to=sid)


def _tick_npc_agents(gs):
    """Simulate NPC agents competing for BBS missions."""
    import random as _rng
    from ..models import Mission
    from .constants import (
        NPC_AGENT_NAMES, NPC_MISSION_CHANCE, NPC_CAUGHT_CHANCE,
        NPC_CAUGHT_RATING_PENALTY, NPC_RATING_GAIN_BASE, NPC_RATING_GAIN_VARIANCE,
        MISSION_AVAILABLE, MISSION_COMPLETED,
    )

    plot_data = gs.plot_data

    # Initialize NPC state if absent
    if "npc_agents" not in plot_data:
        rng = _rng.Random(gs.id)
        npc_agents = {}
        for name in NPC_AGENT_NAMES:
            npc_agents[name] = {
                "rating": rng.randint(0, 150),
                "active": True,
            }
        plot_data["npc_agents"] = npc_agents
        gs.plot_data = plot_data

    npc_agents = plot_data["npc_agents"]

    # Pick a random active NPC
    active_npcs = [name for name, data in npc_agents.items() if data.get("active")]
    if not active_npcs:
        return

    chosen_name = _rng.choice(active_npcs)

    # Roll for mission attempt
    if _rng.random() > NPC_MISSION_CHANCE:
        return

    # Find an available mission
    available = Mission.query.filter_by(
        game_session_id=gs.id, status=MISSION_AVAILABLE
    ).all()
    if not available:
        return

    mission = _rng.choice(available)

    # Roll for caught
    if _rng.random() < NPC_CAUGHT_CHANCE:
        # NPC gets caught — loses rating, news generated
        penalty = min(npc_agents[chosen_name]["rating"], NPC_CAUGHT_RATING_PENALTY)
        npc_agents[chosen_name]["rating"] = max(0, npc_agents[chosen_name]["rating"] - penalty)

        from .news_engine import generate_news_article
        generate_news_article(
            gs.id,
            f"Agent '{chosen_name}' caught during hack attempt",
            (
                f"Uplink agent known as '{chosen_name}' was detected while\n"
                f"attempting unauthorized access. The agent's rating has\n"
                f"been penalized. The target system's security held."
            ),
            "Uplink Internal Affairs",
            gs.game_time_ticks,
        )
    else:
        # NPC succeeds — complete mission, gain rating
        mission.status = MISSION_COMPLETED
        mission.completed_at_tick = gs.game_time_ticks

        gain = NPC_RATING_GAIN_BASE + _rng.randint(0, NPC_RATING_GAIN_VARIANCE)
        npc_agents[chosen_name]["rating"] += gain

    plot_data["npc_agents"] = npc_agents
    gs.plot_data = plot_data


def _bfs_path(by_index, start, goal):
    """BFS shortest path through LAN graph. Returns list of node indices (including start and goal)."""
    from collections import deque

    if start == goal:
        return [start]

    visited = {start}
    queue = deque([(start, [start])])

    while queue:
        current, path = queue.popleft()
        node = by_index.get(current)
        if not node:
            continue
        for adj_idx in node.connections:
            if adj_idx in visited:
                continue
            new_path = path + [adj_idx]
            if adj_idx == goal:
                return new_path
            visited.add(adj_idx)
            queue.append((adj_idx, new_path))

    return []  # no path found


def _tick_sysadmin(gs, ts):
    """Advance the SysAdmin AI state machine for one tick."""
    from ..models import LanNode, Computer, AccessLog, Connection
    from .constants import (
        SYSADMIN_ASLEEP, SYSADMIN_CURIOUS, SYSADMIN_SEARCHING, SYSADMIN_FOUNDYOU,
        SYSADMIN_CURIOUS_TICKS, SYSADMIN_SEARCH_STEP_TICKS,
    )
    from ..extensions import socketio
    from ..terminal.output import warning, error, bright_red
    from .screen_renderer import render_screen

    if not ts.is_in_lan or not ts.current_computer_ip:
        return

    computer = Computer.query.filter_by(
        game_session_id=gs.id, ip=ts.current_computer_ip
    ).first()
    if not computer:
        return

    lan_nodes = LanNode.query.filter_by(computer_id=computer.id).order_by(LanNode.node_index).all()
    if not lan_nodes:
        return

    by_index = {n.node_index: n for n in lan_nodes}
    sid = ts.sid

    ts.sysadmin_timer += gs.speed_multiplier

    if ts.sysadmin_state == SYSADMIN_CURIOUS:
        if ts.sysadmin_timer >= SYSADMIN_CURIOUS_TICKS:
            # Transition to SEARCHING
            ts.sysadmin_state = SYSADMIN_SEARCHING
            ts.sysadmin_timer = 0
            ts.sysadmin_node = 0  # Start at ROUTER

            # Start trace on the ISM if not already tracing
            conn = Connection.query.filter_by(game_session_id=gs.id).first()
            if conn and conn.is_active and not conn.trace_in_progress:
                conn.trace_in_progress = True
                conn.trace_progress = 0.0

            msg = warning("SysAdmin alerted! Searching for intruder...")
            socketio.emit("output", {"text": "\n" + msg + "\n"}, to=sid)
            socketio.emit("prompt", {"text": ts.prompt}, to=sid)

    elif ts.sysadmin_state == SYSADMIN_SEARCHING:
        if ts.sysadmin_timer >= SYSADMIN_SEARCH_STEP_TICKS:
            ts.sysadmin_timer = 0

            # Recompute BFS from sysadmin's current node to player's current node
            path = _bfs_path(by_index, ts.sysadmin_node, ts.current_lan_node)
            if len(path) >= 2:
                # Move one step toward player
                next_node_idx = path[1]
                ts.sysadmin_node = next_node_idx
                next_node = by_index.get(next_node_idx)
                label = next_node.label if next_node else f"Node {next_node_idx}"

                if next_node_idx == ts.current_lan_node:
                    # Caught the player
                    ts.sysadmin_state = SYSADMIN_FOUNDYOU
                    _sysadmin_catch_player(gs, ts, computer, by_index, lan_nodes)
                else:
                    msg = warning(f"SysAdmin moved to {label}")
                    socketio.emit("output", {"text": "\n" + msg + "\n"}, to=sid)
                    socketio.emit("prompt", {"text": ts.prompt}, to=sid)
            elif len(path) <= 1:
                # Already at player or no path — caught
                ts.sysadmin_state = SYSADMIN_FOUNDYOU
                _sysadmin_catch_player(gs, ts, computer, by_index, lan_nodes)


def _sysadmin_catch_player(gs, ts, computer, by_index, lan_nodes):
    """SysAdmin catches the player in the LAN."""
    from ..models import AccessLog, Connection
    from .constants import SYSADMIN_ASLEEP
    from ..extensions import socketio
    from ..terminal.output import bright_red
    from .screen_renderer import render_screen

    sid = ts.sid

    # 1. Re-lock all bypassed LAN nodes
    for node in lan_nodes:
        if node.is_bypassed:
            node.is_bypassed = False
            if node.security_level > 0:
                node.is_locked = True

    # 2. Kick player back to ROUTER
    ts.current_lan_node = 0

    # 3. Create suspicious access log
    log = AccessLog(
        computer_id=computer.id,
        game_tick=gs.game_time_ticks,
        from_ip=gs.gateway_ip or "unknown",
        from_name=ts.username or "unknown",
        action="INTRUDER DETECTED by SysAdmin",
        suspicious=True,
    )
    db.session.add(log)

    # 4. Boost trace progress by 15%
    conn = Connection.query.filter_by(game_session_id=gs.id).first()
    if conn and conn.is_active:
        conn.trace_progress = min(conn.trace_progress + 15.0, 100.0)

    # 5. Reset sysadmin to ASLEEP
    ts.sysadmin_state = SYSADMIN_ASLEEP
    ts.sysadmin_node = None
    ts.sysadmin_timer = 0

    # 6. Emit dramatic banner + re-render
    banner = (
        "\n" +
        bright_red("=" * 56) + "\n" +
        bright_red("  INTRUDER DETECTED") + "\n" +
        bright_red("  SysAdmin has found you!") + "\n" +
        bright_red("  All bypassed nodes re-locked. Returned to Router.") + "\n" +
        bright_red("  Trace boosted +15%.") + "\n" +
        bright_red("=" * 56) + "\n"
    )

    # Re-render the LAN screen
    screen = computer.get_screen(ts.current_screen_index)
    lan_view = ""
    if screen:
        lan_view = "\n" + render_screen(computer, screen, ts)

    socketio.emit("output", {"text": banner + lan_view}, to=sid)
    socketio.emit("prompt", {"text": ts.prompt}, to=sid)
