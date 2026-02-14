"""Trace engine -- advances traces backward through bounce chains."""
import logging

from app.extensions import db
from app.models.connection import Connection, ConnectionNode
from app.models.computer import Computer
from app.models.vlocation import VLocation
from app.game import constants as C

log = logging.getLogger(__name__)

TICK_RATE = 5


def tick_traces(speed, session_id):
    """Advance all active traces for session_id by one tick."""
    connections = Connection.query.filter(
        Connection.game_session_id == session_id,
        Connection.is_active == True,
        Connection.trace_active == True,
    ).all()

    if not connections:
        return []

    updates = []

    for conn in connections:
        computer = _resolve_computer(session_id, conn.target_ip)
        if computer is None or computer.trace_speed <= 0:
            continue

        nodes = ConnectionNode.query.filter_by(
            connection_id=conn.id
        ).order_by(ConnectionNode.position.desc()).all()

        num_nodes = max(1, len(nodes))
        modifier = C.TRACESPEED_MODIFIER_NOACCOUNT

        effective_time = computer.trace_speed * modifier * num_nodes

        if effective_time <= 0:
            conn.trace_progress = 1.0
        else:
            increment = (1.0 / (effective_time * TICK_RATE)) * speed
            conn.trace_progress = min(1.0, conn.trace_progress + increment)

        _update_traced_nodes(nodes, num_nodes, conn.trace_progress)

        traced_ips = [n.ip for n in nodes if n.is_traced]

        updates.append({
            "session_id": session_id,
            "progress": round(conn.trace_progress, 4),
            "active": conn.trace_active,
            "traced_nodes": traced_ips,
        })

    return updates


def start_trace(connection, computer):
    """Activate a trace on connection."""
    if connection.trace_active:
        return
    connection.trace_active = True
    connection.trace_progress = 0.0
    log.info("Trace started on connection %d (session=%s)", connection.id, connection.game_session_id)


def check_completed_traces(session_id):
    """Check for fully-traced connections."""
    connections = Connection.query.filter(
        Connection.game_session_id == session_id,
        Connection.is_active == True,
        Connection.trace_active == True,
    ).all()

    completions = []

    for conn in connections:
        if conn.trace_progress >= 1.0:
            conn.is_active = False
            conn.trace_active = False
            log.warning("Trace COMPLETE -- player traced! connection=%d session=%s", conn.id, conn.game_session_id)
            completions.append({
                "session_id": session_id,
                "connection_id": conn.id,
                "reason": "traced",
            })

    return completions


def _resolve_computer(game_session_id, ip):
    if ip is None:
        return None
    loc = VLocation.query.filter_by(
        game_session_id=game_session_id, ip=ip
    ).first()
    if loc is None or loc.computer_id is None:
        return None
    return Computer.query.get(loc.computer_id)


def _update_traced_nodes(nodes, num_nodes, trace_progress):
    if num_nodes == 0:
        return
    nodes_traced_count = int(trace_progress * num_nodes)
    if trace_progress >= 1.0:
        nodes_traced_count = num_nodes
    for i, node in enumerate(nodes):
        node.is_traced = i < nodes_traced_count
