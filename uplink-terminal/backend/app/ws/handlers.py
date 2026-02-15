"""SocketIO event handlers."""

from flask import request
from flask_socketio import emit

from ..extensions import socketio, db
from ..terminal.session import TerminalSession
from ..terminal.banners import WELCOME
from ..commands.parser import dispatch

# sid → TerminalSession
sessions = {}


@socketio.on("connect")
def on_connect():
    sid = request.sid
    sessions[sid] = TerminalSession(sid)
    ts = sessions[sid]

    emit("output", {"text": WELCOME})
    emit("prompt", {"text": ts.prompt})


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    sessions.pop(sid, None)


def _is_on_password_screen(ts):
    """Check if the terminal session is currently on a PASSWORD screen."""
    if not ts.is_connected or not ts.game_session_id:
        return False
    from ..models import Computer
    comp = Computer.query.filter_by(
        game_session_id=ts.game_session_id,
        ip=ts.current_computer_ip,
    ).first()
    if not comp:
        return False
    screen = comp.get_screen(ts.current_screen_index)
    return screen is not None and screen.screen_type == "PASSWORD"


@socketio.on("input")
def on_input(data):
    sid = request.sid
    ts = sessions.get(sid)
    if ts is None:
        return

    text = data.get("text", "").strip()
    if not text:
        emit("prompt", {"text": ts.prompt})
        return

    was_on_password = _is_on_password_screen(ts)

    result = dispatch(text, ts)
    if result:
        emit("output", {"text": result + "\n"})

    now_on_password = _is_on_password_screen(ts)

    # Emit password mode events
    if was_on_password and not now_on_password:
        emit("password_done")
    if now_on_password and not was_on_password:
        emit("password_prompt")

    emit("prompt", {"text": ts.prompt})
