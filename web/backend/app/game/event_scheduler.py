"""Event scheduler -- processes delayed consequence events.

After a trace completes or a security breach is detected, consequences
are scheduled (as ScheduledEvent records in the DB) and processed
when their trigger time arrives.

Event types:
- WARNING: Player receives a threatening message from the company
- FINE: Player loses credits
- ARREST: Game over -- gateway seized
- MISSION_GENERATE: Generate new BBS missions periodically

Timeline from the original game:
- trace_complete -> immediate WARNING message
- trace_complete -> after TIME_LEGALACTION (3 hours game time): FINE or ARREST
"""
import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduled_event import ScheduledEvent
from app.models.message import Message
from app.models.player import Player
from app.models.game_session import GameSession
from app.game import constants as C

log = logging.getLogger(__name__)

# Game time conversion: 1 game-minute = 5 ticks at speed=1
# (TICK_RATE=5, so 1 real second = 5 ticks = 1 game minute at normal speed)
TICKS_PER_GAME_MINUTE = 5

# Convert time constants from game-minutes to ticks
TIME_LEGALACTION_TICKS = C.TIME_LEGALACTION * TICKS_PER_GAME_MINUTE  # 180 * 5 = 900
FREQUENCY_GENERATENEWMISSION_TICKS = C.FREQUENCY_GENERATENEWMISSION * TICKS_PER_GAME_MINUTE

# Fine amount for traced hack
DEFAULT_FINE_AMOUNT = 3000

# Computers with hack_difficulty above this threshold trigger arrest instead of fine
HIGH_SECURITY_DIFFICULTY_THRESHOLD = 200


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def schedule_event(
    db: AsyncSession,
    session_id: str,
    event_type: str,
    trigger_tick: int,
    data: dict | None = None,
) -> ScheduledEvent:
    """Create a ScheduledEvent record in the database."""
    event = ScheduledEvent(
        game_session_id=session_id,
        event_type=event_type,
        trigger_tick=trigger_tick,
        data=json.dumps(data or {}),
        is_processed=False,
    )
    db.add(event)
    await db.flush()
    log.info(
        "Scheduled event: type=%s trigger_tick=%d session=%s",
        event_type, trigger_tick, session_id,
    )
    return event


async def process_events(
    db: AsyncSession,
    session_id: str,
    current_tick: int,
) -> list[dict]:
    """Process all due events for *session_id*, returning messages to broadcast.

    Events are due when trigger_tick <= current_tick and not yet processed.
    """
    events = (
        await db.execute(
            select(ScheduledEvent).where(
                ScheduledEvent.game_session_id == session_id,
                ScheduledEvent.trigger_tick <= current_tick,
                ScheduledEvent.is_processed == False,  # noqa: E712
            ).order_by(ScheduledEvent.trigger_tick)
        )
    ).scalars().all()

    if not events:
        return []

    # Load the player for this session
    player = (
        await db.execute(
            select(Player).where(Player.game_session_id == session_id)
        )
    ).scalar_one_or_none()

    messages: list[dict] = []

    for event in events:
        event.is_processed = True
        event_data = json.loads(event.data or "{}")

        if event.event_type == "warning":
            result = await _process_warning(db, session_id, player, event_data, current_tick)
            if result:
                messages.append(result)

        elif event.event_type == "fine":
            result = await _process_fine(db, session_id, player, event_data, current_tick)
            if result:
                messages.append(result)

        elif event.event_type == "arrest":
            result = await _process_arrest(db, session_id, player, event_data)
            if result:
                messages.append(result)

        elif event.event_type == "mission_generate":
            result = await _process_mission_generate(db, session_id, player, event_data, current_tick)
            if result:
                messages.append(result)

    return messages


