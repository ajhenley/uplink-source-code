"""Security engine -- breach detection and trace initiation."""
import logging

from app.models.connection import Connection
from app.models.computer import Computer
from app.models.security import SecuritySystem
from app.models.vlocation import VLocation
from app.game import trace_engine

log = logging.getLogger(__name__)

SECURITY_TYPE_MONITOR = 3


def check_security_breaches(session_id):
    """Check active connections against security monitors."""
    connections = Connection.query.filter(
        Connection.game_session_id == session_id,
        Connection.is_active == True,
    ).all()

    if not connections:
        return []

    events = []

    for conn in connections:
        if conn.trace_active:
            continue

        computer = _resolve_computer(session_id, conn.target_ip)
        if computer is None or computer.trace_speed <= 0:
            continue

        if not _has_active_monitor(computer.id):
            continue

        trace_engine.start_trace(conn, computer)

        events.append({
            "type": "trace_started",
            "session_id": session_id,
            "target_ip": conn.target_ip,
            "computer_name": computer.name,
        })

    return events


def _resolve_computer(game_session_id, ip):
    if ip is None:
        return None
    loc = VLocation.query.filter_by(
        game_session_id=game_session_id, ip=ip
    ).first()
    if loc is None or loc.computer_id is None:
        return None
    return Computer.query.get(loc.computer_id)


def _has_active_monitor(computer_id):
    return SecuritySystem.query.filter(
        SecuritySystem.computer_id == computer_id,
        SecuritySystem.security_type == SECURITY_TYPE_MONITOR,
        SecuritySystem.is_active == True,
    ).first() is not None
