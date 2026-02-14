"""Flask-SocketIO event handlers for real-time game communication."""
import logging

from flask import request
from flask_socketio import emit, join_room, leave_room

from app.extensions import socketio, db
from app.models.game_session import GameSession
from app.models.player import Player
from app.models.connection import Connection, ConnectionNode
from app.models.message import Message
from app.models.running_task import RunningTask
from app.game import connection_manager, task_engine, mission_engine
from app.ws import protocol as MSG

log = logging.getLogger(__name__)


class SessionState:
    """Per-connection state tracking for a WebSocket client."""

    def __init__(self, user_id, game_session_id, player_id,
                 computer_id=None, current_sub_page=0):
        self.user_id = user_id
        self.game_session_id = game_session_id
        self.player_id = player_id
        self.computer_id = computer_id
        self.current_sub_page = current_sub_page

    def as_dict(self):
        return {
            "user_id": self.user_id,
            "game_session_id": self.game_session_id,
            "player_id": self.player_id,
            "computer_id": self.computer_id,
            "current_sub_page": self.current_sub_page,
        }

    def update_from(self, d):
        for key in ("computer_id", "current_sub_page"):
            if key in d:
                setattr(self, key, d[key])


# Module-level dict mapping SocketIO session id (request.sid) to SessionState.
sessions = {}

# Mapping game_session_id -> set of request.sid values (used by game_loop).
session_rooms = {}


@socketio.on("join")
def handle_join(data):
    """Client joins a game session room."""
    try:
        game_session_id = data.get("session_id")
        user_id = data.get("user_id")

        if not game_session_id or not user_id:
            emit(MSG.MSG_ERROR, {"message": "session_id and user_id are required"})
            return

        game_session = GameSession.query.get(game_session_id)
        if game_session is None:
            emit(MSG.MSG_ERROR, {"message": "Game session not found"})
            return

        if game_session.user_id != int(user_id):
            emit(MSG.MSG_ERROR, {"message": "Access denied"})
            return

        player = Player.query.filter_by(game_session_id=game_session_id).first()
        if player is None:
            emit(MSG.MSG_ERROR, {"message": "Player not found for this session"})
            return

        state = SessionState(
            user_id=int(user_id),
            game_session_id=game_session_id,
            player_id=player.id,
        )
        sessions[request.sid] = state
        session_rooms.setdefault(game_session_id, set()).add(request.sid)

        join_room(game_session_id)

        # Build initial state payload
        connection = Connection.query.filter_by(
            game_session_id=game_session_id, player_id=player.id
        ).first()
        bounce_chain = []
        connection_data = None
        if connection is not None:
            nodes = ConnectionNode.query.filter_by(
                connection_id=connection.id
            ).order_by(ConnectionNode.position).all()
            bounce_chain = [{"position": n.position, "ip": n.ip} for n in nodes]
            connection_data = {
                "is_active": connection.is_active,
                "target_ip": connection.target_ip,
                "trace_progress": connection.trace_progress,
                "trace_active": connection.trace_active,
            }

        unread_count = Message.query.filter_by(
            game_session_id=game_session_id, player_id=player.id, is_read=False
        ).count()

        active_tasks = RunningTask.query.filter_by(
            game_session_id=game_session_id, player_id=player.id, is_active=True
        ).all()

        emit("joined", {
            "session_id": game_session_id,
            "player": {
                "id": player.id,
                "name": player.name,
                "handle": player.handle,
                "balance": player.balance,
                "uplink_rating": player.uplink_rating,
                "neuromancer_rating": player.neuromancer_rating,
                "credit_rating": player.credit_rating,
                "localhost_ip": player.localhost_ip,
            },
            "connection": connection_data,
            "bounce_chain": bounce_chain,
            "unread_messages": unread_count,
            "active_tasks": [
                {
                    "id": t.id,
                    "tool_name": t.tool_name,
                    "tool_version": t.tool_version,
                    "target_ip": t.target_ip,
                    "progress": t.progress,
                    "ticks_remaining": t.ticks_remaining,
                }
                for t in active_tasks
            ],
            "game_time_ticks": game_session.game_time_ticks,
        })

    except Exception as exc:
        log.exception("Error in join handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_HEARTBEAT)
def handle_heartbeat(data):
    """Respond to client heartbeat."""
    state = sessions.get(request.sid)
    payload = {"server_time": data.get("client_time", 0)}
    if state is not None:
        game_session = GameSession.query.get(state.game_session_id)
        if game_session:
            payload["game_time_ticks"] = game_session.game_time_ticks
    emit(MSG.MSG_HEARTBEAT_ACK, payload)


@socketio.on(MSG.MSG_BOUNCE_ADD)
def handle_bounce_add(data):
    """Add an IP to the bounce chain."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        ip = data.get("ip")
        if not ip:
            emit(MSG.MSG_ERROR, {"message": "ip is required"})
            return

        chain = connection_manager.add_bounce(
            state.game_session_id, state.player_id, ip
        )
        db.session.commit()
        emit(MSG.MSG_BOUNCE_CHAIN_UPDATED, {"bounce_chain": chain},
             room=state.game_session_id)

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in bounce_add handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_BOUNCE_REMOVE)
def handle_bounce_remove(data):
    """Remove a bounce node by position."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        position = data.get("position")
        if position is None:
            emit(MSG.MSG_ERROR, {"message": "position is required"})
            return

        chain = connection_manager.remove_bounce(
            state.game_session_id, state.player_id, int(position)
        )
        db.session.commit()
        emit(MSG.MSG_BOUNCE_CHAIN_UPDATED, {"bounce_chain": chain},
             room=state.game_session_id)

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in bounce_remove handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on("connect_to")
def handle_connect_to(data):
    """Establish connection through bounce chain to the target computer."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        result = connection_manager.connect(
            state.game_session_id, state.player_id
        )
        db.session.commit()

        state.computer_id = result["computer_id"]
        state.current_sub_page = result["screen"]["screen_index"]

        emit(MSG.MSG_CONNECTED, {
            "target_ip": result["target_ip"],
            "computer_id": result["computer_id"],
            "screen": result["screen"],
        })

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in connect_to handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on("disconnect_from")
def handle_disconnect_from(data):
    """Disconnect from the currently connected computer."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        connection_manager.disconnect(
            state.game_session_id, state.player_id
        )
        db.session.commit()

        state.computer_id = None
        state.current_sub_page = 0

        emit(MSG.MSG_DISCONNECTED, {"session_id": state.game_session_id})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in disconnect_from handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_SCREEN_ACTION)
