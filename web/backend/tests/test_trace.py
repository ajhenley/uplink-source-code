"""Tests for Phase 5 — Trace engine, security engine, and game-over flow."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.computer import Computer
from app.models.vlocation import VLocation
from app.models.connection import Connection, ConnectionNode
from app.models.security import SecuritySystem
from app.game import constants as C
from app.game import trace_engine, security_engine


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _register_and_create_game(client):
    """Register a user, create a game, and return (headers, session_id, player_id)."""
    reg = await client.post("/api/auth/register", json={
        "username": "traceuser",
        "password": "pass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    game = await client.post("/api/game/new", json={
        "player_name": "Trace Player",
        "handle": "Traced",
    }, headers=headers)
    data = game.json()
    return headers, data["session"]["id"], data["player_id"]


async def _setup_connected_state(db, session_id, player_id, target_ip, num_bounce_nodes=3):
    """Create an active connection with bounce nodes, ready for trace testing."""
    conn = Connection(
        game_session_id=session_id,
        player_id=player_id,
        target_ip=target_ip,
        is_active=True,
        trace_progress=0.0,
        trace_active=False,
    )
    db.add(conn)
    await db.flush()

    # Create bounce nodes (positions 0..N-1)
    for i in range(num_bounce_nodes):
        node = ConnectionNode(
            connection_id=conn.id,
            position=i,
            ip=f"10.0.{i}.1",
            is_traced=False,
        )
        db.add(node)

    await db.commit()
    return conn


async def _find_computer_with_trace(db, session_id):
    """Find a computer with positive trace_speed."""
    computer = (await db.execute(
        select(Computer).where(
            Computer.game_session_id == session_id,
            Computer.trace_speed > 0,
        ).limit(1)
    )).scalar_one_or_none()
    return computer


# ── Trace engine tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trace_does_not_advance_without_activation(client, db_engine):
    """An active connection without trace_active should not be affected by tick_traces."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        # Look up the IP for this computer via VLocation
        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip)

        # Tick traces — nothing should happen since trace_active=False
        updates = await trace_engine.tick_traces(db, speed=1, session_id=session_id)
        await db.commit()

        assert len(updates) == 0
        await db.refresh(conn)
        assert conn.trace_progress == 0.0


@pytest.mark.asyncio
async def test_start_trace(client, db_engine):
    """start_trace should activate trace on a connection."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip)

        assert conn.trace_active is False

        await trace_engine.start_trace(db, conn, computer)
        await db.commit()

        await db.refresh(conn)
        assert conn.trace_active is True
        assert conn.trace_progress == 0.0


@pytest.mark.asyncio
async def test_trace_advances_on_tick(client, db_engine):
    """After starting a trace, tick_traces should advance progress."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip, num_bounce_nodes=2)

        # Start the trace
        await trace_engine.start_trace(db, conn, computer)
        await db.commit()

        # Tick once
        updates = await trace_engine.tick_traces(db, speed=1, session_id=session_id)
        await db.commit()

        assert len(updates) == 1
        assert updates[0]["progress"] > 0.0
        assert updates[0]["active"] is True

        await db.refresh(conn)
        assert conn.trace_progress > 0.0


@pytest.mark.asyncio
async def test_trace_completes_after_many_ticks(client, db_engine):
    """Trace should reach 1.0 and trigger game-over after enough ticks."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        # Use 1 bounce node for faster trace completion
        conn = await _setup_connected_state(db, session_id, player_id, loc.ip, num_bounce_nodes=1)

        await trace_engine.start_trace(db, conn, computer)
        await db.commit()

        # Tick many times with high speed to guarantee completion
        for _ in range(5000):
            await trace_engine.tick_traces(db, speed=8, session_id=session_id)

        await db.commit()
        await db.refresh(conn)
        assert conn.trace_progress >= 1.0

        # check_completed_traces should detect the game-over
        completions = await trace_engine.check_completed_traces(db, session_id)
        await db.commit()

        assert len(completions) >= 1
        assert completions[0]["reason"] == "traced"

        # Connection should be deactivated
        await db.refresh(conn)
        assert conn.is_active is False
        assert conn.trace_active is False


@pytest.mark.asyncio
async def test_trace_marks_nodes_as_traced(client, db_engine):
    """As trace progresses, ConnectionNodes should be marked is_traced from the end."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip, num_bounce_nodes=3)
        await trace_engine.start_trace(db, conn, computer)
        await db.commit()

        # Tick enough to get past 1/3 progress (one node traced)
        # Use high speed ticks; check in-memory progress (no db.refresh
        # which would reload the uncommitted DB value and reset it).
        for _ in range(2000):
            await trace_engine.tick_traces(db, speed=8, session_id=session_id)
            if conn.trace_progress >= 0.4:
                break

        await db.commit()

        assert conn.trace_progress >= 0.4, f"Progress only reached {conn.trace_progress}"

        # One more tick to get the update dict with traced_nodes
        updates = await trace_engine.tick_traces(db, speed=1, session_id=session_id)
        await db.commit()

        if updates:
            traced_nodes = updates[0]["traced_nodes"]
            # At >= 33% progress, at least 1 node should be traced
            assert len(traced_nodes) >= 1


