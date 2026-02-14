"""NPC Agent AI engine -- rival agents that compete with the player for missions."""
import logging
import random

from app.extensions import db
from app.models.person import Person
from app.models.mission import Mission
from app.models.player import Player
from app.game import constants as C

log = logging.getLogger(__name__)

# ============================================================
# Tuning constants for NPC behaviour
# ============================================================

# How many game-time ticks between NPC evaluation cycles
NPC_TICK_INTERVAL = C.FREQUENCY_GIVEMISSIONTONPC * 5  # convert game-minutes to ticks (5 ticks/min)

# Base probability (0-1) that an NPC will attempt a mission each cycle
NPC_ATTEMPT_BASE_PROBABILITY = 0.35

# Skill bonus per point of uplink_rating above mission difficulty
SKILL_BONUS_PER_POINT = 0.04

# Base success rate when NPC rating exactly matches difficulty
BASE_SUCCESS_RATE = 0.50

# Probability that a failed attempt leads to arrest
ARREST_ON_FAILURE_PROBABILITY = 0.15

# Rating points gained on a successful mission (scaled by difficulty)
RATING_GAIN_PER_DIFFICULTY = 1

# Rating points lost on a failed mission
RATING_LOSS_ON_FAILURE = 2


def tick_npcs(session_id, current_tick):
    """Called periodically by the game loop.

    NPCs attempt available missions, gain or lose rating, and may get arrested.
    Should be invoked every ``NPC_TICK_INTERVAL`` ticks (the caller is
    responsible for gating the frequency).

    Returns a list of event dicts describing what happened this cycle.
    """
    if current_tick % NPC_TICK_INTERVAL != 0:
        return []

    rng = random.Random()
    events = []

    # Fetch all NPC agents for this session that are not arrested
    npcs = Person.query.filter(
        Person.game_session_id == session_id,
        Person.is_agent == True,
        Person.has_criminal_record == False,
    ).all()

    if not npcs:
        return events

    # Fetch unclaimed, incomplete missions for this session
    available_missions = Mission.query.filter(
        Mission.game_session_id == session_id,
        Mission.is_accepted == False,
        Mission.is_completed == False,
    ).all()

    if not available_missions:
        return events

    # Shuffle so NPCs don't always pick the same mission
    rng.shuffle(available_missions)

    # Build a quick set of missions already claimed this cycle
    claimed_mission_ids = set()

    for npc in npcs:
        # Each NPC has a random chance of being active this cycle
        if rng.random() > NPC_ATTEMPT_BASE_PROBABILITY:
            continue

        # Find a mission this NPC qualifies for
        npc_rating_level = _get_rating_level(npc.uplink_rating)
        mission = _pick_mission_for_npc(available_missions, npc_rating_level, claimed_mission_ids)
        if mission is None:
            continue

        claimed_mission_ids.add(mission.id)

        # Determine success based on NPC skill vs mission difficulty
        success_probability = _calc_success_probability(npc.uplink_rating, mission.difficulty)
        succeeded = rng.random() < success_probability

        if succeeded:
            event = _npc_complete_mission(npc, mission)
            events.append(event)
        else:
            event = _npc_fail_mission(npc, mission, rng)
            events.append(event)

    db.session.flush()
    return events


def get_agent_rankings(session_id):
    """Return a ranked list of all agents (NPCs + player) ordered by uplink_rating descending.

    Each entry is a dict with ``name``, ``uplink_rating``, ``rating_name``,
    ``is_player``, and ``is_arrested``.
    """
    rankings = []

    # NPCs
    npcs = Person.query.filter(
        Person.game_session_id == session_id,
        Person.is_agent == True,
    ).all()

    for npc in npcs:
        level = _get_rating_level(npc.uplink_rating)
        rankings.append({
            "name": npc.name,
            "uplink_rating": npc.uplink_rating,
            "rating_name": C.UPLINKRATING[level][0],
            "rating_level": level,
            "is_player": False,
            "is_arrested": npc.has_criminal_record,
        })

    # Player
    player = Player.query.filter_by(game_session_id=session_id).first()
    if player is not None:
        level = _get_rating_level(player.uplink_rating)
        rankings.append({
            "name": player.handle or player.name,
            "uplink_rating": player.uplink_rating,
            "rating_name": C.UPLINKRATING[level][0],
            "rating_level": level,
            "is_player": True,
            "is_arrested": False,
        })

    # Sort descending by rating, with ties broken alphabetically
    rankings.sort(key=lambda r: (-r["uplink_rating"], r["name"]))

    # Assign rank positions (1-based)
    for idx, entry in enumerate(rankings, start=1):
        entry["rank"] = idx

    return rankings


