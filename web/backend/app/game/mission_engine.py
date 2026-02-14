"""Mission engine -- generates, accepts, checks, and completes missions.

Ported from uplink/src/world/generator/missiongenerator.cpp.
"""
import json
import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mission import Mission
from app.models.message import Message
from app.models.player import Player
from app.models.company import Company
from app.models.computer import Computer
from app.models.databank import DataFile
from app.models.person import Person
from app.models.vlocation import VLocation
from app.game import constants as C
from app.game.name_generator import generate_name

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mission type constants
# ---------------------------------------------------------------------------
TYPE_STEALFILE = 1
TYPE_DESTROYFILE = 2
TYPE_FINDDATA = 3
TYPE_CHANGEDATA = 4

# Probability tables for the MVP mission types (by index).
_PROB_TABLES = {
    TYPE_STEALFILE: C.PROB_MISSION_STEALFILE,
    TYPE_DESTROYFILE: C.PROB_MISSION_DESTROYFILE,
    TYPE_FINDDATA: C.PROB_MISSION_FINDDATA,
    TYPE_CHANGEDATA: C.PROB_MISSION_CHANGEDATA,
}

# Base payment per type.
_BASE_PAYMENT = {
    TYPE_STEALFILE: C.PAYMENT_MISSION_STEALFILE,
    TYPE_DESTROYFILE: C.PAYMENT_MISSION_DESTROYFILE,
    TYPE_FINDDATA: C.PAYMENT_MISSION_FINDDATA,
    TYPE_CHANGEDATA: C.PAYMENT_MISSION_CHANGEDATA,
}

# Minimum difficulty per type.
_MIN_DIFFICULTY = {
    TYPE_STEALFILE: C.MINDIFFICULTY_MISSION_STEALFILE,
    TYPE_DESTROYFILE: C.MINDIFFICULTY_MISSION_DESTROYFILE,
    TYPE_FINDDATA: C.MINDIFFICULTY_MISSION_FINDDATA,
    TYPE_CHANGEDATA: C.MINDIFFICULTY_MISSION_CHANGEDATA,
}

# File name pools for generated missions.
_STEAL_FILENAMES = [
    "accounts.dat", "personnel.db", "clients.dat", "finances.xls",
    "passwords.sys", "strategy.doc", "research.dat", "patents.db",
    "contracts.dat", "internal_memo.doc", "salary_data.xls",
    "project_plans.doc", "customer_list.db", "trade_secrets.dat",
    "marketing_plan.doc", "employee_records.db",
]

_DESTROY_FILENAMES = [
    "evidence.log", "backup.dat", "audit_trail.log", "witness_report.doc",
    "transaction_log.dat", "security_footage.dat", "communications.log",
    "incriminating_data.dat", "surveillance.dat", "financial_records.db",
]