async def schedule_trace_consequences(
    db: AsyncSession,
    session_id: str,
    computer_name: str,
    current_tick: int = 0,
    hack_difficulty: float = 0.0,
) -> list[ScheduledEvent]:
    """Schedule consequence events after a trace completion.

    - Immediately schedules a WARNING event (trigger at current_tick)
    - Schedules a FINE or ARREST event at current_tick + TIME_LEGALACTION_TICKS
      (ARREST for high-security computers, FINE otherwise)
    """
    events: list[ScheduledEvent] = []

    # Immediate warning
    warning = await schedule_event(
        db, session_id, "warning",
        trigger_tick=current_tick,
        data={"computer_name": computer_name},
    )
    events.append(warning)

    # Delayed consequence: arrest for high-security, fine otherwise
    if hack_difficulty >= HIGH_SECURITY_DIFFICULTY_THRESHOLD:
        consequence = await schedule_event(
            db, session_id, "arrest",
            trigger_tick=current_tick + TIME_LEGALACTION_TICKS,
            data={"computer_name": computer_name},
        )
    else:
        consequence = await schedule_event(
            db, session_id, "fine",
            trigger_tick=current_tick + TIME_LEGALACTION_TICKS,
            data={
                "computer_name": computer_name,
                "amount": DEFAULT_FINE_AMOUNT,
            },
        )
    events.append(consequence)

    return events


# ---------------------------------------------------------------------------
# Event processors
# ---------------------------------------------------------------------------


async def _process_warning(
    db: AsyncSession,
    session_id: str,
    player: Player | None,
    data: dict,
    current_tick: int,
) -> dict | None:
    """Create a warning message for the player."""
    if player is None:
        return None

    computer_name = data.get("computer_name", "Unknown System")

    msg = Message(
        game_session_id=session_id,
        player_id=player.id,
        from_name="Federal Investigation Bureau",
        subject=f"Security Alert: Unauthorized access to {computer_name}",
        body=(
            f"Agent,\n\n"
            f"Our records indicate that you were involved in unauthorized "
            f"access to {computer_name}.\n\n"
            f"This is a formal warning. Further illegal activity will result "
            f"in fines or arrest.\n\n"
            f"- Federal Investigation Bureau"
        ),
        created_at_tick=current_tick,
    )
    db.add(msg)

    return {
        "type": "message_received",
        "session_id": session_id,
        "subject": msg.subject,
    }


async def _process_fine(
    db: AsyncSession,
    session_id: str,
    player: Player | None,
    data: dict,
    current_tick: int,
) -> dict | None:
    """Deduct credits from the player and send a message."""
    if player is None:
        return None

    computer_name = data.get("computer_name", "Unknown System")
    amount = data.get("amount", DEFAULT_FINE_AMOUNT)

    player.balance = max(0, player.balance - amount)

    msg = Message(
        game_session_id=session_id,
        player_id=player.id,
        from_name="Federal Investigation Bureau",
        subject=f"Fine: {amount}c deducted from your account",
        body=(
            f"Agent,\n\n"
            f"Following your unauthorized access to {computer_name}, "
            f"a fine of {amount}c has been deducted from your account.\n\n"
            f"Your current balance is {player.balance}c.\n\n"
            f"Further violations will result in more severe penalties.\n\n"
            f"- Federal Investigation Bureau"
        ),
        created_at_tick=current_tick,
    )
    db.add(msg)

    return {
        "type": "balance_changed",
        "session_id": session_id,
        "balance": player.balance,
        "fine": amount,
    }


async def _process_arrest(
    db: AsyncSession,
    session_id: str,
    player: Player | None,
    data: dict,
) -> dict | None:
    """Game over -- mark session as inactive."""
    session = await db.get(GameSession, session_id)
    if session is None:
        return None

    session.is_active = False

    computer_name = data.get("computer_name", "Unknown System")

    if player is not None:
        msg = Message(
            game_session_id=session_id,
            player_id=player.id,
            from_name="Federal Investigation Bureau",
            subject="ARRESTED: Gateway Seized",
            body=(
                f"Agent,\n\n"
                f"Following your unauthorized access to {computer_name}, "
                f"agents have traced your connection and seized your gateway.\n\n"
                f"Your Uplink account has been terminated.\n\n"
                f"- Federal Investigation Bureau"
            ),
        )
        db.add(msg)

    return {
        "type": "game_over",
        "session_id": session_id,
        "reason": "arrested",
    }


async def _process_mission_generate(
    db: AsyncSession,
    session_id: str,
    player: Player | None,
    data: dict,
    current_tick: int,
) -> dict | None:
    """Generate new missions for the BBS."""
    from app.game import mission_engine

    player_rating = player.uplink_rating if player else 0
    count = data.get("count", 3)

    await mission_engine.generate_missions(
        db, session_id, count,
        player_rating=player_rating,
        current_tick=current_tick,
    )

    log.info("Generated %d new missions for session %s", count, session_id)
    return None  # No broadcast message needed for mission generation
