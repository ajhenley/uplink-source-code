"""REST API endpoints for game state queries."""
from flask import Blueprint, jsonify, abort, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models.game_session import GameSession
from app.models.player import Player
from app.models.gateway import Gateway
from app.models.message import Message
from app.models.mission import Mission
from app.models.running_task import RunningTask
from app.models.connection import Connection, ConnectionNode
from app.models.vlocation import VLocation
from app.models.data_file import DataFile
from app.models.news import NewsArticle
from app.models.stock_market import StockEntry
from app.game import mission_engine

api_bp = Blueprint("api", __name__)


def _verify_session(session_id):
    """Load a GameSession and verify it belongs to the current user."""
    game_session = GameSession.query.get(session_id)
    if game_session is None:
        abort(404, description="Game session not found")
    if game_session.user_id != current_user.id:
        abort(403, description="Access denied")
    return game_session


@api_bp.route("/session/<session_id>/state")
@login_required
def session_state(session_id):
    game_session = _verify_session(session_id)

    player = Player.query.filter_by(game_session_id=session_id).first()
    if player is None:
        abort(404, description="Player not found for this session")

    gateway = Gateway.query.get(player.gateway_id) if player.gateway_id else None

    messages = Message.query.filter_by(
        game_session_id=session_id, player_id=player.id
    ).order_by(Message.id.desc()).all()

    active_tasks = RunningTask.query.filter_by(
        game_session_id=session_id, player_id=player.id, is_active=True
    ).all()

    connection = Connection.query.filter_by(
        game_session_id=session_id, player_id=player.id
    ).first()

    bounce_chain = []
    if connection is not None:
        nodes = ConnectionNode.query.filter_by(
            connection_id=connection.id
        ).order_by(ConnectionNode.position).all()
        bounce_chain = [{"position": n.position, "ip": n.ip} for n in nodes]

    # Locations for map
    locations = VLocation.query.filter_by(
        game_session_id=session_id
    ).all()

    # Software installed on gateway (found via player's localhost_ip → VLocation → Computer)
    software = []
    if player.localhost_ip:
        gw_loc = VLocation.query.filter_by(
            game_session_id=session_id, ip=player.localhost_ip
        ).first()
        if gw_loc and gw_loc.computer_id:
            gateway_files = DataFile.query.filter_by(
                computer_id=gw_loc.computer_id
            ).all()
            software = [
                {"name": f.filename, "version": int(f.data) if f.data and f.data.isdigit() else 1}
                for f in gateway_files if f.softwaretype and f.softwaretype > 0
            ]

    # Missions
    available_missions = mission_engine.get_available_missions(
        session_id, player_rating=player.uplink_rating
    )
    active_missions_list = Mission.query.filter_by(
        game_session_id=session_id, is_accepted=True, is_completed=False
    ).all()

    return jsonify({
        "session_id": session_id,
        "ticks": game_session.game_time_ticks,
        "speed": 1,
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
        "gateway": {
            "id": gateway.id,
            "name": gateway.name,
            "cpu_speed": gateway.cpu_speed,
            "modem_speed": gateway.modem_speed,
            "memory_size": gateway.memory_size,
            "has_self_destruct": gateway.has_self_destruct,
            "has_motion_sensor": gateway.has_motion_sensor,
        } if gateway else None,
        "messages": [
            {
                "id": m.id,
                "from_name": m.from_name,
                "subject": m.subject,
                "body": m.body,
                "is_read": m.is_read,
                "created_at_tick": m.created_at_tick,
            }
            for m in messages
        ],
        "tasks": [
            {
                "id": t.id,
                "tool_name": t.tool_name,
                "tool_version": t.tool_version,
                "target_ip": t.target_ip,
                "progress": t.progress,
                "ticks_remaining": t.ticks_remaining,
                "is_active": t.is_active,
            }
            for t in active_tasks
        ],
        "connection": {
            "isConnected": connection.is_active if connection else False,
            "targetIp": connection.target_ip if connection else None,
            "traceProgress": connection.trace_progress if connection else 0,
            "traceActive": connection.trace_active if connection else False,
            "bounceChain": bounce_chain,
        },
        "locations": [
            {
                "id": loc.id,
                "ip": loc.ip,
                "x": loc.x,
                "y": loc.y,
                "listed": loc.listed,
            }
            for loc in locations
        ],
        "software": software,
        "missions": {
            "available": available_missions,
            "active": [
                {
                    "id": m.id,
                    "type": m.mission_type,
                    "description": m.description,
                    "payment": m.payment,
                    "target_ip": m.target_computer_ip,
                    "is_completed": m.is_completed,
                }
                for m in active_missions_list
            ],
        },
    })


