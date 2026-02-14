"""Trace engine -- advances traces backward through bounce chains.

When a player connects to a computer with a security monitor, a trace
begins.  The trace progress advances from 0.0 to 1.0 across the entire
bounce chain.  When it reaches 1.0, the player has been fully traced and
the game is over (arrested).

Trace speed calculation mirrors the original Uplink C++ implementation:
- ``trace_speed`` on the Computer is "seconds per link" (higher = slower trace).
- Total trace time = trace_speed * account_modifier * num_bounce_nodes seconds.
- Per-tick increment = 1.0 / (trace_speed * modifier * num_nodes * TICK_RATE).
- A ``trace_speed`` of -1 means the computer never traces.
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection, ConnectionNode
from app.models.computer import Computer
from app.models.vlocation import VLocation
from app.game import constants as C

log = logging.getLogger(__name__)

# The game loop tick rate (ticks per second).
TICK_RATE = 5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def tick_traces(
    db: AsyncSession, speed: int, session_id: str
) -> list[dict]:
    """Advance all active traces for *session_id* by one tick (scaled by *speed*).

    Returns a list of trace-update dicts suitable for WebSocket broadcast.
    Each dict contains: session_id, progress, active, traced_nodes.
    """
    connections = (
        await db.execute(
            select(Connection).where(
                Connection.game_session_id == session_id,
                Connection.is_active == True,  # noqa: E712
                Connection.trace_active == True,  # noqa: E712
            )
        )
    ).scalars().all()

    if not connections:
        return []

    updates: list[dict] = []

    for conn in connections:
        # Resolve the target computer via IP -> VLocation -> Computer
        computer = await _resolve_computer(db, session_id, conn.target_ip)
        if computer is None:
            continue

        # A trace_speed of -1 (or <= 0) means this computer never traces.
        if computer.trace_speed <= 0:
            continue

        # Count bounce nodes for this connection
        nodes = (
            await db.execute(
                select(ConnectionNode)
                .where(ConnectionNode.connection_id == conn.id)
                .order_by(ConnectionNode.position.desc())
            )
        ).scalars().all()

        num_nodes = len(nodes)
        if num_nodes == 0:
            # No bounce nodes -- trace completes instantly
            num_nodes = 1

        # Apply account modifier.  For MVP we assume "no account" (fastest
        # trace, i.e. the player is most vulnerable).
        modifier = C.TRACESPEED_MODIFIER_NOACCOUNT  # 0.1

        # Effective trace time (in seconds) across the entire chain:
        # trace_speed * modifier * num_nodes
        effective_time = computer.trace_speed * modifier * num_nodes

        if effective_time <= 0:
            # Edge case: if somehow zero, complete immediately
            conn.trace_progress = 1.0
        else:
            # Per-tick increment
            increment = (1.0 / (effective_time * TICK_RATE)) * speed
            conn.trace_progress = min(1.0, conn.trace_progress + increment)

        # Update which nodes have been traced.
        # Nodes are ordered highest-position-first (the end of the chain,
        # closest to the target).  As trace_progress increases, more nodes
        # from the end get marked as traced.
        _update_traced_nodes(nodes, num_nodes, conn.trace_progress)

        traced_ips = [n.ip for n in nodes if n.is_traced]

        updates.append({
            "session_id": session_id,
            "progress": round(conn.trace_progress, 4),
            "active": conn.trace_active,
            "traced_nodes": traced_ips,
        })

    return updates


async def start_trace(
    db: AsyncSession, connection: Connection, computer: Computer
) -> None:
    """Activate a trace on *connection*.

    Called by the security engine when a security monitor detects the player.
    """
    if connection.trace_active:
        return  # already tracing
    connection.trace_active = True
    connection.trace_progress = 0.0
    log.info(
        "Trace started on connection %d (session=%s, target=%s, trace_speed=%.1f)",
        connection.id,
        connection.game_session_id,
        connection.target_ip,
        computer.trace_speed,
    )


async def check_completed_traces(
    db: AsyncSession, session_id: str
) -> list[dict]:
    """Check for any fully-traced connections and return game-over dicts.

    A trace is complete when ``trace_progress >= 1.0``.  When that happens
    the connection is deactivated and a game-over event is emitted.
    """
    connections = (
        await db.execute(
            select(Connection).where(
                Connection.game_session_id == session_id,
                Connection.is_active == True,  # noqa: E712
                Connection.trace_active == True,  # noqa: E712
            )
        )
    ).scalars().all()

    completions: list[dict] = []

    for conn in connections:
        if conn.trace_progress >= 1.0:
            conn.is_active = False
            conn.trace_active = False
            log.warning(
                "Trace COMPLETE -- player traced! connection=%d session=%s",
                conn.id,
                conn.game_session_id,
            )
            completions.append({
                "session_id": session_id,
                "connection_id": conn.id,
                "reason": "traced",
            })

    return completions


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


def _update_traced_nodes(
    nodes: list[ConnectionNode],
    num_nodes: int,
    trace_progress: float,
) -> None:
    """Mark ConnectionNodes as traced based on overall trace progress.

    Nodes are expected to be ordered by position descending (highest
    position first -- the end of the bounce chain nearest the target).
    The trace works backward from the target toward the player, so the
    highest-position nodes are traced first.
    """
    if num_nodes == 0:
        return

    # How many nodes have been fully reached?
    nodes_traced_count = int(trace_progress * num_nodes)
    # If progress is 1.0, all nodes are traced
    if trace_progress >= 1.0:
        nodes_traced_count = num_nodes

    for i, node in enumerate(nodes):
        # nodes[0] is highest position (traced first)
        node.is_traced = i < nodes_traced_count