_FIND_DATA_TYPES = [
    "financial records", "employment history", "personal details",
    "medical records", "criminal record", "banking information",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _select_mission_type(rng: random.Random, player_rating: int) -> int:
    """Choose a mission type using weighted random selection."""
    rating_index = max(0, min(16, player_rating))
    weights = [table[rating_index] for table in _PROB_TABLES.values()]
    types = list(_PROB_TABLES.keys())

    total = sum(weights)
    if total == 0:
        return rng.choice(types)

    return rng.choices(types, weights=weights, k=1)[0]


def _get_rating_level(score: int) -> int:
    """Compute the Uplink rating level (0-16) from a running score."""
    level = 0
    for idx, (_, threshold) in enumerate(C.UPLINKRATING):
        if score >= threshold:
            level = idx
    return level


# ---------------------------------------------------------------------------
# generate_missions
# ---------------------------------------------------------------------------

async def generate_missions(
    db: AsyncSession,
    session_id: str,
    count: int,
    player_rating: int = 0,
    current_tick: int = 0,
) -> list[Mission]:
    """Generate *count* random missions for the given game session.

    Uses the probability tables from constants to select mission types
    based on the player's Uplink rating level.
    """
    rng = random.Random()

    # Load companies eligible to be employers (not Government, not Uplink Corporation)
    companies = (
        await db.execute(
            select(Company).where(
                Company.game_session_id == session_id,
                Company.name.notin_(["Government", "Uplink Corporation"]),
            )
        )
    ).scalars().all()

    if not companies:
        log.warning("No eligible employer companies found for session %s", session_id)
        return []

    # Load internal services machines (computer_type=1) as potential targets
    target_computers = (
        await db.execute(
            select(Computer).where(
                Computer.game_session_id == session_id,
                Computer.computer_type == 1,  # internal services
            )
        )
    ).scalars().all()

    if not target_computers:
        log.warning("No target computers found for session %s", session_id)
        return []

    # Load people for find/change data missions
    people = (
        await db.execute(
            select(Person).where(
                Person.game_session_id == session_id,
                Person.is_agent == False,
            )
        )
    ).scalars().all()

    missions: list[Mission] = []

    for _ in range(count):
        mission_type = _select_mission_type(rng, player_rating)
        employer = rng.choice(companies)
        target_computer = rng.choice(target_computers)

        # Payment: base * (1 + random variance)
        base_payment = _BASE_PAYMENT[mission_type]
        variance = rng.uniform(-C.PAYMENT_MISSION_VARIANCE, C.PAYMENT_MISSION_VARIANCE)
        payment = int(base_payment * (1 + variance))

        # Difficulty: min + random(0, variance)
        min_diff = _MIN_DIFFICULTY[mission_type]
        difficulty = min_diff + rng.randint(0, C.DIFFICULTY_MISSION_VARIANCE)

        # Min rating: difficulty // 2, clamped 0-16
        min_rating = max(0, min(16, difficulty // 2))

        # Generate description and target_data based on type
        description: str
        target_data: dict

        if mission_type == TYPE_STEALFILE:
            filename = rng.choice(_STEAL_FILENAMES)
            description = (
                f"Steal file '{filename}' from "
                f"{target_computer.company_name} Internal Services Machine"
            )
            target_data = {
                "target_filename": filename,
                "target_company": target_computer.company_name,
                "target_computer_id": target_computer.id,
            }

        elif mission_type == TYPE_DESTROYFILE:
            filename = rng.choice(_DESTROY_FILENAMES)
            description = (
                f"Destroy all evidence: delete file '{filename}' from "
                f"{target_computer.company_name} file server"
            )
            target_data = {
                "target_filename": filename,
                "target_company": target_computer.company_name,
                "target_computer_id": target_computer.id,
            }

            # Create the target file on the target computer so it can be deleted
            target_file = DataFile(
                computer_id=target_computer.id,
                filename=filename,
                size=rng.randint(1, 4),
                file_type=2,  # data file
                data=f"Confidential data from {target_computer.company_name}",
            )
            db.add(target_file)

        elif mission_type == TYPE_FINDDATA:
            person_name = generate_name(rng) if not people else rng.choice(people).name
            data_type = rng.choice(_FIND_DATA_TYPES)
            description = (
                f"Find {data_type} for {person_name} - "
                f"check {target_computer.company_name} records"
            )
            target_data = {
                "target_person": person_name,
                "target_data_type": data_type,
                "target_company": target_computer.company_name,
                "target_computer_id": target_computer.id,
            }

        elif mission_type == TYPE_CHANGEDATA:
            person_name = generate_name(rng) if not people else rng.choice(people).name
            description = (
                f"Change academic record for {person_name} "
                f"at International Academic Database"
            )
            target_data = {
                "target_person": person_name,
                "target_company": target_computer.company_name,
                "target_computer_id": target_computer.id,
            }

        else:
            continue

        # Also ensure a target file exists for steal missions
        if mission_type == TYPE_STEALFILE:
            target_file = DataFile(
                computer_id=target_computer.id,
                filename=target_data["target_filename"],
                size=rng.randint(1, 4),
                file_type=2,
                data=f"Confidential: {target_data['target_filename']}",
            )
            db.add(target_file)

        mission = Mission(
            game_session_id=session_id,
            mission_type=mission_type,
            description=description,
            employer_name=employer.name,
            payment=payment,
            difficulty=difficulty,
            min_rating=min_rating,
            target_computer_ip=target_computer.ip,
            target_data=json.dumps(target_data),
            is_accepted=False,
            is_completed=False,
            created_at_tick=current_tick,
            due_at_tick=current_tick + C.TIME_TOEXPIREMISSIONS,
        )
        db.add(mission)
        missions.append(mission)

    await db.flush()
    return missions


# ---------------------------------------------------------------------------
# accept_mission
# ---------------------------------------------------------------------------

async def accept_mission(
    db: AsyncSession,
    session_id: str,
    player_id: int,
    mission_id: int,
) -> dict:
    """Accept a mission on behalf of the player.

    Returns a dict with mission data suitable for sending over the wire.
    Raises ValueError if the mission cannot be accepted.
    """
    mission = (
        await db.execute(
            select(Mission).where(
                Mission.id == mission_id,
                Mission.game_session_id == session_id,
            )
        )
    ).scalar_one_or_none()

    if mission is None:
        raise ValueError(f"Mission {mission_id} not found")
    if mission.is_accepted:
        raise ValueError(f"Mission {mission_id} is already accepted")
    if mission.is_completed:
        raise ValueError(f"Mission {mission_id} is already completed")

    mission.is_accepted = True
    mission.accepted_by = str(player_id)

    # Send confirmation message to the player
    msg = Message(
        game_session_id=session_id,
        player_id=player_id,
        from_name=mission.employer_name,
        subject=f"Mission Accepted: {mission.description[:80]}",
        body=(
            f"Agent,\n\n"
            f"Thank you for accepting this mission.\n\n"
            f"Objective: {mission.description}\n"
            f"Payment on completion: {mission.payment}c\n\n"
            f"Complete the objective and report back for payment.\n\n"
            f"- {mission.employer_name}"
        ),
    )
    db.add(msg)
    await db.flush()

    return _mission_to_dict(mission)


# ---------------------------------------------------------------------------
# check_mission_completion
# ---------------------------------------------------------------------------

async def check_mission_completion(
    db: AsyncSession,
    session_id: str,
    player_id: int,
    mission_id: int,
) -> dict:
    """Check whether the player has completed the mission objective.

    Returns {"completed": True/False, "reason": "..."}.
    """
    mission = (
        await db.execute(
            select(Mission).where(
                Mission.id == mission_id,
                Mission.game_session_id == session_id,
            )
        )
    ).scalar_one_or_none()

    if mission is None:
        raise ValueError(f"Mission {mission_id} not found")
    if not mission.is_accepted or mission.accepted_by != str(player_id):
        raise ValueError(f"Mission {mission_id} is not accepted by this player")
    if mission.is_completed:
        return {"completed": True, "reason": "Mission already completed"}

    target_data = json.loads(mission.target_data or "{}")

    # Find the player to get their gateway computer ID
    player = (
        await db.execute(select(Player).where(Player.id == player_id))
    ).scalar_one()

    gateway_computer_id = await _get_gateway_computer_id(db, session_id, player)

    if mission.mission_type == TYPE_STEALFILE:
        # Check if a file with the matching filename exists on the player's gateway
        target_filename = target_data.get("target_filename", "")
        if gateway_computer_id is None:
            return {"completed": False, "reason": "No gateway computer found"}

        file_on_gateway = (
            await db.execute(
                select(DataFile).where(
                    DataFile.computer_id == gateway_computer_id,
                    DataFile.filename == target_filename,
                )
            )
        ).scalar_one_or_none()

        if file_on_gateway is not None:
            return {"completed": True, "reason": f"File '{target_filename}' found on gateway"}
        return {"completed": False, "reason": f"File '{target_filename}' not found on gateway"}

    elif mission.mission_type == TYPE_DESTROYFILE:
        # Check if the target file no longer exists on the target computer
        target_filename = target_data.get("target_filename", "")
        target_computer_id = target_data.get("target_computer_id")

        if target_computer_id is None:
            return {"completed": False, "reason": "Target computer not specified"}

        file_on_target = (
            await db.execute(
                select(DataFile).where(
                    DataFile.computer_id == int(target_computer_id),
                    DataFile.filename == target_filename,
                )
            )
        ).scalar_one_or_none()

        if file_on_target is None:
            return {"completed": True, "reason": f"File '{target_filename}' has been destroyed"}
        return {"completed": False, "reason": f"File '{target_filename}' still exists on target"}

    elif mission.mission_type == TYPE_FINDDATA:
        # Check if the player has a file containing the target data on their gateway
        target_person = target_data.get("target_person", "")
        if gateway_computer_id is None:
            return {"completed": False, "reason": "No gateway computer found"}

        files = (
            await db.execute(
                select(DataFile).where(
                    DataFile.computer_id == gateway_computer_id,
                )
            )
        ).scalars().all()

        for f in files:
            if f.data and target_person in f.data:
                return {"completed": True, "reason": f"Data about '{target_person}' found on gateway"}

        return {"completed": False, "reason": f"No data about '{target_person}' found on gateway"}

    elif mission.mission_type == TYPE_CHANGEDATA:
        # Simplified check: see if the player has connected to the target computer
        # by checking for any access log with the player's IP
        target_computer_id = target_data.get("target_computer_id")
        if target_computer_id is None:
            return {"completed": False, "reason": "Target computer not specified"}

        from app.models.logbank import AccessLog
        player_log = (
            await db.execute(
                select(AccessLog).where(
                    AccessLog.computer_id == int(target_computer_id),
                    AccessLog.from_ip == (player.localhost_ip or "127.0.0.1"),
                )
            )
        ).scalar_one_or_none()

        if player_log is not None:
            return {"completed": True, "reason": "Academic record has been modified"}
        return {"completed": False, "reason": "Target records have not been changed"}

    return {"completed": False, "reason": "Unknown mission type"}


# ---------------------------------------------------------------------------
# complete_mission
# ---------------------------------------------------------------------------

async def complete_mission(
    db: AsyncSession,
    session_id: str,
    player_id: int,
    mission_id: int,
) -> dict:
    """Mark a mission as completed, credit payment, and update ratings.

    Returns a dict with updated player data: balance, uplink_rating,
    neuromancer_rating, and the rating level.
    """
    mission = (
        await db.execute(
            select(Mission).where(
                Mission.id == mission_id,
                Mission.game_session_id == session_id,
            )
        )
    ).scalar_one_or_none()

    if mission is None:
        raise ValueError(f"Mission {mission_id} not found")
    if mission.is_completed:
        raise ValueError(f"Mission {mission_id} is already completed")

    mission.is_completed = True

    # Credit the player
    player = (
        await db.execute(select(Player).where(Player.id == player_id))
    ).scalar_one()

    player.balance += mission.payment

    # Update uplink rating: add difficulty points to running score
    player.uplink_rating += mission.difficulty

    # Update neuromancer rating
    mission_type_index = mission.mission_type
    if 0 <= mission_type_index < len(C.NEUROMANCERCHANGE):
        player.neuromancer_rating += C.NEUROMANCERCHANGE[mission_type_index]

    # Compute the rating level for display
    rating_level = _get_rating_level(player.uplink_rating)

    # Send "payment received" message
    msg = Message(
        game_session_id=session_id,
        player_id=player_id,
        from_name=mission.employer_name,
        subject=f"Payment: {mission.payment}c credited",
        body=(
            f"Agent,\n\n"
            f"Mission completed successfully.\n\n"
            f"Payment of {mission.payment}c has been credited to your account.\n"
            f"Your current balance is {player.balance}c.\n\n"
            f"We may have further work for you in the future.\n\n"
            f"- {mission.employer_name}"
        ),
    )
    db.add(msg)
    await db.flush()

    return {
        "balance": player.balance,
        "uplink_rating": player.uplink_rating,
        "uplink_rating_level": rating_level,
        "uplink_rating_name": C.UPLINKRATING[rating_level][0],
        "neuromancer_rating": player.neuromancer_rating,
        "mission_payment": mission.payment,
    }


# ---------------------------------------------------------------------------
# get_available_missions
# ---------------------------------------------------------------------------

async def get_available_missions(
    db: AsyncSession,
    session_id: str,
    player_rating: int = 0,
) -> list[dict]:
    """Return available (unaccepted, uncompleted) missions the player can see.

    Only includes missions where min_rating <= player_rating.
    Ordered by payment descending.
    """
    rating_level = _get_rating_level(player_rating)

    missions = (
        await db.execute(
            select(Mission).where(
                Mission.game_session_id == session_id,
                Mission.is_accepted == False,
                Mission.is_completed == False,
                Mission.min_rating <= rating_level,
            ).order_by(Mission.payment.desc())
        )
    ).scalars().all()

    return [_mission_to_dict(m) for m in missions]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _mission_to_dict(mission: Mission) -> dict:
    """Convert a Mission model to a serialisable dict."""
    return {
        "id": mission.id,
        "mission_type": mission.mission_type,
        "description": mission.description,
        "employer_name": mission.employer_name,
        "payment": mission.payment,
        "difficulty": mission.difficulty,
        "min_rating": mission.min_rating,
        "target_computer_ip": mission.target_computer_ip,
        "is_accepted": mission.is_accepted,
        "is_completed": mission.is_completed,
        "accepted_by": mission.accepted_by,
        "created_at_tick": mission.created_at_tick,
        "due_at_tick": mission.due_at_tick,
    }


async def _get_gateway_computer_id(
    db: AsyncSession, session_id: str, player: Player
) -> int | None:
    """Resolve the computer_id for the player's gateway (via their localhost IP)."""
    if player.localhost_ip is None:
        return None
    gateway_loc = (
        await db.execute(
            select(VLocation).where(
                VLocation.game_session_id == session_id,
                VLocation.ip == player.localhost_ip,
            )
        )
    ).scalar_one_or_none()
    if gateway_loc is None:
        return None
    return gateway_loc.computer_id
