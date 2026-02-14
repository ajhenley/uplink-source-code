"""Security engine -- breach detection and consequence scheduling.

Periodically checks active connections against the target computer's
security systems.  If a computer has an active security monitor
(security_type=3) and the player is connected, a trace is initiated
via the trace engine.

In the original Uplink, the security monitor is one of several security
systems (proxy, firewall, monitor).  For the MVP we only handle the
monitor -> trace path.
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.models.computer import Computer
from app.models.security import SecuritySystem
from app.models.vlocation import VLocation
from app.game import trace_engine

log = logging.getLogger(__name__)

# Security system type constants (from the original Uplink)
SECURITY_TYPE_MONITOR = 3


async def check_security_breaches(
    db: AsyncSession, session_id: str
) -> list[dict]:
    """Check all active connections for *session_id* against security monitors.

    For each connection where the target computer has an active security
    monitor and no trace is already running, start a trace.

    Returns a list of event dicts describing what happened.
    """
    connections = (
        await db.execute(
            select(Connection).where(
                Connection.game_session_id == session_id,
                Connection.is_active == True,  # noqa: E712
            )
        )
    ).scalars().all()

    if not connections:
        return []

    events: list[dict] = []

    for conn in connections:
        # Skip connections that already have an active trace
        if conn.trace_active:
            continue

        # Resolve the target computer
        computer = await _resolve_computer(db, session_id, conn.target_ip)
        if computer is None:
            continue

        # A trace_speed of -1 means this computer never traces
        if computer.trace_speed <= 0:
            continue

        # Check if the computer has an active security monitor
        has_monitor = await _has_active_monitor(db, computer.id)
        if not has_monitor:
            continue

        # Start the trace
        await trace_engine.start_trace(db, conn, computer)

        events.append({
            "type": "trace_started",
            "session_id": session_id,
            "target_ip": conn.target_ip,
            "computer_name": computer.name,
        })
        log.info(
            "Security breach detected: trace started on %s (%s) for session %s",
            computer.name,
            conn.target_ip,
            session_id,
        )

    return events


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _resolve_computer(
    db: AsyncSession, game_session_id: str, ip: str | None
) -> Computer | None:
    """Find the Computer behind *ip* in the given game session."""
    if ip is None:
        return None
    loc = (
        await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == game_session_id,
                VLocation.ip == ip,
            )
        )
    ).scalar_one_or_none()
    if loc is None or loc.computer_id is None:
        return None
    return (
        await db.execute(select(Computer).where(Computer.id == loc.computer_id))
    ).scalar_one_or_none()


async def _has_active_monitor(db: AsyncSession, computer_id: int) -> bool:
    """Return True if the computer has at least one active security monitor."""
    monitor = (
        await db.execute(
            select(SecuritySystem.id).where(
                SecuritySystem.computer_id == computer_id,
                SecuritySystem.security_type == SECURITY_TYPE_MONITOR,
                SecuritySystem.is_active == True,  # noqa: E712
            ).limit(1)
        )
    ).scalar_one_or_none()
    return monitor is not None