def handle_screen_action(data):
    """Process a screen interaction (password submit, menu select, etc.)."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        action = data.get("action")
        action_data = data.get("data", {})

        if not action:
            emit(MSG.MSG_ERROR, {"message": "action is required"})
            return

        session_state_dict = state.as_dict()
        screen_data = connection_manager.handle_screen_action(
            state.game_session_id, state.player_id,
            action, action_data, session_state_dict,
        )
        db.session.commit()

        # Update local state from any changes the handler made
        state.update_from(session_state_dict)

        emit(MSG.MSG_SCREEN_UPDATE, {"screen": screen_data})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in screen_action handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_RUN_TOOL)
def handle_run_tool(data):
    """Start a hacking tool."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        tool_name = data.get("tool_name")
        tool_version = data.get("tool_version", 1)
        target_ip = data.get("target_ip")
        target_data = data.get("target_data", {})

        if not tool_name:
            emit(MSG.MSG_ERROR, {"message": "tool_name is required"})
            return

        task_data = task_engine.start_task(
            state.game_session_id, state.player_id,
            tool_name, int(tool_version), target_ip, target_data,
        )
        db.session.commit()

        emit(MSG.MSG_TASK_UPDATE, task_data)

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in run_tool handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_STOP_TOOL)
def handle_stop_tool(data):
    """Stop a running hacking tool."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        task_id = data.get("task_id")
        if task_id is None:
            emit(MSG.MSG_ERROR, {"message": "task_id is required"})
            return

        task_data = task_engine.stop_task(int(task_id))
        db.session.commit()

        emit(MSG.MSG_TASK_UPDATE, task_data)

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in stop_tool handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_SET_SPEED)
def handle_set_speed(data):
    """Update game speed multiplier for this session."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        speed = data.get("speed")
        if speed is None:
            emit(MSG.MSG_ERROR, {"message": "speed is required"})
            return

        speed = int(speed)
        if speed not in (0, 1, 3, 8):
            emit(MSG.MSG_ERROR, {"message": "speed must be 0, 1, 3, or 8"})
            return

        # Update the game loop speed multiplier if the game loop module exists
        try:
            from app.game.game_loop import game_loop
            game_loop.speed_multiplier[state.game_session_id] = speed
        except ImportError:
            pass

        emit(MSG.MSG_SPEED_CHANGED, {
            "speed": speed,
            "session_id": state.game_session_id,
        }, room=state.game_session_id)

    except Exception as exc:
        log.exception("Error in set_speed handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_ACCEPT_MISSION)
def handle_accept_mission(data):
    """Accept a mission from the BBS."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        mission_id = data.get("mission_id")
        if mission_id is None:
            emit(MSG.MSG_ERROR, {"message": "mission_id is required"})
            return

        mission_data = mission_engine.accept_mission(
            state.game_session_id, state.player_id, int(mission_id)
        )
        db.session.commit()

        emit("mission_accepted", mission_data)

        # If currently viewing the BBS, refresh the screen
        if state.computer_id is not None:
            try:
                screen_data = connection_manager.build_screen_data(
                    state.computer_id, state.current_sub_page,
                    game_session_id=state.game_session_id,
                    player_rating=Player.query.get(state.player_id).uplink_rating,
                )
                emit(MSG.MSG_SCREEN_UPDATE, {"screen": screen_data})
            except Exception:
                pass

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in accept_mission handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_COMPLETE_MISSION)
def handle_complete_mission(data):
    """Check and complete a mission."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        mission_id = data.get("mission_id")
        if mission_id is None:
            emit(MSG.MSG_ERROR, {"message": "mission_id is required"})
            return

        check_result = mission_engine.check_mission_completion(
            state.game_session_id, state.player_id, int(mission_id)
        )

        if not check_result.get("completed"):
            emit(MSG.MSG_ERROR, {
                "message": check_result.get("reason", "Mission not yet completed"),
            })
            return

        result = mission_engine.complete_mission(
            state.game_session_id, state.player_id, int(mission_id)
        )
        db.session.commit()

        emit("mission_completed", result)

        emit(MSG.MSG_BALANCE_CHANGED, {
            "balance": result["balance"],
            "session_id": state.game_session_id,
        })
        emit(MSG.MSG_RATING_CHANGED, {
            "uplink_rating": result["uplink_rating"],
            "neuromancer_rating": result["neuromancer_rating"],
            "session_id": state.game_session_id,
        })

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in complete_mission handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_BUY_SOFTWARE)
def handle_buy_software(data):
    """Buy software from the store."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        tool_name = data.get("tool_name")
        version = data.get("version", 1)

        if not tool_name:
            emit(MSG.MSG_ERROR, {"message": "tool_name is required"})
            return

        try:
            from app.game import store_engine
            result = store_engine.buy_software(
                state.game_session_id, state.player_id, tool_name, int(version)
            )
        except ImportError:
            emit(MSG.MSG_ERROR, {"message": "Store not available yet"})
            return

        db.session.commit()

        if result.get("success"):
            emit("software_purchased", result)
            emit(MSG.MSG_BALANCE_CHANGED, {
                "balance": result.get("balance", 0),
                "session_id": state.game_session_id,
            })
        else:
            emit(MSG.MSG_ERROR, {"message": result.get("reason", "Purchase failed")})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in buy_software handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_BUY_HARDWARE)
def handle_buy_hardware(data):
    """Buy hardware upgrade from the store."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        hardware_type = data.get("hardware_type")
        level = data.get("level", 1)

        if not hardware_type:
            emit(MSG.MSG_ERROR, {"message": "hardware_type is required"})
            return

        try:
            from app.game import store_engine
            result = store_engine.buy_hardware(
                state.game_session_id, state.player_id, hardware_type, int(level)
            )
        except ImportError:
            emit(MSG.MSG_ERROR, {"message": "Store not available yet"})
            return

        db.session.commit()

        if result.get("success"):
            emit("hardware_purchased", result)
            emit(MSG.MSG_BALANCE_CHANGED, {
                "balance": result.get("balance", 0),
                "session_id": state.game_session_id,
            })
        else:
            emit(MSG.MSG_ERROR, {"message": result.get("reason", "Purchase failed")})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in buy_hardware handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_BUY_STOCK)
