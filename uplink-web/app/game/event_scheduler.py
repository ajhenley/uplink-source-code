"""Event scheduler -- processes delayed consequence events."""
import json
import logging

from app.extensions import db
from app.models.scheduled_event import ScheduledEvent
from app.models.message import Message
from app.models.player import Player
from app.models.game_session import GameSession
from app.game import constants as C

log = logging.getLogger(__name__)

TICKS_PER_GAME_MINUTE = 5
TIME_LEGALACTION_TICKS = C.TIME_LEGALACTION * TICKS_PER_GAME_MINUTE
FREQUENCY_GENERATENEWMISSION_TICKS = C.FREQUENCY_GENERATENEWMISSION * TICKS_PER_GAME_MINUTE
DEFAULT_FINE_AMOUNT = 3000
HIGH_SECURITY_DIFFICULTY_THRESHOLD = 200
TIME_FINE_TICKS = C.TIME_TOPAYLEGALFINE * TICKS_PER_GAME_MINUTE
TIME_TACTICALACTION_TICKS = C.TIME_TACTICALACTION * TICKS_PER_GAME_MINUTE
TIME_TACTICALWARNING_TICKS = C.TIME_TACTICALACTION_WARNING * TICKS_PER_GAME_MINUTE
TIME_LEGALWARNING_TICKS = C.TIME_LEGALACTION_WARNING * TICKS_PER_GAME_MINUTE
TIME_BANKROBBERY_TICKS = C.TIME_TOCOVERBANKROBBERY * TICKS_PER_GAME_MINUTE
COST_UPLINK_PERMONTH_TICKS = 30 * 24 * 60 * TICKS_PER_GAME_MINUTE  # 30 days
FREQUENCY_EXPIREOLDSTUFF_TICKS = C.FREQUENCY_EXPIREOLDSTUFF * TICKS_PER_GAME_MINUTE
FREQUENCY_CHECKBREACHES_TICKS = C.FREQUENCY_CHECKFORSECURITYBREACHES * TICKS_PER_GAME_MINUTE


def schedule_event(session_id, event_type, trigger_tick, data=None):
    event = ScheduledEvent(
        game_session_id=session_id,
        event_type=event_type,
        trigger_tick=trigger_tick,
        data=json.dumps(data or {}),
        is_processed=False,
    )
    db.session.add(event)
    db.session.flush()
    return event


def process_events(session_id, current_tick):
    events = ScheduledEvent.query.filter(
        ScheduledEvent.game_session_id == session_id,
        ScheduledEvent.trigger_tick <= current_tick,
        ScheduledEvent.is_processed == False,
    ).order_by(ScheduledEvent.trigger_tick).all()

    if not events:
        return []

    player = Player.query.filter_by(game_session_id=session_id).first()
    messages = []

    for event in events:
        event.is_processed = True
        event_data = json.loads(event.data or "{}")

        if event.event_type == "warning":
            result = _process_warning(session_id, player, event_data, current_tick)
            if result:
                messages.append(result)
        elif event.event_type == "fine":
            result = _process_fine(session_id, player, event_data, current_tick)
            if result:
                messages.append(result)
        elif event.event_type == "arrest":
            result = _process_arrest(session_id, player, event_data)
            if result:
                messages.append(result)
        elif event.event_type == "legal_warning":
            result = _process_legal_warning(session_id, player, event_data, current_tick)
            if result:
                messages.append(result)
        elif event.event_type == "tactical_warning":
            result = _process_tactical_warning(session_id, player, event_data, current_tick)
            if result:
                messages.append(result)
        elif event.event_type == "shot_by_feds":
            result = _process_shot_by_feds(session_id, player, event_data)
            if result:
                messages.append(result)
        elif event.event_type == "gateway_seizure":
            result = _process_gateway_seizure(session_id, player, event_data)
            if result:
                messages.append(result)
        elif event.event_type == "bank_robbery":
            result = _process_bank_robbery(session_id, player, event_data, current_tick)
            if result:
                messages.append(result)
        elif event.event_type == "uplink_fee":
            result = _process_uplink_fee(session_id, player, event_data, current_tick)
            if result:
                messages.append(result)
        elif event.event_type == "expire_old":
            result = _process_expire_old(session_id, player, event_data, current_tick)
            if result:
                messages.append(result)
        elif event.event_type == "mission_generate":
            _process_mission_generate(session_id, player, event_data, current_tick)

    return messages