def arrest_agent(session_id, person_id):
    """Mark an NPC agent as arrested (has_criminal_record = True).

    Returns a dict describing the arrest, or ``None`` if the person was not found.
    """
    npc = Person.query.filter_by(
        id=person_id,
        game_session_id=session_id,
        is_agent=True,
    ).first()

    if npc is None:
        return None

    npc.has_criminal_record = True
    # Halve their rating as a penalty
    npc.uplink_rating = max(0, npc.uplink_rating // 2)
    db.session.flush()

    return {
        "person_id": npc.id,
        "name": npc.name,
        "arrested": True,
        "uplink_rating": npc.uplink_rating,
    }


# ============================================================
# Internal helpers
# ============================================================

def _get_rating_level(score):
    """Convert a raw uplink_rating score to an index into C.UPLINKRATING."""
    level = 0
    for idx, (_, threshold) in enumerate(C.UPLINKRATING):
        if score >= threshold:
            level = idx
    return level


def _pick_mission_for_npc(available_missions, npc_rating_level, claimed_ids):
    """Select the first available mission the NPC is qualified for.

    Returns ``None`` if no suitable mission is found.
    """
    for mission in available_missions:
        if mission.id in claimed_ids:
            continue
        if mission.min_rating <= npc_rating_level:
            return mission
    return None


def _calc_success_probability(npc_rating, mission_difficulty):
    """Calculate NPC success probability (clamped 0.05 -- 0.95).

    Higher NPC rating relative to mission difficulty increases the chance.
    """
    delta = npc_rating - mission_difficulty
    probability = BASE_SUCCESS_RATE + (delta * SKILL_BONUS_PER_POINT)
    return max(0.05, min(0.95, probability))


def _npc_complete_mission(npc, mission):
    """Handle a successful NPC mission completion."""
    mission.is_accepted = True
    mission.is_completed = True
    mission.accepted_by = f"npc:{npc.id}"

    # Reward: rating increase proportional to difficulty
    rating_gain = mission.difficulty * RATING_GAIN_PER_DIFFICULTY
    npc.uplink_rating += rating_gain
    npc.rating += mission.payment

    log.debug(
        "NPC %s completed mission %d (diff=%d) -- rating now %d",
        npc.name, mission.id, mission.difficulty, npc.uplink_rating,
    )

    return {
        "type": "npc_mission_complete",
        "session_id": mission.game_session_id,
        "npc_name": npc.name,
        "npc_id": npc.id,
        "mission_id": mission.id,
        "mission_description": mission.description,
        "difficulty": mission.difficulty,
        "payment": mission.payment,
        "new_rating": npc.uplink_rating,
    }


def _npc_fail_mission(npc, mission, rng):
    """Handle a failed NPC mission attempt.

    The NPC loses some rating.  There is also a chance the NPC gets arrested.
    """
    npc.uplink_rating = max(0, npc.uplink_rating - RATING_LOSS_ON_FAILURE)

    arrested = rng.random() < ARREST_ON_FAILURE_PROBABILITY
    if arrested:
        npc.has_criminal_record = True
        npc.uplink_rating = max(0, npc.uplink_rating // 2)
        log.debug("NPC %s ARRESTED after failing mission %d", npc.name, mission.id)
        return {
            "type": "npc_arrested",
            "session_id": mission.game_session_id,
            "npc_name": npc.name,
            "npc_id": npc.id,
            "mission_id": mission.id,
            "mission_description": mission.description,
        }

    log.debug(
        "NPC %s failed mission %d -- rating now %d",
        npc.name, mission.id, npc.uplink_rating,
    )

    return {
        "type": "npc_mission_failed",
        "session_id": mission.game_session_id,
        "npc_name": npc.name,
        "npc_id": npc.id,
        "mission_id": mission.id,
        "mission_description": mission.description,
        "new_rating": npc.uplink_rating,
    }