def handle_buy_stock(data):
    """Buy stock shares."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        company_name = data.get("company_name")
        shares = data.get("shares", 1)
        if not company_name:
            emit(MSG.MSG_ERROR, {"message": "company_name is required"})
            return

        from app.game import finance_engine
        result = finance_engine.buy_stock(
            state.game_session_id, state.player_id, company_name, int(shares)
        )
        db.session.commit()

        if result.get("success"):
            emit(MSG.MSG_STOCK_UPDATE, result)
            emit(MSG.MSG_BALANCE_CHANGED, {
                "balance": result.get("balance", 0),
                "session_id": state.game_session_id,
            })
        else:
            emit(MSG.MSG_ERROR, {"message": result.get("reason", "Purchase failed")})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in buy_stock handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_SELL_STOCK)
def handle_sell_stock(data):
    """Sell stock shares."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        company_name = data.get("company_name")
        shares = data.get("shares", 1)
        if not company_name:
            emit(MSG.MSG_ERROR, {"message": "company_name is required"})
            return

        from app.game import finance_engine
        result = finance_engine.sell_stock(
            state.game_session_id, state.player_id, company_name, int(shares)
        )
        db.session.commit()

        if result.get("success"):
            emit(MSG.MSG_STOCK_UPDATE, result)
            emit(MSG.MSG_BALANCE_CHANGED, {
                "balance": result.get("balance", 0),
                "session_id": state.game_session_id,
            })
        else:
            emit(MSG.MSG_ERROR, {"message": result.get("reason", "Sale failed")})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in sell_stock handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_TAKE_LOAN)