def schedule_trace_consequences(session_id, computer_name, current_tick=0, hack_difficulty=0.0):
    """Full cascading consequence timeline from the PRD."""
    events = []

    # Step 1: Immediate warning email
    events.append(schedule_event(session_id, "warning", trigger_tick=current_tick,
                                 data={"computer_name": computer_name}))

    # Step 2: Fine after 7 days
    fine_tick = current_tick + TIME_FINE_TICKS
    events.append(schedule_event(session_id, "fine",
                                 trigger_tick=fine_tick,
                                 data={"computer_name": computer_name, "amount": DEFAULT_FINE_AMOUNT}))

    # Step 3: Legal action (arrest) 3 hours after fine deadline
    if hack_difficulty >= HIGH_SECURITY_DIFFICULTY_THRESHOLD:
        # High security: 2-minute warning, then arrest
        legal_warning_tick = fine_tick + TIME_LEGALACTION_TICKS - TIME_LEGALWARNING_TICKS
        events.append(schedule_event(session_id, "legal_warning",
                                     trigger_tick=legal_warning_tick,
                                     data={"computer_name": computer_name}))
        events.append(schedule_event(session_id, "arrest",
                                     trigger_tick=fine_tick + TIME_LEGALACTION_TICKS,
                                     data={"computer_name": computer_name}))

        # Step 4: Tactical action 5 minutes after arrest
        tactical_warning_tick = fine_tick + TIME_LEGALACTION_TICKS + TIME_TACTICALACTION_TICKS - TIME_TACTICALWARNING_TICKS
        events.append(schedule_event(session_id, "tactical_warning",
                                     trigger_tick=tactical_warning_tick,
                                     data={"computer_name": computer_name}))
        events.append(schedule_event(session_id, "shot_by_feds",
                                     trigger_tick=fine_tick + TIME_LEGALACTION_TICKS + TIME_TACTICALACTION_TICKS,
                                     data={"computer_name": computer_name}))

    return events


def schedule_initial_events(session_id, start_tick):
    """Schedule the initial set of recurring events for a new game session."""
    # Monthly Uplink fee
    schedule_event(session_id, "uplink_fee",
                   trigger_tick=start_tick + COST_UPLINK_PERMONTH_TICKS, data={})
    # Periodic expiry cleanup
    schedule_event(session_id, "expire_old",
                   trigger_tick=start_tick + FREQUENCY_EXPIREOLDSTUFF_TICKS, data={})
    # First mission generation
    schedule_event(session_id, "mission_generate",
                   trigger_tick=start_tick + FREQUENCY_GENERATENEWMISSION_TICKS,
                   data={"count": 3})


def _process_warning(session_id, player, data, current_tick):
    if player is None:
        return None
    computer_name = data.get("computer_name", "Unknown System")
    db.session.add(Message(
        game_session_id=session_id,
        player_id=player.id,
        from_name="Federal Investigation Bureau",
        subject=f"Security Alert: Unauthorized access to {computer_name}",
        body=(
            f"Agent,\n\nOur records indicate that you were involved in unauthorized "
            f"access to {computer_name}.\n\nThis is a formal warning. Further illegal "
            f"activity will result in fines or arrest.\n\n- Federal Investigation Bureau"
        ),
        created_at_tick=current_tick,
    ))
    return {"type": "message_received", "session_id": session_id, "subject": f"Security Alert: {computer_name}"}


def _process_fine(session_id, player, data, current_tick):
    if player is None:
        return None
    amount = data.get("amount", DEFAULT_FINE_AMOUNT)
    player.balance = max(0, player.balance - amount)
    computer_name = data.get("computer_name", "Unknown System")
    db.session.add(Message(
        game_session_id=session_id,
        player_id=player.id,
        from_name="Federal Investigation Bureau",
        subject=f"Fine: {amount}c deducted",
        body=(
            f"Agent,\n\nFollowing your unauthorized access to {computer_name}, "
            f"a fine of {amount}c has been deducted.\nBalance: {player.balance}c.\n\n"
            f"- Federal Investigation Bureau"
        ),
        created_at_tick=current_tick,
    ))
    return {"type": "balance_changed", "session_id": session_id, "balance": player.balance, "fine": amount}


def _process_arrest(session_id, player, data):
    session = db.session.get(GameSession, session_id)
    if session is None:
        return None
    session.is_active = False
    if player is not None:
        computer_name = data.get("computer_name", "Unknown System")
        db.session.add(Message(
            game_session_id=session_id,
            player_id=player.id,
            from_name="Federal Investigation Bureau",
            subject="ARRESTED: Gateway Seized",
            body=f"Agent,\n\nYour gateway has been seized following unauthorized access to {computer_name}.\n\n- Federal Investigation Bureau",
        ))
    return {"type": "game_over", "session_id": session_id, "reason": "arrested"}