@pytest.mark.asyncio
async def test_trace_speed_negative_never_traces(client, db_engine):
    """A computer with trace_speed <= 0 should never have its trace advance."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        # Find a computer with trace_speed = -1 (public access server)
        computer = (await db.execute(
            select(Computer).where(
                Computer.game_session_id == session_id,
                Computer.trace_speed <= 0,
            ).limit(1)
        )).scalar_one_or_none()

        if computer is None:
            pytest.skip("No computer with non-positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip)

        # Manually activate trace
        conn.trace_active = True
        conn.trace_progress = 0.0
        await db.commit()

        # Tick — should not advance
        updates = await trace_engine.tick_traces(db, speed=1, session_id=session_id)
        await db.commit()

        # Either no updates or progress remains 0
        await db.refresh(conn)
        assert conn.trace_progress == 0.0


@pytest.mark.asyncio
async def test_more_bounce_nodes_slows_trace(client, db_engine):
    """More bounce nodes should slow down trace per-tick increment."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        # Connection with 1 node
        conn1 = await _setup_connected_state(db, session_id, player_id, loc.ip, num_bounce_nodes=1)
        await trace_engine.start_trace(db, conn1, computer)
        await db.commit()

        await trace_engine.tick_traces(db, speed=1, session_id=session_id)
        await db.commit()
        await db.refresh(conn1)
        progress_1_node = conn1.trace_progress

        # Deactivate first connection
        conn1.is_active = False
        conn1.trace_active = False
        await db.commit()

        # Connection with 5 nodes
        conn5 = await _setup_connected_state(db, session_id, player_id, loc.ip, num_bounce_nodes=5)
        await trace_engine.start_trace(db, conn5, computer)
        await db.commit()

        await trace_engine.tick_traces(db, speed=1, session_id=session_id)
        await db.commit()
        await db.refresh(conn5)
        progress_5_nodes = conn5.trace_progress

        # 1-node trace should advance faster than 5-node trace
        assert progress_1_node > progress_5_nodes


@pytest.mark.asyncio
async def test_start_trace_idempotent(client, db_engine):
    """Calling start_trace twice should not reset progress."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip, num_bounce_nodes=2)

        await trace_engine.start_trace(db, conn, computer)
        await db.commit()

        # Tick to advance progress
        for _ in range(10):
            await trace_engine.tick_traces(db, speed=1, session_id=session_id)
        await db.commit()

        await db.refresh(conn)
        progress_before = conn.trace_progress
        assert progress_before > 0

        # Call start_trace again — should NOT reset
        await trace_engine.start_trace(db, conn, computer)
        await db.commit()

        await db.refresh(conn)
        assert conn.trace_progress == progress_before


# ── Security engine tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_security_breach_starts_trace(client, db_engine):
    """A computer with an active security monitor should trigger a trace."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip)

        # Add an active security monitor to this computer
        monitor = SecuritySystem(
            computer_id=computer.id,
            security_type=3,  # MONITOR
            level=1,
            is_active=True,
        )
        db.add(monitor)
        await db.commit()

        # Check security — should start a trace
        events = await security_engine.check_security_breaches(db, session_id)
        await db.commit()

        assert len(events) == 1
        assert events[0]["type"] == "trace_started"
        assert events[0]["target_ip"] == loc.ip

        # Connection should now have an active trace
        await db.refresh(conn)
        assert conn.trace_active is True


@pytest.mark.asyncio
async def test_security_no_monitor_no_trace(client, db_engine):
    """A computer without a security monitor should not trigger a trace."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip)

        # Remove any existing security monitors for this computer
        existing = (await db.execute(
            select(SecuritySystem).where(
                SecuritySystem.computer_id == computer.id,
                SecuritySystem.security_type == 3,
            )
        )).scalars().all()
        for sec in existing:
            sec.is_active = False
        await db.commit()

        # Check security — should find nothing
        events = await security_engine.check_security_breaches(db, session_id)
        await db.commit()

        assert len(events) == 0

        await db.refresh(conn)
        assert conn.trace_active is False


@pytest.mark.asyncio
async def test_security_skips_already_tracing(client, db_engine):
    """check_security_breaches should not start a second trace on a connection already being traced."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip)

        # Add a security monitor
        monitor = SecuritySystem(
            computer_id=computer.id,
            security_type=3,
            level=1,
            is_active=True,
        )
        db.add(monitor)
        await db.commit()

        # Manually start a trace
        conn.trace_active = True
        conn.trace_progress = 0.3
        await db.commit()

        # Check security — should skip because already tracing
        events = await security_engine.check_security_breaches(db, session_id)
        await db.commit()

        assert len(events) == 0

        # Progress should not have been reset
        await db.refresh(conn)
        assert conn.trace_progress == 0.3


@pytest.mark.asyncio
async def test_security_inactive_monitor_ignored(client, db_engine):
    """An inactive security monitor (is_active=False) should not trigger a trace."""
    headers, session_id, player_id = await _register_and_create_game(client)

    async_sess = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_sess() as db:
        computer = await _find_computer_with_trace(db, session_id)
        if computer is None:
            pytest.skip("No computer with positive trace_speed found")

        loc = (await db.execute(
            select(VLocation).where(VLocation.computer_id == computer.id)
        )).scalar_one()

        conn = await _setup_connected_state(db, session_id, player_id, loc.ip)

        # Remove existing active monitors, add inactive one
        existing = (await db.execute(
            select(SecuritySystem).where(SecuritySystem.computer_id == computer.id)
        )).scalars().all()
        for sec in existing:
            sec.is_active = False
        await db.flush()

        inactive_monitor = SecuritySystem(
            computer_id=computer.id,
            security_type=3,
            level=1,
            is_active=False,
        )
        db.add(inactive_monitor)
        await db.commit()

        events = await security_engine.check_security_breaches(db, session_id)
        await db.commit()

        assert len(events) == 0
        await db.refresh(conn)
        assert conn.trace_active is False