def handle_take_loan(data):
    """Take out a loan."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        amount = data.get("amount")
        if not amount or int(amount) <= 0:
            emit(MSG.MSG_ERROR, {"message": "Valid amount is required"})
            return

        from app.game import finance_engine
        game_session = GameSession.query.get(state.game_session_id)
        current_tick = game_session.game_time_ticks if game_session else 0
        result = finance_engine.take_loan(
            state.game_session_id, state.player_id, int(amount), current_tick
        )
        db.session.commit()

        if result.get("success"):
            emit(MSG.MSG_BALANCE_CHANGED, {
                "balance": result.get("balance", 0),
                "session_id": state.game_session_id,
            })
            emit("loan_taken", result)
        else:
            emit(MSG.MSG_ERROR, {"message": result.get("reason", "Loan denied")})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in take_loan handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_REPAY_LOAN)
def handle_repay_loan(data):
    """Repay a loan."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        loan_id = data.get("loan_id")
        amount = data.get("amount")
        if loan_id is None or not amount:
            emit(MSG.MSG_ERROR, {"message": "loan_id and amount are required"})
            return

        from app.game import finance_engine
        result = finance_engine.repay_loan(
            state.game_session_id, state.player_id, int(loan_id), int(amount)
        )
        db.session.commit()

        if result.get("success"):
            emit(MSG.MSG_BALANCE_CHANGED, {
                "balance": result.get("balance", 0),
                "session_id": state.game_session_id,
            })
            emit("loan_repaid", result)
        else:
            emit(MSG.MSG_ERROR, {"message": result.get("reason", "Repayment failed")})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in repay_loan handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_LAN_ACTION)
def handle_lan_action(data):
    """Perform a LAN hacking action."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        action = data.get("action")
        action_data = data.get("data", {})
        if not action:
            emit(MSG.MSG_ERROR, {"message": "action is required"})
            return

        from app.game import lan_engine
        result = lan_engine.lan_action(
            state.game_session_id, state.player_id, action, action_data
        )
        db.session.commit()

        if result.get("error"):
            emit(MSG.MSG_ERROR, {"message": result["error"]})
        else:
            # Send updated LAN state
            lan_state = lan_engine.get_lan_state(
                state.game_session_id, state.player_id
            )
            emit(MSG.MSG_LAN_UPDATE, {"lan": lan_state, "result": result})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in lan_action handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_CHOOSE_SIDE)
def handle_choose_side(data):
    """Choose Arunmor or ARC in the plot."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        side = data.get("side")
        if side not in ("arunmor", "arc"):
            emit(MSG.MSG_ERROR, {"message": "side must be 'arunmor' or 'arc'"})
            return

        from app.game import plot_engine
        plot_engine.choose_side(state.game_session_id, side)
        db.session.commit()

        plot_state = plot_engine.get_plot_state(state.game_session_id)
        emit(MSG.MSG_PLOT_UPDATE, {"plot": plot_state})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in choose_side handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_COMPLETE_SPECIAL_MISSION)