@api_bp.route("/session/<session_id>/messages")
@login_required
def session_messages(session_id):
    _verify_session(session_id)

    player = Player.query.filter_by(game_session_id=session_id).first()
    if player is None:
        abort(404, description="Player not found for this session")

    messages = Message.query.filter_by(
        game_session_id=session_id, player_id=player.id
    ).order_by(Message.id.desc()).all()

    return jsonify({
        "messages": [
            {
                "id": m.id,
                "from_name": m.from_name,
                "subject": m.subject,
                "body": m.body,
                "is_read": m.is_read,
                "created_at_tick": m.created_at_tick,
            }
            for m in messages
        ]
    })


@api_bp.route("/session/<session_id>/missions")
@login_required
def session_missions(session_id):
    _verify_session(session_id)

    player = Player.query.filter_by(game_session_id=session_id).first()
    if player is None:
        abort(404, description="Player not found for this session")

    missions = mission_engine.get_available_missions(
        session_id, player_rating=player.uplink_rating
    )

    return jsonify({"missions": missions})


@api_bp.route("/session/<session_id>/map")
@login_required
def session_map(session_id):
    _verify_session(session_id)

    locations = VLocation.query.filter_by(
        game_session_id=session_id
    ).all()

    return jsonify({
        "locations": [
            {
                "id": loc.id,
                "ip": loc.ip,
                "x": loc.x,
                "y": loc.y,
                "listed": loc.listed,
                "computer_id": loc.computer_id,
            }
            for loc in locations
        ]
    })


@api_bp.route("/session/<session_id>/news")
@login_required
def session_news(session_id):
    _verify_session(session_id)

    articles = NewsArticle.query.filter_by(
        game_session_id=session_id
    ).order_by(NewsArticle.created_at_tick.desc()).limit(30).all()

    return jsonify({
        "articles": [
            {
                "id": a.id,
                "headline": a.headline,
                "body": a.body,
                "category": a.category,
                "created_at_tick": a.created_at_tick,
            }
            for a in articles
        ]
    })


@api_bp.route("/session/<session_id>/stocks")
@login_required
def session_stocks(session_id):
    _verify_session(session_id)

    stocks = StockEntry.query.filter_by(game_session_id=session_id).all()
    player = Player.query.filter_by(game_session_id=session_id).first()

    holdings = {}
    if player:
        from app.models.stock_market import StockHolding
        for h in StockHolding.query.filter_by(
            game_session_id=session_id, player_id=player.id
        ).all():
            holdings[h.company_name] = {"shares": h.shares, "purchase_price": h.purchase_price}

    return jsonify({
        "stocks": [
            {
                "company_name": s.company_name,
                "current_price": s.current_price,
                "previous_price": s.previous_price,
                "change": s.current_price - s.previous_price,
                "player_shares": holdings.get(s.company_name, {}).get("shares", 0),
            }
            for s in stocks
        ]
    })


@api_bp.route("/session/<session_id>/rankings")
@login_required
def session_rankings(session_id):
    _verify_session(session_id)

    try:
        from app.game import npc_engine
        rankings = npc_engine.get_agent_rankings(session_id)
    except (ImportError, Exception):
        # Fallback: just return player
        player = Player.query.filter_by(game_session_id=session_id).first()
        rankings = [{
            "name": player.handle if player else "Unknown",
            "rating": player.uplink_rating if player else 0,
            "is_player": True,
        }] if player else []

    return jsonify({"rankings": rankings})


@api_bp.route("/session/<session_id>/store/hardware")
@login_required
def store_hardware(session_id):
    _verify_session(session_id)
    try:
        from app.game import store_engine
        return jsonify({"catalog": store_engine.get_hardware_catalog()})
    except ImportError:
        return jsonify({"catalog": []})


@api_bp.route("/session/<session_id>/store/software")
@login_required
def store_software(session_id):
    _verify_session(session_id)
    try:
        from app.game import store_engine
        return jsonify({"catalog": store_engine.get_software_catalog()})
    except ImportError:
        return jsonify({"catalog": []})


@api_bp.route("/session/<session_id>/save", methods=["POST"])
@login_required
def save_game(session_id):
    """Explicitly save the current game state (snapshot the tick counter)."""
    game_session = _verify_session(session_id)
    game_session.last_saved_at = game_session.game_time_ticks
    db.session.commit()
    return jsonify({"success": True, "saved_at": game_session.last_saved_at})
