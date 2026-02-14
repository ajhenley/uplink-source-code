"""Game session management routes."""
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models.game_session import GameSession
from app.models.player import Player
from app.models.gateway import Gateway
from app.models.connection import Connection, ConnectionNode
from app.models.message import Message
from app.models.mission import Mission
from app.models.running_task import RunningTask
from app.models.computer import Computer, ComputerScreenDef
from app.models.vlocation import VLocation
from app.models.bank_account import BankAccount
from app.models.data_file import DataFile
from app.models.access_log import AccessLog
from app.models.security import SecuritySystem
from app.models.company import Company
from app.models.person import Person
from app.game import world_generator

game_bp = Blueprint("game", __name__)


@game_bp.route("/sessions")
@login_required
def sessions():
    user_sessions = GameSession.query.filter_by(
        user_id=current_user.id
    ).order_by(GameSession.updated_at.desc()).all()
    return render_template("sessions.html", sessions=user_sessions)


@game_bp.route("/new", methods=["POST"])
@login_required
def new_game():
    session_name = request.form.get("session_name", "").strip()
    agent_handle = request.form.get("agent_handle", "").strip()
    try:
        city_index = int(request.form.get("city_index", 0))
    except (ValueError, TypeError):
        city_index = 0
    city_index = max(0, min(7, city_index))

    if not session_name:
        session_name = f"Agent {agent_handle or current_user.username}"

    if not agent_handle:
        flash("Agent handle is required.", "error")
        return redirect(url_for("game.sessions"))

    game_session = GameSession(
        user_id=current_user.id,
        name=session_name,
    )
    db.session.add(game_session)
    db.session.flush()

    world_generator.generate_world(
        game_session.id,
        player_name=current_user.username,
        player_handle=agent_handle,
        city_index=city_index,
    )
    db.session.commit()

    return redirect(url_for("game.play", session_id=game_session.id))


@game_bp.route("/play/<session_id>")
@login_required
def play(session_id):
    game_session = GameSession.query.get_or_404(session_id)
    if game_session.user_id != current_user.id:
        abort(403)
    return render_template("game.html", session_id=session_id)


@game_bp.route("/delete/<session_id>", methods=["POST"])
@login_required
def delete_game(session_id):
    game_session = GameSession.query.get_or_404(session_id)
    if game_session.user_id != current_user.id:
        abort(403)

    # Delete all related data in dependency order.
    # Connection nodes reference connections, so delete them first.
    connection_ids = [
        c.id for c in Connection.query.filter_by(game_session_id=session_id).all()
    ]
    if connection_ids:
        ConnectionNode.query.filter(
            ConnectionNode.connection_id.in_(connection_ids)
        ).delete(synchronize_session=False)

    Connection.query.filter_by(game_session_id=session_id).delete()
    RunningTask.query.filter_by(game_session_id=session_id).delete()
    Message.query.filter_by(game_session_id=session_id).delete()
    Mission.query.filter_by(game_session_id=session_id).delete()
    BankAccount.query.filter_by(game_session_id=session_id).delete()

    # Computer-dependent tables: screen defs, data files, access logs, security
    computer_ids = [
        c.id for c in Computer.query.filter_by(game_session_id=session_id).all()
    ]
    if computer_ids:
        ComputerScreenDef.query.filter(
            ComputerScreenDef.computer_id.in_(computer_ids)
        ).delete(synchronize_session=False)
        DataFile.query.filter(
            DataFile.computer_id.in_(computer_ids)
        ).delete(synchronize_session=False)
        AccessLog.query.filter(
            AccessLog.computer_id.in_(computer_ids)
        ).delete(synchronize_session=False)
        SecuritySystem.query.filter(
            SecuritySystem.computer_id.in_(computer_ids)
        ).delete(synchronize_session=False)

    VLocation.query.filter_by(game_session_id=session_id).delete()
    Player.query.filter_by(game_session_id=session_id).delete()
    Gateway.query.filter_by(game_session_id=session_id).delete()
    Computer.query.filter_by(game_session_id=session_id).delete()
    Company.query.filter_by(game_session_id=session_id).delete()
    Person.query.filter_by(game_session_id=session_id).delete()

    db.session.delete(game_session)
    db.session.commit()

    flash("Game session deleted.", "info")
    return redirect(url_for("game.sessions"))