def handle_complete_special_mission(data):
    """Complete a special plot mission."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        mission_id = data.get("mission_id")
        if mission_id is None:
            emit(MSG.MSG_ERROR, {"message": "mission_id is required"})
            return

        from app.game import plot_engine
        result = plot_engine.complete_special_mission(
            state.game_session_id, int(mission_id)
        )
        db.session.commit()

        if result.get("success"):
            emit("special_mission_completed", result)
            player = Player.query.get(state.player_id)
            if player:
                emit(MSG.MSG_BALANCE_CHANGED, {
                    "balance": player.balance,
                    "session_id": state.game_session_id,
                })
        else:
            emit(MSG.MSG_ERROR, {"message": result.get("reason", "Not completed")})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in complete_special_mission handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on(MSG.MSG_MARK_READ)
def handle_mark_read(data):
    """Mark a message as read."""
    state = sessions.get(request.sid)
    if state is None:
        emit(MSG.MSG_ERROR, {"message": "Not joined to a session"})
        return
    try:
        message_id = data.get("message_id")
        if message_id is None:
            emit(MSG.MSG_ERROR, {"message": "message_id is required"})
            return

        msg = Message.query.get(int(message_id))
        if msg and msg.game_session_id == state.game_session_id:
            msg.is_read = True
            db.session.commit()
            unread = Message.query.filter_by(
                game_session_id=state.game_session_id,
                player_id=state.player_id,
                is_read=False,
            ).count()
            emit("message_read", {"message_id": message_id, "unread_count": unread})

    except Exception as exc:
        db.session.rollback()
        log.exception("Error in mark_read handler")
        emit(MSG.MSG_ERROR, {"message": str(exc)})


@socketio.on('cheat')
def handle_cheat(data):
    """Process cheat code input from the client."""
    state = sessions.get(request.sid)
    if state is None:
        return
    sid = state.game_session_id
    code = data.get('cheat_code', '')

    try:
        player = Player.query.filter_by(game_session_id=sid).first()
        if player is None:
            return

        if code == 'lotsofmoney':
            player.balance += 10000
            emit('balance_changed', {'balance': player.balance})

        elif code == 'nextrating':
            player.uplink_rating += 1
            emit('rating_changed', {'uplink_rating': player.uplink_rating, 'neuromancer_rating': player.neuromancer_rating})

        elif code == 'maxratings':
            player.uplink_rating = 2500
            emit('rating_changed', {'uplink_rating': player.uplink_rating, 'neuromancer_rating': player.neuromancer_rating})

        elif code == 'canceltrace':
            conn = Connection.query.filter_by(game_session_id=sid, is_active=True).first()
            if conn:
                conn.trace_active = False
                conn.trace_progress = 0
                emit('trace_update', {'progress': 0, 'active': False}, room=sid)

        elif code == 'allsoftware':
            from app.models.data_file import DataFile
            from app.models.vlocation import VLocation
            gw_loc = VLocation.query.filter_by(game_session_id=sid, ip=player.localhost_ip).first()
            if gw_loc and gw_loc.computer_id:
                from app.game import constants as C
                existing = {f.filename for f in DataFile.query.filter_by(computer_id=gw_loc.computer_id).all()}
                for sw in C.SOFTWARE_UPGRADES:
                    fname = f"{sw[0]} v{sw[4]}"
                    if fname not in existing:
                        db.session.add(DataFile(
                            computer_id=gw_loc.computer_id,
                            filename=fname,
                            size=sw[3],
                            softwaretype=sw[1],
                            data=str(sw[4]),
                        ))
                emit('gateway_updated', {}, room=sid)

        elif code == 'allhardware':
            from app.models.gateway import Gateway
            gw = Gateway.query.filter_by(game_session_id=sid).first()
            if gw:
                gw.cpu_speed = 200
                gw.modem_speed = 10
                gw.memory_size = 32
                gw.has_self_destruct = True
                gw.has_motion_sensor = True
                emit('gateway_updated', {}, room=sid)

        elif code == 'allinks':
            from app.models.vlocation import VLocation
            locs = VLocation.query.filter_by(game_session_id=sid).all()
            loc_data = [{"id": l.id, "ip": l.ip, "x": l.x, "y": l.y} for l in locs]
            emit('locations_updated', {"locations": loc_data})

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        emit('error', {'message': str(e)})


@socketio.on("disconnect")
def handle_disconnect():
    """Clean up session state when a client disconnects."""
    state = sessions.pop(request.sid, None)
    if state is not None:
        # Auto-save: record the last saved tick on disconnect
        try:
            session = db.session.get(GameSession, state.game_session_id)
            if session:
                session.last_saved_at = session.game_time_ticks
                db.session.commit()
        except Exception:
            db.session.rollback()

        leave_room(state.game_session_id)
        # Remove from session_rooms tracking
        room_set = session_rooms.get(state.game_session_id)
        if room_set is not None:
            room_set.discard(request.sid)
            if not room_set:
                del session_rooms[state.game_session_id]
        log.info(
            "Client %s disconnected from session %s",
            request.sid, state.game_session_id,
        )