def _process_mission_generate(session_id, player, data, current_tick):
    from app.game import mission_engine
    player_rating = player.uplink_rating if player else 0
    count = data.get("count", 3)
    mission_engine.generate_missions(session_id, count, player_rating=player_rating, current_tick=current_tick)


def _process_legal_warning(session_id, player, data, current_tick):
    if player is None:
        return None
    computer_name = data.get("computer_name", "Unknown System")
    db.session.add(Message(
        game_session_id=session_id,
        player_id=player.id,
        from_name="Federal Investigation Bureau",
        subject="URGENT: Arrest Warrant Issued",
        body=(
            f"Agent,\n\nA warrant has been issued for your arrest following "
            f"unauthorized access to {computer_name}.\n\n"
            f"Federal agents will arrive at your gateway within 2 minutes.\n\n"
            f"- Federal Investigation Bureau"
        ),
        created_at_tick=current_tick,
    ))
    return {"type": "message_received", "session_id": session_id, "subject": "URGENT: Arrest Warrant Issued"}


def _process_tactical_warning(session_id, player, data, current_tick):
    if player is None:
        return None
    db.session.add(Message(
        game_session_id=session_id,
        player_id=player.id,
        from_name="Federal Investigation Bureau",
        subject="CRITICAL: Armed Response Incoming",
        body=(
            "Agent,\n\nYou have failed to comply with the arrest warrant.\n\n"
            "An armed tactical team has been dispatched to your physical location.\n"
            "You have approximately 1 minute.\n\n"
            "- Federal Investigation Bureau"
        ),
        created_at_tick=current_tick,
    ))
    return {"type": "message_received", "session_id": session_id, "subject": "CRITICAL: Armed Response Incoming"}


def _process_shot_by_feds(session_id, player, data):
    session = db.session.get(GameSession, session_id)
    if session is None:
        return None
    session.is_active = False
    return {"type": "game_over", "session_id": session_id, "reason": "shot_by_feds"}


def _process_gateway_seizure(session_id, player, data):
    session = db.session.get(GameSession, session_id)
    if session is None:
        return None
    session.is_active = False
    return {"type": "game_over", "session_id": session_id, "reason": "gateway_seized"}


def _process_bank_robbery(session_id, player, data, current_tick):
    """2-minute window has expired without covering tracks."""
    if player is None:
        return None
    session = db.session.get(GameSession, session_id)
    if session is None:
        return None
    session.is_active = False
    return {"type": "game_over", "session_id": session_id, "reason": "caught_money_transfer"}


def _process_uplink_fee(session_id, player, data, current_tick):
    """Monthly Uplink subscription fee of 300c."""
    if player is None:
        return None
    player.balance = max(0, player.balance - C.COST_UPLINK_PERMONTH)
    db.session.add(Message(
        game_session_id=session_id,
        player_id=player.id,
        from_name="Uplink Corporation",
        subject=f"Monthly Subscription: {C.COST_UPLINK_PERMONTH}c",
        body=(
            f"Agent,\n\nYour monthly Uplink subscription fee of {C.COST_UPLINK_PERMONTH}c "
            f"has been deducted from your account.\n\nBalance: {player.balance}c\n\n"
            f"- Uplink Corporation Billing"
        ),
        created_at_tick=current_tick,
    ))
    # Reschedule next month
    schedule_event(session_id, "uplink_fee", trigger_tick=current_tick + COST_UPLINK_PERMONTH_TICKS, data={})
    return {"type": "balance_changed", "session_id": session_id, "balance": player.balance}


def _process_expire_old(session_id, player, data, current_tick):
    """Expire old news, logs, and missions."""
    from app.models.news import NewsArticle
    from app.models.mission import Mission

    expire_news_tick = current_tick - (C.TIME_TOEXPIRENEWS * TICKS_PER_GAME_MINUTE)
    NewsArticle.query.filter(
        NewsArticle.game_session_id == session_id,
        NewsArticle.created_at_tick < expire_news_tick,
    ).delete()

    expire_mission_tick = current_tick - (C.TIME_TOEXPIREMISSIONS * TICKS_PER_GAME_MINUTE)
    Mission.query.filter(
        Mission.game_session_id == session_id,
        Mission.is_accepted == False,
        Mission.is_completed == False,
        Mission.created_at_tick < expire_mission_tick,
    ).delete()

    expire_log_tick = current_tick - (C.TIME_TOEXPIRELOGS * TICKS_PER_GAME_MINUTE)
    from app.models.access_log import AccessLog
    AccessLog.query.filter(
        AccessLog.created_at_tick < expire_log_tick,
    ).delete()

    # Reschedule
    schedule_event(session_id, "expire_old", trigger_tick=current_tick + FREQUENCY_EXPIREOLDSTUFF_TICKS, data={})
    return None
